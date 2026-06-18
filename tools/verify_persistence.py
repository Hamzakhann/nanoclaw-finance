"""
Persistence verification test.

Inserts 5 expense rows, closes the engine entirely, opens a brand-new
connection, re-fetches every row by ID, and confirms amounts match exactly.
Cleans up all test data in a finally block regardless of outcome.
"""
import datetime
import os
from decimal import Decimal

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from models import Base, Category, Expense, User

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]

TEST_EMAIL = "persist_verify@nanoclaw.test"

# Five rows with distinct amounts that are unlikely to collide with real data.
TEST_ROWS = [
    {"amount": Decimal("1500.00"), "description": "__persist_test_1__"},
    {"amount": Decimal("2750.50"), "description": "__persist_test_2__"},
    {"amount": Decimal("350.00"),  "description": "__persist_test_3__"},
    {"amount": Decimal("8999.99"), "description": "__persist_test_4__"},
    {"amount": Decimal("450.25"),  "description": "__persist_test_5__"},
]


def _make_engine():
    eng = create_engine(DATABASE_URL)
    if eng.dialect.name == "sqlite":
        @event.listens_for(eng, "connect")
        def _fk_on(dbapi_conn, _rec):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.close()
    return eng


def _get_category(session: Session) -> Category:
    cat = session.query(Category).first()
    if cat is None:
        raise RuntimeError("No categories found. Run tools/db_setup.py first.")
    return cat


# ── Phase 1: insert and commit ────────────────────────────────────────────────

def insert_test_rows() -> tuple[int, list[int]]:
    """Returns (user_id, [expense_ids])."""
    eng = _make_engine()
    try:
        Base.metadata.create_all(eng)
        with Session(eng) as session, session.begin():
            category = _get_category(session)

            user = User(name="Persist Verify User", email=TEST_EMAIL)
            session.add(user)
            session.flush()

            expense_ids = []
            for row in TEST_ROWS:
                exp = Expense(
                    amount=row["amount"],
                    description=row["description"],
                    date=datetime.date.today(),
                    user_id=user.id,
                    category_id=category.id,
                )
                session.add(exp)
                session.flush()
                expense_ids.append(exp.id)

            user_id = user.id
            # session.begin() commits here on clean exit
    finally:
        eng.dispose()  # close every connection in the pool

    return user_id, expense_ids


# ── Phase 2: reconnect and verify ─────────────────────────────────────────────

def verify_rows(expense_ids: list[int]) -> int:
    """Returns the number of rows found with correct amounts."""
    eng = _make_engine()
    try:
        with Session(eng) as session:
            found = 0
            for idx, exp_id in enumerate(expense_ids):
                row = session.get(Expense, exp_id)
                expected = TEST_ROWS[idx]["amount"]
                if row is not None and Decimal(str(row.amount)) == expected:
                    found += 1
            return found
    finally:
        eng.dispose()


# ── Phase 3: cleanup ──────────────────────────────────────────────────────────

def cleanup(user_id: int, expense_ids: list[int]) -> None:
    eng = _make_engine()
    try:
        with Session(eng) as session, session.begin():
            for exp_id in expense_ids:
                row = session.get(Expense, exp_id)
                if row:
                    session.delete(row)
            user = session.get(User, user_id)
            if user:
                session.delete(user)
    finally:
        eng.dispose()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== verify_persistence ===\n")
    user_id = None
    expense_ids = []

    try:
        print("[1/3] Inserting 5 test rows...")
        user_id, expense_ids = insert_test_rows()
        print(f"      inserted expense IDs: {expense_ids}")

        print("\n[2/3] Engine disposed. Opening brand-new connection...")
        found = verify_rows(expense_ids)

        total = len(TEST_ROWS)
        if found == total:
            print(f"\nPERSISTENCE VERIFIED: {found}/{total} rows survived reconnection")
        else:
            print(f"\nFAILURE: only {found}/{total} rows found after reconnection")

    finally:
        if expense_ids or user_id:
            print("\n[3/3] Cleaning up test rows...")
            cleanup(user_id, expense_ids)
            print("      test rows deleted")


if __name__ == "__main__":
    main()
