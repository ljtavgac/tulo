import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import Page
from .schemas import PageOut, PageSummary
from .seed_templates import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Render's free-tier disk is ephemeral (resets on redeploy), so this
    # keeps the small template-review dataset self-healing without a manual
    # step. Real batch content will need a persistent database before launch.
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Tulo API", lifespan=lifespan)

# The frontend runs on a different origin than the backend, so browser-side
# requests need CORS enabled. FRONTEND_ORIGIN should be set to the deployed
# frontend's URL (e.g. https://tulo.com); it defaults to the local Next.js
# dev server for local development.
frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/pages/{slug}", response_model=PageOut)
def get_page(slug: str, db: Session = Depends(get_db)):
    page = db.query(Page).filter(Page.slug == slug).first()
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@app.get("/pages", response_model=list[PageSummary])
def list_pages(template_type: str | None = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(Page)
    if template_type is not None:
        query = query.filter(Page.template_type == template_type)
    return query.all()
