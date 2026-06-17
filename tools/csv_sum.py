import csv
import sys
from decimal import Decimal, InvalidOperation


def main() -> int:
    reader = csv.DictReader(sys.stdin)
    total = Decimal("0")
    valid_rows = 0

    for row in reader:
        raw = row.get("amount", "").strip()
        try:
            amount = Decimal(raw)
        except InvalidOperation:
            sys.stderr.write(f"Skipping invalid amount: {dict(row)}\n")
            continue

        total += abs(amount)
        valid_rows += 1

    if valid_rows == 0:
        sys.stderr.write("Error: no valid rows processed.\n")
        return 1

    formatted = f"PKR {total:,.2f}"
    print(f"Total: {formatted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
