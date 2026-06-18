"""
Idempotency demo.

Generates a SHA-256 key from "date:amount:description", inserts the same
expense row twice using INSERT ... ON CONFLICT (idempotency_key) DO NOTHING,
then confirms exactly one row exists.  All test data is cleaned up afterward.
"""
import datetime
import hashlib
import os
from decimal import Decimal

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from models import Base, Category

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

TEST_EMAIL = "idem_demo@nanoclaw.test"
TEST_DATE = datetime.date.today()
TEST_AMOUNT = Decimal("3750.00")
TEST_DESCRIPTION = "Carrefour grocery run — idempotency demo"

UPSERT_USER = text("""
    INSERT INTO users (name, email, created_at)
    VALUES (:name, :email, NOW())
    ON CONFLICT (email) DO NOTHING
""")

SELECT_USER_BY_EMAIL = text("""
    SELECT id FROM users WHERE email = :email
""")

INSERT_EXPENSE = text("""
    INSERT INTO expenses
        (amount, description, date, created_at, category_id, user_id, idempotency_key)
    VALUES
        (:amount, :description, :date, NOW(), :category_id, :user_id, :idempotency_key)
    ON CONFLICT (idempotency_key) DO NOTHING
""")

COUNT_BY_KEY = text("""
    SELECT COUNT(*) FROM expenses WHERE idempotency_key = :key
""")

DELETE_EXPENSES_BY_KEY = text("""
    DELETE FROM expenses WHERE idempotency_key = :key
""")


def make_idempotency_key(date: datetime.date, amount: Decimal, description: str) -> str:
    raw = f"{date}:{amount}:{description}"
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def get_first_category(session: Session) -> Category:
    cat = session.query(Category).first()
    if cat is None:
        raise RuntimeError("No categories found. Run tools/db_setup.py first.")
    return cat


def main() -> None:
    print("=== idempotency_demo ===\n")

    key = make_idempotency_key(TEST_DATE, TEST_AMOUNT, TEST_DESCRIPTION)
    print(f"[0]   idempotency key : {key}")

    engine = create_engine(DATABASE_URL)
    user_id = None

    try:
        Base.metadata.create_all(engine)

        # --- seed a temporary user and resolve a real category ---
        with Session(engine) as session:
            category = get_first_category(session)
            category_id = category.id

        with engine.begin() as conn:
            conn.execute(UPSERT_USER, {"name": "Idem Demo User", "email": TEST_EMAIL})
            user_id = conn.execute(
                SELECT_USER_BY_EMAIL, {"email": TEST_EMAIL}
            ).scalar_one()

        params = {
            "amount": str(TEST_AMOUNT),
            "description": TEST_DESCRIPTION,
            "date": TEST_DATE,
            "category_id": category_id,
            "user_id": user_id,
            "idempotency_key": key,
        }

        # --- first insert ---
        with engine.begin() as conn:
            conn.execute(INSERT_EXPENSE, params)
        print("[1]   first  insert : executed (ON CONFLICT DO NOTHING)")

        # --- second insert — identical row, same key ---
        with engine.begin() as conn:
            conn.execute(INSERT_EXPENSE, params)
        print("[2]   second insert : executed (ON CONFLICT DO NOTHING)")

        # --- verify exactly one row ---
        with engine.connect() as conn:
            count = conn.execute(COUNT_BY_KEY, {"key": key}).scalar()

        if count == 1:
            print("\nIDEMPOTENCY VERIFIED: 2 inserts produced 1 row")
        else:
            print(f"\nFAILURE: found {count} rows — duplicates not prevented")

    finally:
        if user_id is not None:
            with engine.begin() as conn:
                # Delete all expenses for this user first to satisfy the FK,
                # then delete the user. One transaction keeps cleanup atomic.
                conn.execute(
                    text("DELETE FROM expenses WHERE user_id = :uid"), {"uid": user_id}
                )
                conn.execute(
                    text("DELETE FROM users WHERE id = :uid"), {"uid": user_id}
                )
        print("\n[3]   test rows cleaned up")
        engine.dispose()


if __name__ == "__main__":
    main()
