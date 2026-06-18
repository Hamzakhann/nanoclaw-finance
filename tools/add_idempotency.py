"""
Migration: add idempotency_key to expenses table.

Uses ALTER TABLE ... ADD COLUMN IF NOT EXISTS so it is safe to run multiple
times — a no-op if the column already exists.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

ADD_COLUMN = text("""
    ALTER TABLE expenses
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(64) UNIQUE
""")


def column_exists(engine) -> bool:
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("expenses")}
    return "idempotency_key" in cols


def main() -> None:
    print("=== add_idempotency migration ===\n")

    engine = create_engine(DATABASE_URL)
    try:
        if column_exists(engine):
            print("expenses.idempotency_key: already exists — nothing to do")
            return

        print("expenses.idempotency_key: adding column ...")
        with engine.begin() as conn:
            conn.execute(ADD_COLUMN)

        if column_exists(engine):
            print("expenses.idempotency_key: added successfully (VARCHAR(64) UNIQUE)")
        else:
            print("FAILURE: column not found after ALTER TABLE")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
