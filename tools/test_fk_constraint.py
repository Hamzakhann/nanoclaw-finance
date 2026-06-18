"""
FK constraint smoke-test.

Attempts to insert an Expense referencing category_id=999, which does not
exist.  Expects an IntegrityError.  Rolls back all test data regardless of
outcome so the DB is left unchanged.

SQLite note: FK enforcement is off by default.  The event listener below
enables it per-connection so the test is accurate against both SQLite and
PostgreSQL (Neon).
"""
import datetime

from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Base, Expense, User, engine


def _enable_sqlite_fk(dbapi_conn, _connection_record):
    """Turn on FK enforcement for every new SQLite connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


def _register_sqlite_fk_pragma():
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_fk)


def run_fk_test() -> None:
    _register_sqlite_fk_pragma()

    # Ensure tables exist before testing.
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # Wrap everything in one transaction that will be rolled back,
        # so no test data survives regardless of outcome.
        with session.begin():
            # Insert a real user so user_id FK is valid; only category_id
            # will be intentionally broken.
            test_user = User(name="FK Test User", email="fk_test@nanoclaw.test")
            session.add(test_user)
            session.flush()  # assigns test_user.id

            bad_expense = Expense(
                amount="100.00",
                description="FK constraint test — should be rejected",
                date=datetime.date.today(),
                user_id=test_user.id,
                category_id=999,  # does not exist
            )

            try:
                session.add(bad_expense)
                session.flush()
                # If flush succeeded, FK is not being enforced.
                print("FAILURE — FK constraint not enforced")
            except IntegrityError:
                print("FK constraint working correctly — bad insert rejected")

            # Always roll back so neither the test user nor the bad expense
            # persists in the database.
            session.rollback()


if __name__ == "__main__":
    run_fk_test()
