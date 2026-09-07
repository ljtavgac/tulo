import io
import os
import secrets
from contextlib import asynccontextmanager, redirect_stdout

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .fetch_stock_images import fetch_images
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


# Manual trigger for fetch_stock_images.py, for hosts (like Render's free
# tier) with no shell access to run the script directly. Gated behind
# ADMIN_TASK_TOKEN so it isn't a public unauthenticated endpoint hitting
# external APIs -- if that env var isn't set, this always 404s, matching
# the "inert without configuration" pattern used everywhere else in the
# stock-photo feature. A token in a URL query string is a modest bar (it
# can end up in server/proxy logs) but is a reasonable trade-off for an
# occasional manual maintenance action on a low-traffic site; rotate
# ADMIN_TASK_TOKEN in Render if you ever suspect it's leaked.
ADMIN_TASK_TOKEN = os.environ.get("ADMIN_TASK_TOKEN")


@app.get("/admin/fetch-images")
def trigger_fetch_images(token: str, force: bool = False, db: Session = Depends(get_db)):
    if not ADMIN_TASK_TOKEN or not secrets.compare_digest(token, ADMIN_TASK_TOKEN):
        raise HTTPException(status_code=404)

    log = io.StringIO()
    with redirect_stdout(log):
        pages_updated, images_written = fetch_images(db, force=force)

    return {
        "pages_updated": pages_updated,
        "images_written": images_written,
        "log": log.getvalue().splitlines(),
    }
