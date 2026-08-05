"""FastAPI dependencies. Pure HTTP glue -- no business logic lives here."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from recommender.db import SessionLocal


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
