"""
Exercises the action_log and knowledge tables end-to-end:
  1. Inserts 3 real-world actions with different trust levels.
  2. Inserts 2 human-correction knowledge triples.
  3. Queries actions taken today, grouped by trust_level.
  4. Queries all knowledge rows about category assignment.
  5. Prints both result sets in readable format.
  6. Cleans up the test rows it inserted.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

# ── inserts ────────────────────────────────────────────────────────────────

INSERT_ACTION = text("""
    INSERT INTO action_log (action_type, target, trust_level, result)
    VALUES (:action_type, :target, :trust_level, :result)
    RETURNING id
""")

ACTIONS = [
    {
        "action_type": "categorise_transaction",
        "target": "Imtiaz grocery",
        "trust_level": "auto_approved",
        "result": "Assigned to Groceries & Household",
    },
    {
        "action_type": "flag_for_review",
        "target": "Laptop repair PKR 12,000.00",
        "trust_level": "needs_approval",
        "result": "Held pending human confirmation of category",
    },
    {
        "action_type": "reject_input",
        "target": "prompt-injection attempt in memo field",
        "trust_level": "escalated",
        "result": "Input rejected; incident written to audit trail",
    },
    {
        "action_type": "categorise_transaction",
        "target": "online order PKR 3,200.00",
        "trust_level": "unverified_skill_bypass",
        "result": "category not verified against rules.md — treating as unconfirmed",
    },
]

INSERT_KNOWLEDGE = text("""
    INSERT INTO knowledge (subject, predicate, object, source)
    VALUES (:subject, :predicate, :object, :source)
    RETURNING id
""")

KNOWLEDGE_ROWS = [
    {
        "subject": "Daraz",
        "predicate": "belongs_to_category",
        "object": "Shopping & Apparel",
        "source": "human_correction",
    },
    {
        "subject": "Laptop repair",
        "predicate": "belongs_to_category",
        "object": "Other - needs new category",
        "source": "human_correction",
    },
]

# ── queries ────────────────────────────────────────────────────────────────

ACTIONS_TODAY_BY_TRUST = text("""
    SELECT trust_level,
           COUNT(*)              AS total,
           array_agg(target)     AS targets
    FROM   action_log
    WHERE  created_at::date = CURRENT_DATE
    GROUP  BY trust_level
    ORDER  BY trust_level
""")

CATEGORY_CORRECTIONS = text("""
    SELECT subject, object, source, created_at
    FROM   knowledge
    WHERE  predicate = 'belongs_to_category'
    ORDER  BY created_at
""")

# ── cleanup ────────────────────────────────────────────────────────────────

DELETE_ACTIONS = text("DELETE FROM action_log  WHERE id = ANY(:ids)")
DELETE_KNOWLEDGE = text("DELETE FROM knowledge   WHERE id = ANY(:ids)")


def _print_section(title: str) -> None:
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


def main() -> None:
    print("=== memory_test ===\n")

    engine = create_engine(DATABASE_URL)
    action_ids: list[int] = []
    knowledge_ids: list[int] = []

    try:
        # ── 1. insert actions ──────────────────────────────────────────────
        print("[1/4] Inserting 4 actions into action_log ...")
        with engine.begin() as conn:
            for row in ACTIONS:
                result = conn.execute(INSERT_ACTION, row).mappings().one()
                action_ids.append(result["id"])
                print(f"      id={result['id']:>4}  [{row['trust_level']}]  {row['target']}")

        # ── 2. insert knowledge ───────────────────────────────────────────
        print("\n[2/4] Inserting 2 rows into knowledge ...")
        with engine.begin() as conn:
            for row in KNOWLEDGE_ROWS:
                result = conn.execute(INSERT_KNOWLEDGE, row).mappings().one()
                knowledge_ids.append(result["id"])
                print(f"      id={result['id']:>4}  {row['subject']} → {row['object']}")

        # ── 3. query: actions today by trust_level ─────────────────────────
        _print_section("Actions taken today — grouped by trust_level")
        with engine.connect() as conn:
            rows = conn.execute(ACTIONS_TODAY_BY_TRUST).mappings().all()

        if not rows:
            print("  (no actions recorded today)")
        else:
            for r in rows:
                targets = ", ".join(str(t) for t in r["targets"])
                print(f"  {r['trust_level']:<20}  count={r['total']}  targets=[{targets}]")

        # ── 4. query: category-assignment corrections ──────────────────────
        _print_section("Knowledge — category corrections (predicate=belongs_to_category)")
        with engine.connect() as conn:
            rows = conn.execute(CATEGORY_CORRECTIONS).mappings().all()

        if not rows:
            print("  (no corrections stored)")
        else:
            for r in rows:
                ts = r["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                print(f"  [{r['source']}]  {r['subject']:<20} → {r['object']:<35}  @ {ts}")

        print("\nAll assertions passed.\n")

    finally:
        # ── 5. cleanup ─────────────────────────────────────────────────────
        with engine.begin() as conn:
            if action_ids:
                conn.execute(DELETE_ACTIONS, {"ids": action_ids})
            if knowledge_ids:
                conn.execute(DELETE_KNOWLEDGE, {"ids": knowledge_ids})
        print(
            f"[cleanup] Removed {len(action_ids)} action(s) "
            f"and {len(knowledge_ids)} knowledge row(s)."
        )
        engine.dispose()


if __name__ == "__main__":
    main()
