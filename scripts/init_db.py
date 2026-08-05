"""Bootstrap the recommender's database: create pgvector extension, all
tables (via Base.metadata.create_all -- no Alembic for this prototype), the
HNSW ANN index on Interaction.embedding, and the GIN full-text index used by
keyword search.

Re-runnable: DROP_AND_RECREATE=1 drops all tables first, which is the
expected path when switching EMBEDDING_MODEL (the vector column's dimension
is fixed at creation time, so a model swap needs a rebuild, not a migration).
"""

from __future__ import annotations

import os
import sys

from sqlalchemy import text

# Ensure the repo root is importable when this script is run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from recommender.config import settings  # noqa: E402
from recommender.db import Base, engine  # noqa: E402
from recommender.models import (  # noqa: E402,F401
    Customer,
    Interaction,
    RecommendationFeedback,
    Ticket,
)


def main() -> None:
    drop_first = os.environ.get("DROP_AND_RECREATE") == "1"

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

    if drop_first:
        print("DROP_AND_RECREATE=1 -- dropping all tables first")
        Base.metadata.drop_all(engine)

    Base.metadata.create_all(engine)
    print(f"Tables created. Embedding model={settings.ollama.embedding_model} "
          f"dim={settings.ollama.embedding_dim}")

    with engine.begin() as conn:
        # HNSW ANN index, cosine distance -- matches "ANN Search (Dense)" in
        # the architecture diagram. ivfflat would need a training pass over
        # existing data; HNSW builds incrementally, which suits a dataset
        # this small. m/ef_construction are set explicitly even though they
        # match pgvector's own defaults, purely so the debug dashboard's
        # Index Info endpoint can read them back from pg_class.reloptions
        # instead of assuming -- not a behavior change. DROP+CREATE (not
        # IF NOT EXISTS) so re-running this script also picks up the
        # explicit options on a database created before this change.
        conn.execute(text("DROP INDEX IF EXISTS ix_interactions_embedding_hnsw;"))
        conn.execute(text(
            "CREATE INDEX ix_interactions_embedding_hnsw "
            "ON interactions USING hnsw (embedding vector_cosine_ops) "
            "WITH (m = 16, ef_construction = 64);"
        ))
        # Functional GIN index backing keyword search's to_tsvector query --
        # matches "PostgreSQL Full Text Search" in the diagram.
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_interactions_content_fts "
            "ON interactions USING gin (to_tsvector('english', clean_content));"
        ))
    print("HNSW + full-text indexes ready.")


if __name__ == "__main__":
    main()
