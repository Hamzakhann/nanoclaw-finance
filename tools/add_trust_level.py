"""
Migration: widen action_log.trust_level and extend its CHECK constraint.

Step 1 — widen column: VARCHAR(20) → VARCHAR(40)
  'unverified_skill_bypass' is 24 characters; the original width silently
  truncates it.  Idempotent: skipped if width is already >= 40.

Step 2 — extend CHECK constraint:
  Old values: auto_approved | needs_approval | escalated
  New values: auto_approved | needs_approval | escalated | unverified_skill_bypass
  PostgreSQL does not support ALTER CONSTRAINT in place, so the constraint is
  dropped and recreated.  Idempotent: skipped if value is already present.

Safe to run multiple times.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

TABLE = "action_log"
COLUMN = "trust_level"
NEW_VALUE = "unverified_skill_bypass"
NEW_CONSTRAINT_NAME = "action_log_trust_level_check"
ALL_VALUES = ("auto_approved", "needs_approval", "escalated", NEW_VALUE)

FIND_COLUMN_WIDTH = text("""
    SELECT character_maximum_length
    FROM   information_schema.columns
    WHERE  table_name  = 'action_log'
      AND  column_name = 'trust_level'
""")

WIDEN_COLUMN = text(
    "ALTER TABLE action_log ALTER COLUMN trust_level TYPE VARCHAR(40)"
)

FIND_CONSTRAINT = text("""
    SELECT conname,
           pg_get_constraintdef(oid) AS check_clause
    FROM   pg_constraint
    WHERE  conrelid = 'action_log'::regclass
      AND  contype  = 'c'
      AND  conname  LIKE '%trust_level%'
    LIMIT  1
""")

DROP_CONSTRAINT = "ALTER TABLE {table} DROP CONSTRAINT {name}"

ADD_CONSTRAINT = (
    "ALTER TABLE {table} "
    "ADD CONSTRAINT {name} "
    "CHECK ({column} IN ({values}))"
)


def find_constraint(conn) -> tuple[str, str] | None:
    """Return (name, check_clause) for the trust_level constraint, or None."""
    row = conn.execute(FIND_CONSTRAINT).mappings().one_or_none()
    return (row["conname"], row["check_clause"]) if row else None


def main() -> None:
    print("=== add_trust_level migration ===\n")

    engine = create_engine(DATABASE_URL)
    try:
        # ── step 1: widen column if still too narrow ───────────────────────
        with engine.connect() as conn:
            row = conn.execute(FIND_COLUMN_WIDTH).mappings().one_or_none()
        current_width = row["character_maximum_length"] if row else None
        print(f"[1/4] trust_level column width: {current_width}")

        if current_width is not None and current_width < 40:
            print("      too narrow for 'unverified_skill_bypass' — widening to VARCHAR(40) ...")
            with engine.begin() as conn:
                conn.execute(WIDEN_COLUMN)
            print("      column widened successfully")
        else:
            print("      already wide enough — skipping")

        # ── step 2: find CHECK constraint ──────────────────────────────────
        with engine.connect() as conn:
            constraint = find_constraint(conn)

        if constraint is None:
            print(f"WARNING: no trust_level CHECK constraint found on {TABLE}.")
            print("         Has memory_schema.sql been applied? Aborting.")
            return

        name, clause = constraint
        print(f"\n[2/4] Found constraint  name={name!r}")
        print(f"      clause: {clause}")

        if NEW_VALUE in clause:
            print(f"\n[3/4] '{NEW_VALUE}' already present — nothing to do.")
            return

        print(f"\n[3/4] '{NEW_VALUE}' not yet present — applying migration ...")

        values_sql = ", ".join(f"'{v}'" for v in ALL_VALUES)
        with engine.begin() as conn:
            conn.execute(text(DROP_CONSTRAINT.format(table=TABLE, name=name)))
            conn.execute(text(ADD_CONSTRAINT.format(
                table=TABLE,
                name=NEW_CONSTRAINT_NAME,
                column=COLUMN,
                values=values_sql,
            )))

        # verify
        with engine.connect() as conn:
            constraint_after = find_constraint(conn)

        if constraint_after and NEW_VALUE in constraint_after[1]:
            print(f"\n[4/4] Constraint updated successfully.")
            print(f"      new clause: {constraint_after[1]}")
        else:
            print("FAILURE: constraint not found or value still missing after ALTER.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
