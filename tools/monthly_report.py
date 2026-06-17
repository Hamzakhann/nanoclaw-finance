import csv
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from datetime import datetime


def parse_month(date_str: str) -> str | None:
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m")
        except ValueError:
            continue
    return None


def month_label(ym: str) -> str:
    return datetime.strptime(ym, "%Y-%m").strftime("%B %Y")


def fmt_pkr(amount: Decimal) -> str:
    return f"PKR {amount:,.2f}"


def main() -> int:
    reader = csv.DictReader(sys.stdin)

    # month -> category -> Decimal total
    data: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))

    for row in reader:
        date_str = row.get("date", "").strip()
        raw_amount = row.get("amount", "").strip()
        category = row.get("category", "").strip()

        month = parse_month(date_str)
        if not month:
            sys.stderr.write(f"SKIP: missing or malformed date: {dict(row)}\n")
            continue

        try:
            amount = Decimal(raw_amount)
        except InvalidOperation:
            sys.stderr.write(f"SKIP: non-numeric amount: {dict(row)}\n")
            continue

        if amount == 0:
            sys.stderr.write(f"SKIP: zero amount: {dict(row)}\n")
            continue

        if not category:
            sys.stderr.write(f"SKIP: missing category: {dict(row)}\n")
            continue

        data[month][category] += abs(amount)

    if not data:
        sys.stderr.write("SKIP: no valid rows to report.\n")
        return 1

    lines = ["# nanoclaw-finance Expense Report", ""]

    for month in sorted(data):
        categories = data[month]
        month_total = sum(categories.values(), Decimal("0"))

        lines.append(f"## {month_label(month)}")
        lines.append("")
        lines.append("| Category | Total PKR |")
        lines.append("| --- | --- |")

        for category in sorted(categories):
            lines.append(f"| {category} | {fmt_pkr(categories[category])} |")

        lines.append(f"| **Total** | {fmt_pkr(month_total)} |")
        lines.append("")

    print("\n".join(lines).rstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
