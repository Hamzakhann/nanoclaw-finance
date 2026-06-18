"""
Migration: add embedding vector(1536) to expenses table.

Requires the pgvector extension on the Neon database.
Both the extension and the column are added with IF NOT EXISTS / IF NOT EXISTS
so this script is safe to run multiple times.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

ENABLE_PGVECTOR = text("CREATE EXTENSION IF NOT EXISTS vector")

ADD_COLUMN = text("""
    ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS embedding vector(1536)
""")


def column_exists(engine) -> bool:
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("expenses")}
    return "embedding" in cols


def main() -> None:
    print("=== add_embedding migration ===\n")

    engine = create_engine(DATABASE_URL)
    try:
        print("expenses.embedding: enabling pgvector extension ...")
        with engine.begin() as conn:
            conn.execute(ENABLE_PGVECTOR)
        print("expenses.embedding: pgvector extension ready")

        if column_exists(engine):
            print("expenses.embedding: already exists — nothing to do")
            return

        print("expenses.embedding: adding column ...")
        with engine.begin() as conn:
            conn.execute(ADD_COLUMN)

        if column_exists(engine):
            print("expenses.embedding: added successfully (vector(1536))")
        else:
            print("FAILURE: column not found after ALTER TABLE")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
