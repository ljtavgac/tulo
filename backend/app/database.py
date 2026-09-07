import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Defaults to a local SQLite file for development. In production this should
# point at a persistent database (e.g. Postgres) via DATABASE_URL -- Render's
# free-tier disk is ephemeral, so SQLite there resets on every deploy, which
# is why app startup auto-seeds the small template-review dataset (see
# seed_templates.py) rather than relying on data surviving between deploys.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./tulo.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
