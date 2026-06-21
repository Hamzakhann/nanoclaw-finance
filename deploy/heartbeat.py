import signal
import sys
import time
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
import os

ENV_PATH = Path(__file__).resolve().parent.parent / "config" / ".env"
load_dotenv(dotenv_path=ENV_PATH)

DATABASE_URL = os.environ["DATABASE_URL"]

_running = True


def _handle_sigterm(_signum, _frame):
    global _running
    print("shutting down", flush=True)
    _running = False


signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT, _handle_sigterm)


def heartbeat():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT NOW()")
        row = cur.fetchone()
        now = row[0] if row else "?"
        cur.close()
        conn.close()
        print(f"heartbeat ok — db time: {now}", flush=True)
    except Exception as e:
        print(f"heartbeat error: {e}", file=sys.stderr, flush=True)


def main():
    print("heartbeat starting", flush=True)
    while _running:
        heartbeat()
        for _ in range(60):
            if not _running:
                break
            time.sleep(1)
    print("heartbeat stopped", flush=True)


if __name__ == "__main__":
    main()
