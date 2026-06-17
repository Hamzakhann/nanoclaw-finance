# nanoclaw-finance — v1.0 Specification

## What the project does (plain language)
nanoclaw-finance is a personal finance AI Employee.
It tracks PKR expenses, categorises them, and reports weekly.

## Inputs
- CSV files with expense rows: date, amount, description
- WhatsApp messages (Day 9+)

## Outputs
- Categorised expense records in SQLite/PostgreSQL
- Monthly markdown report with PKR totals per category
- Weekly autonomous report with 1+ proactive recommendation

## Success Criteria (testable)
1. Given a CSV with 10 expense rows, the system produces:
   - correct PKR totals per category
   - correctly tagged categories (food, transport, utilities, misc)
   - zero rows silently dropped on errors
2. Amount formatting: always PKR X,XXX.XX — never bare numbers
3. Negative amounts (refunds) handled with abs() — never negative totals
4. Any expense > PKR 10,000 flagged for review automatically

## What this is NOT
- Not a bank integration
- Not a budgeting app
- Not multi-currency (PKR only)