"""
Unit tests for parse_intent() in noor_webhook.py.
Run: python tools/test_parse_intent.py
"""
import os
import sys
from decimal import Decimal
from pathlib import Path

# Provide dummy env vars so noor_webhook imports without a real .env
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test_token")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

sys.path.insert(0, str(Path(__file__).parent))
from noor_webhook import (
    INTENT_ADD_EXPENSE,
    INTENT_HELP,
    INTENT_MONTH,
    INTENT_REPORT,
    INTENT_TODAY,
    INTENT_UNDO,
    INTENT_UNKNOWN,
    INTENT_WEEK,
    INTENT_YESTERDAY,
    ParsedIntent,
    parse_intent,
)

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

_failures: list[str] = []


def check(label: str, got: ParsedIntent, intent, amount=None, desc_contains=None):
    ok = True

    if got.intent != intent:
        print(f"{FAIL}  {label}")
        print(f"       intent: expected {intent!r}, got {got.intent!r}")
        ok = False

    if amount is not None and got.amount != Decimal(str(amount)):
        print(f"{FAIL}  {label}")
        print(f"       amount: expected {amount}, got {got.amount}")
        ok = False

    if desc_contains is not None:
        if got.description is None or desc_contains.lower() not in got.description.lower():
            print(f"{FAIL}  {label}")
            print(f"       description: expected to contain {desc_contains!r}, got {got.description!r}")
            ok = False

    if ok:
        print(f"{PASS}  {label}")
    else:
        _failures.append(label)


# ── Command intents ───────────────────────────────────────────────────────────

check("today", parse_intent("today"), INTENT_TODAY)
check("today uppercase", parse_intent("TODAY"), INTENT_TODAY)
check("/today", parse_intent("/today"), INTENT_TODAY)
check("yesterday", parse_intent("yesterday"), INTENT_YESTERDAY)
check("/yesterday", parse_intent("/yesterday"), INTENT_YESTERDAY)
check("last week", parse_intent("last week"), INTENT_WEEK)
check("/last week", parse_intent("/last week"), INTENT_WEEK)
check("this month", parse_intent("this month"), INTENT_MONTH)
check("/this month", parse_intent("/this month"), INTENT_MONTH)
check("report", parse_intent("report"), INTENT_REPORT)
check("weekly", parse_intent("weekly"), INTENT_REPORT)
check("/report", parse_intent("/report"), INTENT_REPORT)
check("undo", parse_intent("undo"), INTENT_UNDO)
check("/undo", parse_intent("/undo"), INTENT_UNDO)
check("help", parse_intent("help"), INTENT_HELP)
check("/help", parse_intent("/help"), INTENT_HELP)

# Commands are case-insensitive
check("LAST WEEK", parse_intent("LAST WEEK"), INTENT_WEEK)
check("This Month", parse_intent("This Month"), INTENT_MONTH)

# Whitespace tolerance
check("  today  ", parse_intent("  today  "), INTENT_TODAY)

# ── INTENT_ADD_EXPENSE ────────────────────────────────────────────────────────

# Task spec examples
check(
    "KFC lunch PKR 850",
    parse_intent("KFC lunch PKR 850"),
    INTENT_ADD_EXPENSE,
    amount=850,
    desc_contains="KFC",
)
check(
    "850 KFC lunch",
    parse_intent("850 KFC lunch"),
    INTENT_ADD_EXPENSE,
    amount=850,
    desc_contains="KFC",
)
check(
    "spent 1200 on groceries",
    parse_intent("spent 1200 on groceries"),
    INTENT_ADD_EXPENSE,
    amount=1200,
    desc_contains="groceries",
)
check(
    "Imtiaz 3400",
    parse_intent("Imtiaz 3400"),
    INTENT_ADD_EXPENSE,
    amount=3400,
    desc_contains="Imtiaz",
)
check(
    "petrol 450 shell",
    parse_intent("petrol 450 shell"),
    INTENT_ADD_EXPENSE,
    amount=450,
    desc_contains="petrol",
)

# PKR with comma-separated thousands
check(
    "rent PKR 25,000",
    parse_intent("rent PKR 25,000"),
    INTENT_ADD_EXPENSE,
    amount=25000,
    desc_contains="rent",
)

# Decimal amount
check(
    "chai 35.50",
    parse_intent("chai 35.50"),
    INTENT_ADD_EXPENSE,
    amount="35.50",
    desc_contains="chai",
)

# Small but valid (>= 10 PKR)
check(
    "chai 30",
    parse_intent("chai 30"),
    INTENT_ADD_EXPENSE,
    amount=30,
    desc_contains="chai",
)

# Single-digit quantity skipped; larger number taken as amount
check(
    "2 burgers 450",
    parse_intent("2 burgers 450"),
    INTENT_ADD_EXPENSE,
    amount=450,
    desc_contains="burgers",
)

# Trailing-number free text
check(
    "kfc dinner 700",
    parse_intent("kfc dinner 700"),
    INTENT_ADD_EXPENSE,
    amount=700,
    desc_contains="kfc",
)

# Middle number
check(
    "grocery 1500 imtiaz",
    parse_intent("grocery 1500 imtiaz"),
    INTENT_ADD_EXPENSE,
    amount=1500,
    desc_contains="grocery",
)

# ── INTENT_UNKNOWN ────────────────────────────────────────────────────────────

check("empty string", parse_intent(""), INTENT_UNKNOWN)
check("pure text no amount", parse_intent("hello there"), INTENT_UNKNOWN)
check("random question", parse_intent("what is my balance"), INTENT_UNKNOWN)

# Single digit alone: below _MIN_EXPENSE_AMOUNT threshold, no PKR prefix
check("single digit alone", parse_intent("5"), INTENT_UNKNOWN)

# ── No false positives on partial words ──────────────────────────────────────

# "reporter" must NOT match INTENT_REPORT
check("reporter is not report", parse_intent("reporter app 200"), INTENT_ADD_EXPENSE, amount=200)

# "undo" embedded in a word — "undone" should not trigger INTENT_UNDO
# (it's not an exact fullmatch, so it falls through to expense or unknown)
check("undone not undo", parse_intent("undone 500"), INTENT_ADD_EXPENSE, amount=500)

# ── Return type sanity ────────────────────────────────────────────────────────

result = parse_intent("lunch 300")
assert isinstance(result, ParsedIntent), "parse_intent must return ParsedIntent"
assert result.amount == Decimal("300")
assert result.raw == "lunch 300"
print(f"{PASS}  return type is ParsedIntent with correct fields")

# ── Summary ───────────────────────────────────────────────────────────────────

print()
if _failures:
    print(f"FAILED: {len(_failures)} test(s) — {', '.join(_failures)}")
    sys.exit(1)
else:
    print("All tests passed.")
