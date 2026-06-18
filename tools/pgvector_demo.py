"""
pgvector similarity-search demo.

Embeds 10 expense descriptions, stores them in expenses.embedding (vector(1536)),
then finds the 3 most similar rows to a query string using the <-> L2 operator.

Embedding source (in priority order):
  1. OpenAI text-embedding-3-small  — requires OPENAI_API_KEY in .env
  2. Seeded mock (random normalised vector) — used automatically when no key

Note: text-embedding-3-small is an OpenAI model.  Anthropic does not offer
an embedding API.  Swap the embed() call here if you switch providers later.
"""
import hashlib
import math
import os
import random
from decimal import Decimal
import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from models import Base, Category

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

TEST_EMAIL = "pgvec_demo@nanoclaw.test"
TEST_AMOUNT = Decimal("500.00")
TEST_DATE = datetime.date.today()

TEST_DESCRIPTIONS = [
    "Imtiaz grocery store",
    "Shell petrol pump",
    "K-Electric monthly bill",
    "Careem ride to office",
    "Naheed Superstore shopping",
    "PSO fuel station",
    "Foodpanda dinner order",
    "Jazz monthly recharge",
    "Metro Cash and Carry",
    "Uber to airport",
]

QUERY_DESCRIPTION = "grocery shopping at supermarket"

UPSERT_USER = text("""
    INSERT INTO users (name, email, created_at)
    VALUES (:name, :email, NOW())
    ON CONFLICT (email) DO NOTHING
""")

SELECT_USER_ID = text("SELECT id FROM users WHERE email = :email")

INSERT_EXPENSE = text("""
    INSERT INTO expenses
        (amount, description, date, created_at, category_id, user_id,
         idempotency_key, embedding)
    VALUES
        (:amount, :description, :date, NOW(), :category_id, :user_id,
         :idempotency_key, CAST(:embedding AS vector))
    ON CONFLICT (idempotency_key) DO NOTHING
""")

SIMILARITY_SEARCH = text("""
    SELECT description
    FROM expenses
    WHERE user_id = :user_id
    ORDER BY embedding <-> CAST(:query_vec AS vector)
    LIMIT 3
""")

SELECT_USER_FOR_PURGE = text("SELECT id FROM users WHERE email = :email")
DELETE_USER_EXPENSES = text("DELETE FROM expenses WHERE user_id = :uid")
DELETE_USER = text("DELETE FROM users WHERE id = :uid")


# ── Embedding ─────────────────────────────────────────────────────────────────

def _openai_embed(description: str) -> list[float] | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.embeddings.create(model="text-embedding-3-small", input=description)
        return resp.data[0].embedding
    except Exception as exc:
        print(f"      OpenAI error ({exc}), falling back to mock")
        return None


def _mock_embed(description: str) -> list[float]:
    """Seeded random unit vector — deterministic for a given string."""
    seed = int(hashlib.md5(description.encode()).hexdigest(), 16) % (2 ** 32)
    rng = random.Random(seed)
    vec = [rng.gauss(0, 1) for _ in range(1536)]
    mag = math.sqrt(sum(x * x for x in vec))
    return [x / mag for x in vec]


def embed(description: str, use_mock: bool) -> list[float]:
    if not use_mock:
        result = _openai_embed(description)
        if result is not None:
            return result
    return _mock_embed(description)


def purge_test_user(conn, email: str) -> int:
    """Delete a test user and their expenses (expenses first to satisfy FK)."""
    uid = conn.execute(SELECT_USER_FOR_PURGE, {"email": email}).scalar()
    if uid is None:
        return 0
    conn.execute(DELETE_USER_EXPENSES, {"uid": uid})
    conn.execute(DELETE_USER, {"uid": uid})
    return 1


def fmt_vec(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


def idem_key(description: str) -> str:
    raw = f"pgvec_demo:{TEST_DATE}:{description}"
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== pgvector_demo ===\n")

    use_mock = not bool(os.environ.get("OPENAI_API_KEY"))
    embed_source = "mock (seeded random)" if use_mock else "OpenAI text-embedding-3-small"
    print(f"embedding source : {embed_source}")

    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)

    try:
        # --- purge stale test data from a prior crashed run ---
        with engine.begin() as conn:
            purged = purge_test_user(conn, TEST_EMAIL)
            if purged:
                print(f"purged stale row(s) from prior run\n")

        # --- resolve category and test user ---
        with Session(engine) as session:
            category = session.query(Category).first()
            if category is None:
                raise RuntimeError("No categories found. Run tools/db_setup.py first.")
            category_id = category.id

        with engine.begin() as conn:
            conn.execute(UPSERT_USER, {"name": "PGVector Demo User", "email": TEST_EMAIL})
            user_id = conn.execute(SELECT_USER_ID, {"email": TEST_EMAIL}).scalar_one()

        # --- embed and insert 10 rows ---
        print(f"\n[1/3] Inserting {len(TEST_DESCRIPTIONS)} expense rows with embeddings ...")
        for desc in TEST_DESCRIPTIONS:
            vec = embed(desc, use_mock)
            key = idem_key(desc)
            with engine.begin() as conn:
                conn.execute(INSERT_EXPENSE, {
                    "amount": str(TEST_AMOUNT),
                    "description": desc,
                    "date": TEST_DATE,
                    "category_id": category_id,
                    "user_id": user_id,
                    "idempotency_key": key,
                    "embedding": fmt_vec(vec),
                })
            print(f"      inserted : {desc}")

        # --- embed query and run similarity search ---
        print(f'\n[2/3] Query : "{QUERY_DESCRIPTION}"')
        query_vec = embed(QUERY_DESCRIPTION, use_mock)

        with engine.connect() as conn:
            rows = conn.execute(SIMILARITY_SEARCH, {
                "user_id": user_id,
                "query_vec": fmt_vec(query_vec),
            }).fetchall()

        print("\n      Top 3 most similar expenses:")
        for i, row in enumerate(rows, 1):
            print(f"      {i}. {row[0]}")

        if use_mock:
            print(
                "\nNOTE: mock embeddings are random — results are meaningless. "
                "Use real embeddings (e.g. text-embedding-3-small) for semantic accuracy."
            )

    finally:
        with engine.begin() as conn:
            purge_test_user(conn, TEST_EMAIL)
        print("\n[3/3] Test rows cleaned up")
        engine.dispose()


if __name__ == "__main__":
    main()
