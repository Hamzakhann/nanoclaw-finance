import csv
import re
import sys
from decimal import Decimal, InvalidOperation

# Priority order matches docs/rules.md — first category whose pattern fires wins.
_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Health & Medical", [
        "pharmacy", "medical", "clinic", "hospital", "doctor", "lab", "test",
        "dawakhana", "sehat", "shifa", "aga khan", "oladoc", "marham",
        "medicine", "tablet", "injection",
    ]),
    ("Education", [
        "school", "college", "university", "tuition", "fee", "books",
        "stationery", "coursera", "udemy", "khan academy", "academy",
    ]),
    ("Savings & Investments", [
        "savings", "investment", "mutual fund", "prize bond", "deposit",
        "meezan", "hbl saving", "national savings", "naya pakistan certificate",
    ]),
    ("Utilities", [
        "electricity", "wapda", "k-electric", "sui gas", "ssgc", "sngpl",
        "water", "ptcl", "internet", "wifi", "jazz", "telenor", "zong",
        "ufone", "bill", "utility",
    ]),
    ("Dining Out", [
        "restaurant", "cafe", "dhaba", "dine", "biryani", "pizza", "burger",
        "kfc", "mcdonalds", "pizza hut", "subway", "foodpanda", "cheezious",
        "karachi broast", "chai dhaba",
    ]),
    ("Food & Groceries", [
        "grocery", "groceries", "kiryana", "supermarket", "imtiaz", "carrefour",
        "metro", "hyperstar", "store", "mart", "ration",
    ]),
    ("Transport", [
        "petrol", "fuel", "diesel", "cng", "uber", "careem", "indriver", "bus",
        "wagon", "rickshaw", "toll", "parking", "pump", "shell", "pso",
        "total parco",
    ]),
    ("Shopping & Apparel", [
        "clothes", "shirt", "shoes", "jeans", "kurta", "shalwar", "fabric",
        "daraz", "khaadi", "gul ahmed", "sapphire", "alkaram", "bata", "stylo",
        "j.", "breakout",
    ]),
    ("Entertainment & Subscriptions", [
        "cinema", "nueplex", "cinestar", "netflix", "youtube premium", "spotify",
        "game", "ticket", "event", "concert", "subscription",
    ]),
]


def _build_pattern(keyword: str) -> re.Pattern:
    escaped = re.escape(keyword)
    # Keywords ending in a non-word char (e.g. "j.") cannot have a trailing \b
    # because \b requires the next char to be a word char.
    if re.search(r"\W$", keyword):
        return re.compile(r"\b" + escaped, re.IGNORECASE)
    return re.compile(r"\b" + escaped + r"\b", re.IGNORECASE)


CATEGORIES: list[tuple[str, list[re.Pattern]]] = [
    (name, [_build_pattern(kw) for kw in keywords])
    for name, keywords in _CATEGORY_KEYWORDS
]


def classify(description: str) -> str:
    for category, patterns in CATEGORIES:
        if any(p.search(description) for p in patterns):
            return category
    return "Other"


def main() -> int:
    reader = csv.DictReader(sys.stdin)

    if reader.fieldnames is None:
        sys.stderr.write("SKIP: empty input — no header row found\n")
        return 1

    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(list(reader.fieldnames) + ["category"])

    for row in reader:
        date = row.get("date", "").strip()
        raw_amount = row.get("amount", "").strip()
        description = row.get("description", "").strip()

        # Validate amount (General Rule 1: empty, zero, or non-numeric → skip)
        try:
            amount = Decimal(raw_amount)
        except InvalidOperation:
            sys.stderr.write(f"SKIP: non-numeric amount: {dict(row)}\n")
            continue

        if amount == 0:
            sys.stderr.write(f"SKIP: zero amount: {dict(row)}\n")
            continue

        # Review triggers
        if not description:
            sys.stderr.write(f"REVIEW: blank description: {dict(row)}\n")

        if abs(amount) > Decimal("50000"):
            sys.stderr.write(
                f"REVIEW: amount exceeds PKR 50,000: {dict(row)}\n"
            )

        category = classify(description) if description else "Other"

        if category == "Other":
            sys.stderr.write(f"REVIEW: category is Other: {dict(row)}\n")

        writer.writerow([date, raw_amount, description, category])

    return 0


if __name__ == "__main__":
    sys.exit(main())
