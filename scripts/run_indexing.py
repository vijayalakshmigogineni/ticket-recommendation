"""Run the offline interaction indexing pipeline (Milestone 2) over whatever
is currently in the database. Safe to re-run -- only embeds rows that are
missing an embedding or were embedded under a different model."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from recommender.config import settings  # noqa: E402
from recommender.db import SessionLocal  # noqa: E402
from recommender.indexing import run_indexing  # noqa: E402


def main() -> None:
    session = SessionLocal()
    try:
        result = run_indexing(session)
        print(
            f"model={settings.ollama.embedding_model} "
            f"scanned={result.scanned} "
            f"already_current={result.skipped_not_embeddable} "
            f"embedded_this_run={result.embedded}"
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
