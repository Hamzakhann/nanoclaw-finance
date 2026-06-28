import hashlib
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

# Sibling imports from the tools/ directory
sys.path.insert(0, str(Path(__file__).parent))
from category_tagger import classify
from models import Category, Expense, User, engine

load_dotenv(
    dotenv_path=Path(__file__).parent.parent / ".env",
    override=True
)

TELEGRAM_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is empty in .env")

TELEGRAM_API: str = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

LARGE_AMOUNT_THRESHOLD = Decimal("50000")
SOFT_FLAG_THRESHOLD = Decimal("10000")

# ── Logging ───────────────────────────────────────────────────────────────────

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "noor_webhook.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("noor.webhook")

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Noor Finance Webhook")

# ── Telegram payload models ───────────────────────────────────────────────────


class TelegramChat(BaseModel):
    id: int


class TelegramMessage(BaseModel):
    message_id: int
    chat: TelegramChat
    text: Optional[str] = None


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None


# ── Helpers ───────────────────────────────────────────────────────────────────


def fmt_pkr(amount: object) -> str:
    # Accepts Decimal, int, float, or SQLAlchemy numeric column values.
    return f"PKR {Decimal(str(amount)):,.2f}"


async def send_telegram_message(
    chat_id: int,
    message: str,
    parse_mode: Optional[str] = None,
) -> None:
    payload: dict[str, object] = {"chat_id": chat_id, "text": message}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
    if not resp.is_success:
        log.error(
            "Telegram sendMessage failed: status=%d body=%s",
            resp.status_code,
            resp.text[:200],
        )


def _log_action(
    session: Session,
    action_type: str,
    target: Optional[str],
    trust_level: str,
    result: str,
) -> None:
    session.execute(
        text(
            "INSERT INTO action_log (action_type, target, trust_level, result) "
            "VALUES (:action_type, :target, :trust_level, :result)"
        ),
        {
            "action_type": action_type[:50],
            "target": (target or "")[:200],
            "trust_level": trust_level,
            "result": result[:500],
        },
    )
    session.commit()


# ── Intent types ─────────────────────────────────────────────────────────────


class Intent(str, Enum):
    TODAY = "today"
    YESTERDAY = "yesterday"
    WEEK = "week"
    MONTH = "month"
    REPORT = "report"
    UNDO = "undo"
    HELP = "help"
    ADD_EXPENSE = "add_expense"
    UNKNOWN = "unknown"


# Module-level aliases used by callers
INTENT_TODAY = Intent.TODAY
INTENT_YESTERDAY = Intent.YESTERDAY
INTENT_WEEK = Intent.WEEK
INTENT_MONTH = Intent.MONTH
INTENT_REPORT = Intent.REPORT
INTENT_UNDO = Intent.UNDO
INTENT_HELP = Intent.HELP
INTENT_ADD_EXPENSE = Intent.ADD_EXPENSE
INTENT_UNKNOWN = Intent.UNKNOWN


@dataclass(frozen=True)
class ParsedIntent:
    intent: Intent
    amount: Optional[Decimal] = None   # populated for INTENT_ADD_EXPENSE
    description: Optional[str] = None  # populated for INTENT_ADD_EXPENSE
    raw: str = ""                       # original stripped message


# ── Intent patterns ───────────────────────────────────────────────────────────

# Command patterns: anchored fullmatch, optional leading /
_COMMAND_PATTERNS: list[tuple[re.Pattern[str], Intent]] = [
    (re.compile(r"^/?today$", re.IGNORECASE), Intent.TODAY),
    (re.compile(r"^/?yesterday$", re.IGNORECASE), Intent.YESTERDAY),
    (re.compile(r"^/?last\s+week$", re.IGNORECASE), Intent.WEEK),
    (re.compile(r"^/?this\s+month$", re.IGNORECASE), Intent.MONTH),
    (re.compile(r"^/?(?:report|weekly)$", re.IGNORECASE), Intent.REPORT),
    (re.compile(r"^/?undo$", re.IGNORECASE), Intent.UNDO),
    (re.compile(r"^/?help$", re.IGNORECASE), Intent.HELP),
]

# Explicit "PKR <number>" — strongest signal, searched first
_PKR_AMOUNT_RE = re.compile(
    r"\bPKR\s+(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\b",
    re.IGNORECASE,
)

# Standalone number with word boundaries — fallback
_NUM_RE = re.compile(
    r"\b(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\b"
)

# Skip quantities like "2 burgers 450"; any amount below this is likely a count
_MIN_EXPENSE_AMOUNT = Decimal("10")


# ── Intent helpers ────────────────────────────────────────────────────────────


def _match_command(lower: str) -> Optional[Intent]:
    for pattern, intent in _COMMAND_PATTERNS:
        if pattern.match(lower):
            return intent
    return None


def _extract_expense(text: str) -> tuple[Optional[Decimal], Optional[str]]:
    """
    Return (amount, description) from an expense-like message.
    Searches for PKR-prefixed number first, then any standalone number >= 10.
    Description is the remaining text after the amount token is removed.
    Returns (None, None) when no qualifying number is found.
    """
    def _split_around(m: re.Match[str], captured_group: int = 1) -> tuple[Decimal, Optional[str]]:
        raw_num = m.group(captured_group).replace(",", "")
        amount = Decimal(raw_num)
        before = text[: m.start()].strip()
        after = text[m.end() :].strip()
        desc_parts = " ".join(filter(None, [before, after]))
        desc = " ".join(desc_parts.split()) or None
        return amount, desc

    # Priority 1: explicit PKR prefix
    pkr_m = _PKR_AMOUNT_RE.search(text)
    if pkr_m:
        return _split_around(pkr_m)

    # Priority 2: first standalone number >= _MIN_EXPENSE_AMOUNT
    for num_m in _NUM_RE.finditer(text):
        amount = Decimal(num_m.group(1).replace(",", ""))
        if amount >= _MIN_EXPENSE_AMOUNT:
            return _split_around(num_m)

    return None, None


# ── parse_intent ──────────────────────────────────────────────────────────────


def parse_intent(message: str) -> ParsedIntent:
    """
    Classify a Telegram message into a ParsedIntent.

    Priority:
      1. Exact/close command match  → one of the INTENT_* command constants
      2. Contains a PKR amount      → INTENT_ADD_EXPENSE  (amount + description set)
      3. Otherwise                  → INTENT_UNKNOWN
    """
    stripped = message.strip()
    lower = stripped.lower()

    command = _match_command(lower)
    if command is not None:
        return ParsedIntent(intent=command, raw=stripped)

    amount, description = _extract_expense(stripped)
    if amount is not None:
        return ParsedIntent(
            intent=INTENT_ADD_EXPENSE,
            amount=amount,
            description=description,
            raw=stripped,
        )

    return ParsedIntent(intent=INTENT_UNKNOWN, raw=stripped)


# ── Command parser ────────────────────────────────────────────────────────────


def parse_command(raw: str) -> tuple[str, dict[str, str]]:
    """Return (intent, args). Intent is one of: add, report, help, unknown."""
    stripped = raw.strip()
    lower = stripped.lower()

    if lower in ("/help", "help"):
        return "help", {}

    if lower in ("/report", "/weekly", "report", "weekly"):
        return "report", {}

    # /add <amount> <description>
    m = re.match(r"^/add\s+(\d+(?:\.\d+)?)\s+(.+)$", stripped, re.IGNORECASE)
    if m:
        return "add", {"amount": m.group(1), "description": m.group(2).strip()}

    # Free text: leading number — "500 kfc lunch"
    m = re.match(r"^(\d+(?:\.\d+)?)\s+(.+)$", stripped)
    if m:
        return "add", {"amount": m.group(1), "description": m.group(2).strip()}

    # Free text: trailing number — "kfc lunch 500"
    m = re.match(r"^(.+?)\s+(\d+(?:\.\d+)?)$", stripped)
    if m:
        return "add", {"amount": m.group(2), "description": m.group(1).strip()}

    return "unknown", {"raw": stripped}


# ── Handler helpers ───────────────────────────────────────────────────────────


def _resolve_user(session: Session, chat_id: int) -> User:
    """Return the User for this chat_id, creating one automatically if none exists."""
    user = session.query(User).filter_by(telegram_chat_id=chat_id).first()
    if user is None:
        user = User(
            name="Hamza",
            email=f"telegram_{chat_id}@nanoclaw.local",
            telegram_chat_id=chat_id,
        )
        session.add(user)
        session.commit()
        log.info("auto-created user for chat_id=%d", chat_id)
    return user


def _today_total(session: Session, user_id: object) -> Decimal:
    """Sum of absolute expense amounts for user_id on today's date."""
    rows = (
        session.query(Expense)
        .filter(Expense.user_id == user_id, Expense.date == date.today())
        .all()
    )
    return sum((abs(Decimal(str(r.amount))) for r in rows), Decimal("0"))


def _format_table(
    header: str,
    totals: dict[str, Decimal],
    grand_total: Decimal,
    flagged_count: int = 0,
) -> str:
    """Left-aligned category column + right-aligned PKR column, with separator."""
    col_w = max(max(len(c) for c in totals), 5) + 2
    # widest PKR string across all values
    pkr_w = max(
        max(len(fmt_pkr(v)) for v in totals.values()),
        len(fmt_pkr(grand_total)),
    )
    sep = "─" * (col_w + 1 + pkr_w)

    lines: list[str] = [header, ""]
    for cat in sorted(totals):
        lines.append(f"{cat:<{col_w}} {fmt_pkr(totals[cat]):>{pkr_w}}")
    lines.append(sep)
    lines.append(f"{'Total':<{col_w}} {fmt_pkr(grand_total):>{pkr_w}}")

    if flagged_count:
        lines.append(f"\n⚠️  {flagged_count} item(s) over PKR 50,000 — flagged for review")

    return "\n".join(lines)


# ── Handlers ──────────────────────────────────────────────────────────────────


def handle_add_expense(amount: Decimal, description: str, chat_id: int) -> str:
    amount = abs(amount)
    description = (description or "").strip()

    if not description:
        return "Description missing — what did you spend on?"

    category_name = classify(description)
    today = date.today()
    idempotency_key = hashlib.sha256(
        f"{today}|{amount}|{description}".encode()
    ).hexdigest()

    with Session(engine) as session:
        # Duplicate check first — cheapest guard
        existing = (
            session.query(Expense)
            .options(joinedload(Expense.category))
            .filter_by(idempotency_key=idempotency_key)
            .first()
        )
        if existing:
            return (
                f"Already recorded: {fmt_pkr(existing.amount)} — {existing.category.name}\n"
                f"📝 {description}"
            )

        user = _resolve_user(session, chat_id)

        category = session.query(Category).filter_by(name=category_name).first()
        if category is None:
            category = session.query(Category).filter_by(name="Other").first()
        if category is None:
            return "Categories missing. Run: python tools/db_setup.py"

        expense = Expense(
            amount=amount,
            description=description,
            date=today,
            category_id=category.id,
            user_id=user.id,
            idempotency_key=idempotency_key,
        )
        session.add(expense)
        session.commit()

        # Read today's total after commit so it includes the new row
        daily_total = _today_total(session, user.id)

        trust = "escalated" if amount > LARGE_AMOUNT_THRESHOLD else "auto_approved"
        _log_action(
            session,
            "add_expense",
            description[:100],
            trust,
            f"{fmt_pkr(amount)} → {category_name}",
        )

    flagged = amount > LARGE_AMOUNT_THRESHOLD
    amt_display = f"⚠️ {fmt_pkr(amount)}" if flagged else fmt_pkr(amount)

    lines = [
        "✅ Saved",
        f"{amt_display} — {category_name}",
        f"📝 {description}",
        f"📊 Today's total: {fmt_pkr(daily_total)}",
    ]
    if flagged:
        lines.append("⚠️ Amount over PKR 50,000 — flagged for review")
    if category_name == "Other":
        lines.append("📋 No category matched — please categorise manually")

    return "\n".join(lines)


def handle_today(chat_id: int) -> str:
    today = date.today()
    header = f"📅 Today — {today.strftime('%d %b %Y')}"

    with Session(engine) as session:
        user = _resolve_user(session, chat_id)

        expenses = (
            session.query(Expense)
            .options(joinedload(Expense.category))
            .filter(Expense.user_id == user.id, Expense.date == today)
            .all()
        )
        if not expenses:
            return f"{header}\n\nNo expenses recorded today."

        totals: dict[str, Decimal] = {}
        for exp in expenses:
            totals.setdefault(exp.category.name, Decimal("0"))
            totals[exp.category.name] += abs(Decimal(str(exp.amount)))

        return _format_table(header, totals, sum(totals.values(), Decimal("0")))


def handle_week(chat_id: int) -> str:
    today = date.today()
    start = today - timedelta(days=6)
    header = (
        f"📅 Last 7 days — "
        f"{start.strftime('%d %b')} to {today.strftime('%d %b %Y')}"
    )

    with Session(engine) as session:
        user = _resolve_user(session, chat_id)

        expenses = (
            session.query(Expense)
            .options(joinedload(Expense.category))
            .filter(
                Expense.user_id == user.id,
                Expense.date >= start,
                Expense.date <= today,
            )
            .all()
        )
        if not expenses:
            return f"{header}\n\nNo expenses in the last 7 days."

        totals: dict[str, Decimal] = {}
        for exp in expenses:
            totals.setdefault(exp.category.name, Decimal("0"))
            totals[exp.category.name] += abs(Decimal(str(exp.amount)))

        return _format_table(header, totals, sum(totals.values(), Decimal("0")))


def handle_month(chat_id: int) -> str:
    today = date.today()
    start = today.replace(day=1)
    header = f"📅 {today.strftime('%B %Y')}"

    with Session(engine) as session:
        user = _resolve_user(session, chat_id)

        expenses = (
            session.query(Expense)
            .options(joinedload(Expense.category))
            .filter(
                Expense.user_id == user.id,
                Expense.date >= start,
                Expense.date <= today,
            )
            .all()
        )
        if not expenses:
            return f"{header}\n\nNo expenses recorded this month."

        totals: dict[str, Decimal] = {}
        flagged_count = 0
        for exp in expenses:
            amt = abs(Decimal(str(exp.amount)))
            totals.setdefault(exp.category.name, Decimal("0"))
            totals[exp.category.name] += amt
            if amt > LARGE_AMOUNT_THRESHOLD:
                flagged_count += 1

        return _format_table(
            header,
            totals,
            sum(totals.values(), Decimal("0")),
            flagged_count=flagged_count,
        )


def handle_undo(chat_id: int) -> str:
    with Session(engine) as session:
        user = _resolve_user(session, chat_id)

        latest = (
            session.query(Expense)
            .options(joinedload(Expense.category))
            .filter(Expense.user_id == user.id)
            .order_by(Expense.created_at.desc())
            .first()
        )
        if latest is None:
            return "No expenses on record to undo."

        return (
            f"↩️ Remove this entry?\n"
            f"{fmt_pkr(latest.amount)} — {latest.description} ({latest.category.name})\n"
            f"📅 {latest.date}\n"
            f"\nReply /confirm_undo to remove it."
        )


def handle_help(_chat_id: int) -> str:
    return (
        "*Noor Finance — Commands*\n"
        "\n"
        "*Add an expense:*\n"
        "  KFC lunch PKR 850\n"
        "  850 KFC lunch\n"
        "  petrol 450 shell\n"
        "\n"
        "*Reports:*\n"
        "  today\n"
        "  last week\n"
        "  this month\n"
        "  report\n"
        "\n"
        "*Other:*\n"
        "  undo — remove the last entry\n"
        "  help — show this list"
    )


def handle_unknown(_chat_id: int) -> str:
    return (
        "I didn't understand that. Try:\n"
        "\n"
        "• An expense: KFC lunch PKR 850\n"
        "• A command: today / last week / this month / report / undo"
    )


# ── Webhook endpoint ──────────────────────────────────────────────────────────


@app.post("/webhook")
async def webhook(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception as exc:
        log.warning("Non-JSON request body: %s", exc)
        return {"ok": True}

    try:
        update = TelegramUpdate.model_validate(body)
    except Exception as exc:
        log.warning("Unparseable Telegram update: %s", exc)
        return {"ok": True}

    if update.message is None:
        return {"ok": True}
    msg = update.message
    if not msg.text:
        return {"ok": True}

    chat_id = msg.chat.id
    text_in: str = msg.text

    log.info("update_id=%d chat_id=%d text=%r", update.update_id, chat_id, text_in)

    pi = parse_intent(text_in)
    log.info("intent=%s chat_id=%d", pi.intent, chat_id)

    reply = "Something went wrong. Please try again."
    parse_mode: Optional[str] = None

    try:
        if pi.intent == INTENT_ADD_EXPENSE:
            reply = handle_add_expense(
                pi.amount or Decimal("0"),
                pi.description or "",
                chat_id,
            )

        elif pi.intent == INTENT_TODAY:
            reply = handle_today(chat_id)

        elif pi.intent in (INTENT_WEEK, INTENT_REPORT):
            reply = handle_week(chat_id)

        elif pi.intent == INTENT_MONTH:
            reply = handle_month(chat_id)

        elif pi.intent == INTENT_UNDO:
            reply = handle_undo(chat_id)

        elif pi.intent == INTENT_HELP:
            reply = handle_help(chat_id)
            parse_mode = "Markdown"

        else:
            reply = handle_unknown(chat_id)

    except Exception as exc:
        log.exception("Handler error chat_id=%d intent=%s: %s", chat_id, pi.intent, exc)
        reply = "Something went wrong on my end. Please try again."
        try:
            with Session(engine) as err_session:
                _log_action(
                    err_session, "error", str(exc)[:100], "escalated", str(exc)[:200]
                )
        except Exception as log_exc:
            log.exception("Failed to log error to action_log: %s", log_exc)

    try:
        await send_telegram_message(chat_id, reply, parse_mode=parse_mode)
    except Exception as exc:
        log.exception("Failed to send Telegram reply to chat_id=%d: %s", chat_id, exc)

    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("noor_webhook:app", host="0.0.0.0", port=8000, reload=False)
