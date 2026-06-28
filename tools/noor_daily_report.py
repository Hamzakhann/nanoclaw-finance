#!/opt/miniconda3/bin/python3
"""
noor_daily_report.py
Sends yesterday's PKR expense summary to Telegram.
Runs standalone under launchd at 8am — no terminal, no FastAPI.
"""

import logging
import os
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ── Absolute paths (launchd has no CWD or user environment) ──────────────────

_SCRIPT_DIR = Path(__file__).resolve().parent      # /opt/agents/nanoclaw-finance/tools/
_AGENT_ROOT = _SCRIPT_DIR.parent                   # /opt/agents/nanoclaw-finance/
_AGENTS_DIR = _AGENT_ROOT.parent                   # /opt/agents/

ENV_PATH = _AGENTS_DIR / "config" / ".env"         # /opt/agents/config/.env
LOG_DIR  = _AGENT_ROOT / "logs"
LOG_PATH = LOG_DIR / "noor_daily_report.log"

# ── Bootstrap: env + logging must succeed before anything else ────────────────

load_dotenv(dotenv_path=ENV_PATH)

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("noor.daily_report")

# ── Config ────────────────────────────────────────────────────────────────────

DATABASE_URL     = os.environ["DATABASE_URL"]
TELEGRAM_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
TELEGRAM_API     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Recommendation thresholds (rules.md + task spec)
_DINING_PCT_CAP = Decimal("30")    # Dining Out > 30% of total  → rule 1
_LARGE_CAT_CAP  = Decimal("10000") # Any category total > 10k   → rule 2
_HIGH_DAY_CAP   = Decimal("20000") # Day total > 20k            → rule 3
_FLAG_TXN_CAP   = Decimal("50000") # Individual txn (verify.md §Review Triggers)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# ── Formatting ────────────────────────────────────────────────────────────────


def fmt_pkr(amount: object) -> str:
    """Format any numeric value as PKR X,XXX.XX — never float."""
    return f"PKR {Decimal(str(amount)):,.2f}"


def _table(totals: dict[str, Decimal], grand_total: Decimal) -> str:
    """Aligned category/amount table with separator and grand total."""
    col_w = max(max(len(c) for c in totals), 5) + 2
    pkr_w = max(
        max(len(fmt_pkr(v)) for v in totals.values()),
        len(fmt_pkr(grand_total)),
    )
    sep = "─" * (col_w + 1 + pkr_w)
    lines: list[str] = []
    for cat in sorted(totals):
        lines.append(f"{cat:<{col_w}} {fmt_pkr(totals[cat]):>{pkr_w}}")
    lines.append(sep)
    lines.append(f"{'Total':<{col_w}} {fmt_pkr(grand_total):>{pkr_w}}")
    return "\n".join(lines)


# ── Data layer ────────────────────────────────────────────────────────────────


def _query_expenses(target_date: date) -> list[dict]:
    """Return all expenses for target_date as plain dicts with abs() amounts."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT e.amount, e.description, c.name AS category
                FROM   expenses e
                JOIN   categories c ON e.category_id = c.id
                WHERE  e.date = :d
                ORDER  BY e.amount DESC
            """),
            {"d": target_date},
        )
        return [
            {
                "amount":      abs(Decimal(str(r.amount))),
                "description": r.description,
                "category":    r.category,
            }
            for r in rows
        ]


def _aggregate(rows: list[dict]) -> tuple[dict[str, Decimal], Decimal, dict]:
    """(category totals, grand total, largest single expense)."""
    totals: dict[str, Decimal] = {}
    for row in rows:
        totals.setdefault(row["category"], Decimal("0"))
        totals[row["category"]] += row["amount"]
    grand_total = sum(totals.values(), Decimal("0"))
    largest = max(rows, key=lambda r: r["amount"])
    return totals, grand_total, largest


# ── Recommendation ────────────────────────────────────────────────────────────


def _recommend(totals: dict[str, Decimal], grand_total: Decimal) -> str:
    """Return the first matching recommendation rule. Exactly one fires."""
    # Rule 1 — Dining Out > 30 % of total
    dining = totals.get("Dining Out", Decimal("0"))
    if grand_total > 0 and (dining / grand_total * 100) > _DINING_PCT_CAP:
        pct = int(dining / grand_total * 100)
        return (
            f"💡 Dining Out was {pct}% of yesterday's spend ({fmt_pkr(dining)}). "
            "Consider cooking at home to save."
        )

    # Rule 2 — Any single category total > PKR 10,000; flag the largest
    heavy = {c: t for c, t in totals.items() if t > _LARGE_CAT_CAP}
    if heavy:
        top_cat = max(heavy, key=lambda c: heavy[c])
        return (
            f"💡 {top_cat} reached {fmt_pkr(heavy[top_cat])} yesterday "
            "— worth a closer look."
        )

    # Rule 3 — Day total > PKR 20,000
    if grand_total > _HIGH_DAY_CAP:
        return f"💡 High spend day — review attached ({fmt_pkr(grand_total)} total)."

    # Default
    return "💡 Spending looks normal for your patterns."


# ── Message builder ───────────────────────────────────────────────────────────


def _build_message(
    report_date: date,
    rows: list[dict],
    totals: dict[str, Decimal],
    grand_total: Decimal,
    largest: dict,
) -> str:
    header = f"📊 Daily Report — {report_date.strftime('%d %b %Y')}"
    body   = _table(totals, grand_total)
    largest_line = (
        f"📌 Largest: {largest['description']} — "
        f"{fmt_pkr(largest['amount'])} ({largest['category']})"
    )

    parts: list[str] = [header, body, largest_line]

    # verify.md §Review Triggers: flag every transaction over PKR 50,000
    flagged = [r for r in rows if r["amount"] > _FLAG_TXN_CAP]
    if flagged:
        names = ", ".join(r["description"] for r in flagged)
        parts.append(
            f"⚠️ {len(flagged)} transaction(s) over PKR 50,000 — manual review needed\n"
            f"   {names}"
        )

    parts.append(_recommend(totals, grand_total))
    return "\n\n".join(parts)


# ── Telegram ──────────────────────────────────────────────────────────────────


def _send_telegram(message: str) -> None:
    resp = httpx.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": message},
        timeout=15,
    )
    resp.raise_for_status()


# ── Runs table ────────────────────────────────────────────────────────────────


def _open_run() -> int:
    """Insert a 'running' row and return its id."""
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO runs (trigger, status) "
                "VALUES ('scheduled', 'running') RETURNING id"
            )
        )
        return int(result.scalar_one())


def _close_run(run_id: int, status: str, error: Optional[str] = None) -> None:
    """Mark the run as completed or failed."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE runs "
                "SET status = :status, finished_at = NOW(), error = :error "
                "WHERE id = :id"
            ),
            {"status": status, "error": error, "id": run_id},
        )


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> int:
    yesterday = date.today() - timedelta(days=1)
    log.info("noor_daily_report starting for %s", yesterday)

    # Open run record — non-fatal: a missing runs table must not stop the report.
    run_id: Optional[int] = None
    try:
        run_id = _open_run()
        log.info("Opened run id=%d", run_id)
    except Exception as exc:
        log.warning("Could not open run record: %s", exc)

    try:
        rows = _query_expenses(yesterday)

        if not rows:
            message = (
                f"📊 Daily Report — {yesterday.strftime('%d %b %Y')}\n\n"
                "No expenses recorded yesterday."
            )
            log.info("No expenses for %s — sending empty report", yesterday)
        else:
            totals, grand_total, largest = _aggregate(rows)
            message = _build_message(yesterday, rows, totals, grand_total, largest)
            log.info(
                "%d expense(s), %d categor(y/ies), total %s",
                len(rows),
                len(totals),
                fmt_pkr(grand_total),
            )

        _send_telegram(message)
        log.info("Message sent to chat_id=%d", TELEGRAM_CHAT_ID)

        if run_id is not None:
            _close_run(run_id, "completed")
            log.info("Run id=%d marked completed", run_id)

        return 0

    except Exception as exc:
        log.exception("noor_daily_report failed: %s", exc)
        if run_id is not None:
            try:
                _close_run(run_id, "failed", str(exc)[:500])
            except Exception as close_exc:
                log.exception("Could not mark run as failed: %s", close_exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
