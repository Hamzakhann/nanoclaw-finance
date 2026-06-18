"""
Transaction atomicity test.

Inserts a User + linked Expense inside a single session, deliberately raises
an exception before commit, rolls back, then verifies neither row survived.
"""
import datetime

from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Base, Category, Expense, User, engine

TEST_EMAIL = "test@test.com"
TEST_DESCRIPTION = "__transaction_atomicity_test__"


def _enable_sqlite_fk(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


def _register_sqlite_fk_pragma():
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_fk)


def _get_real_category(session: Session) -> Category:
    category = session.query(Category).first()
    if category is None:
        raise RuntimeError(
            "No categories found. Run tools/db_setup.py first to seed categories."
        )
    return category


def run_transaction_test() -> None:
    _register_sqlite_fk_pragma()
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # --- Phase 1: insert, explode, rollback ---
        try:
            category = _get_real_category(session)

            user = User(name="Test User", email=TEST_EMAIL)
            session.add(user)
            session.flush()  # assigns user.id without committing

            expense = Expense(
                amount="250.00",
                description=TEST_DESCRIPTION,
                date=datetime.date.today(),
                user_id=user.id,
                category_id=category.id,
            )
            session.add(expense)
            session.flush()

            # Deliberate failure before any commit.
            raise RuntimeError("Deliberate pre-commit failure — testing atomicity")

        except RuntimeError:
            session.rollback()

        # --- Phase 2: verify nothing survived ---
        leaked_users = (
            session.query(User).filter_by(email=TEST_EMAIL).count()
        )
        leaked_expenses = (
            session.query(Expense).filter_by(description=TEST_DESCRIPTION).count()
        )

        total_leaked = leaked_users + leaked_expenses

        if total_leaked == 0:
            print("ATOMIC: rollback successful — zero partial rows written")
        else:
            parts = []
            if leaked_users:
                parts.append(f"{leaked_users} user row(s)")
            if leaked_expenses:
                parts.append(f"{leaked_expenses} expense row(s)")
            print(f"FAILURE: partial write detected — {' and '.join(parts)} found")


if __name__ == "__main__":
    run_transaction_test()
