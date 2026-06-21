"""
Applies memory_schema.sql against the Neon database and confirms
each table exists afterward.  Safe to run multiple times.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
SCHEMA_FILE = Path(__file__).parent / "memory_schema.sql"
EXPECTED_TABLES = ["action_log", "knowledge"]


def apply_schema(engine) -> None:
    sql = SCHEMA_FILE.read_text()
    with engine.begin() as conn:
        conn.execute(text(sql))


def confirm_tables(engine) -> list[str]:
    """Returns the list of expected tables that are actually present."""
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    return [t for t in EXPECTED_TABLES if t in existing]


def main() -> None:
    print("=== create_memory_tables ===\n")

    engine = create_engine(DATABASE_URL)
    try:
        print(f"[1/2] Applying {SCHEMA_FILE.name} ...")
        apply_schema(engine)
        print("      SQL executed successfully")

        print("\n[2/2] Confirming tables ...")
        found = confirm_tables(engine)
        for table in EXPECTED_TABLES:
            status = "OK" if table in found else "MISSING"
            print(f"      {table}: {status}")

        if len(found) == len(EXPECTED_TABLES):
            print("\nAll memory tables are in place.")
        else:
            missing = [t for t in EXPECTED_TABLES if t not in found]
            print(f"\nWARNING: missing tables: {missing}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
