"""
Crash detection test.

Inserts a run that looks like it started 15 minutes ago and never finished,
runs the crash detection query, confirms the row is found, then cleans up.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

INSERT_CRASHED_RUN = text("""
    INSERT INTO runs (started_at, finished_at, status, trigger)
    VALUES (NOW() - INTERVAL '15 minutes', NULL, 'running', 'crash_detection_test')
    RETURNING id, started_at
""")

CRASH_DETECTION_QUERY = text("""
    SELECT id, started_at, error
    FROM runs
    WHERE status = 'running'
      AND finished_at IS NULL
      AND started_at < NOW() - INTERVAL '10 minutes'
""")

DELETE_RUN = text("DELETE FROM runs WHERE id = :run_id")


def main() -> None:
    print("=== crash_detection_test ===\n")

    engine = create_engine(DATABASE_URL)
    run_id = None

    try:
        with engine.begin() as conn:
            row = conn.execute(INSERT_CRASHED_RUN).mappings().one()
            run_id = row["id"]
            print(f"[1/3] Inserted simulated crashed run  id={run_id}")

        with engine.connect() as conn:
            crashed_runs = conn.execute(CRASH_DETECTION_QUERY).mappings().all()

        print(f"[2/3] Crash detection query returned {len(crashed_runs)} row(s)")

        matched = [r for r in crashed_runs if r["id"] == run_id]

        if matched:
            r = matched[0]
            print(
                f"\nCRASH DETECTED: run ID {r['id']} "
                f"started at {r['started_at']}, never finished"
            )
        else:
            print(
                f"\nFAILURE: inserted run {run_id} did not appear "
                "in crash detection results"
            )

    finally:
        if run_id is not None:
            with engine.begin() as conn:
                conn.execute(DELETE_RUN, {"run_id": run_id})
            print(f"\n[3/3] Cleaned up test run  id={run_id}")
        engine.dispose()


if __name__ == "__main__":
    main()
