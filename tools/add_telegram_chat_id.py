"""
Migration: add telegram_chat_id BIGINT to users table.

Both the column and the unique constraint are added with IF NOT EXISTS
so this script is safe to run multiple times.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

ADD_COLUMN = text("""
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS telegram_chat_id BIGINT
""")

ADD_UNIQUE = text("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'users_telegram_chat_id_key'
              AND conrelid = 'users'::regclass
        ) THEN
            ALTER TABLE users
            ADD CONSTRAINT users_telegram_chat_id_key UNIQUE (telegram_chat_id);
        END IF;
    END
    $$
""")

SQL_PREVIEW = """\
-- Step 1: add column
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS telegram_chat_id BIGINT;

-- Step 2: add unique constraint (idempotent via pg_constraint check)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'users_telegram_chat_id_key'
          AND conrelid = 'users'::regclass
    ) THEN
        ALTER TABLE users
        ADD CONSTRAINT users_telegram_chat_id_key UNIQUE (telegram_chat_id);
    END IF;
END
$$;
"""


def column_exists(engine) -> bool:
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("users")}
    return "telegram_chat_id" in cols


def main() -> None:
    print("=== add_telegram_chat_id migration ===\n")
    print("SQL to be executed:")
    print("-" * 50)
    print(SQL_PREVIEW)
    print("-" * 50)

    engine = create_engine(DATABASE_URL)
    try:
        if column_exists(engine):
            print("users.telegram_chat_id: already exists — skipping ADD COLUMN")
        else:
            print("users.telegram_chat_id: adding column ...")
            with engine.begin() as conn:
                conn.execute(ADD_COLUMN)

            if column_exists(engine):
                print("users.telegram_chat_id: added successfully (BIGINT)")
            else:
                print("FAILURE: column not found after ALTER TABLE")
                return

        print("users.telegram_chat_id: applying unique constraint ...")
        with engine.begin() as conn:
            conn.execute(ADD_UNIQUE)
        print("users.telegram_chat_id: unique constraint ready")

        print("\nMigration complete.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
