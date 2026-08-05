import pytest

from recommender.db import SessionLocal


@pytest.fixture
def db_session():
    """Session against the seeded pgvector Postgres container. Assumes
    scripts/init_db.py + scripts/seed_data.py + scripts/run_indexing.py have
    already been run -- these are integration tests over the shared manual
    dataset, not isolated per-test fixtures with rollback."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
