import sys
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from models import Base, Category, engine

CATEGORIES = [
    (
        "Food & Groceries",
        "General stores, kiryana shops, supermarkets, and online grocery services.",
    ),
    (
        "Dining Out",
        "Restaurants, cafes, fast food outlets, food delivery apps, and takeaway meals.",
    ),
    (
        "Transport",
        "Fuel, ride-hailing, public transport, and vehicle running costs.",
    ),
    (
        "Utilities",
        "Electricity, gas, water, internet, and phone bills or top-ups.",
    ),
    (
        "Health & Medical",
        "Doctor consultations, pharmacy, lab tests, hospital fees, and health insurance.",
    ),
    (
        "Education",
        "School or college fees, tuition, books, stationery, and online courses.",
    ),
    (
        "Shopping & Apparel",
        "Clothing, shoes, accessories, and general non-grocery retail shopping.",
    ),
    (
        "Entertainment & Subscriptions",
        "Cinema, streaming services, games, events, and hobby expenses.",
    ),
    (
        "Savings & Investments",
        "Savings transfers, investments, prize bonds, and mutual funds.",
    ),
    (
        "Other",
        "Catch-all for unmatched transactions. Requires manual review before weekly report.",
    ),
]


def create_tables() -> None:
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())

    Base.metadata.create_all(engine)

    new_tables = set(Base.metadata.tables.keys()) - existing
    for table in sorted(Base.metadata.tables.keys()):
        status = "created" if table in new_tables else "already exists"
        print(f"  table '{table}': {status}")


def seed_categories(session: Session) -> None:
    for name, description in CATEGORIES:
        existing = session.query(Category).filter_by(name=name).first()
        if existing:
            print(f"  category '{name}': already seeded")
        else:
            session.add(Category(name=name, description=description))
            session.flush()
            print(f"  category '{name}': seeded")
    session.commit()


def main() -> None:
    print("=== nanoclaw-finance db setup ===\n")

    print("[1/2] Creating tables...")
    create_tables()

    print("\n[2/2] Seeding categories...")
    with Session(engine) as session:
        seed_categories(session)

    print("\nDone.")


if __name__ == "__main__":
    main()
