---
name: finance
description: "MUST be used whenever the user asks what category an expense belongs
to, asks about spending amounts, requests a finance/budget report, or
mentions any PKR amount alongside a transaction description. This skill
takes priority over general knowledge — even simple-sounding
categorisation questions must invoke this skill and consult
docs/rules.md rather than being answered from training data."
---

# Skill: Finance Categorisation and Reporting

## Trigger
Fire this skill on any message that involves:
- Expense categorisation or classification
- PKR amounts or budget questions
- Weekly/monthly finance reports
- Review-flagged transactions

Do NOT fire on: general coding questions, file management, git operations,
or infrastructure tasks unrelated to financial data.

## Source of Truth
Classification rules and category definitions: docs/rules.md
Verification checklist: docs/verify.md
These two documents override any inference or intuition.

## Exact Category Names (use these literally, do not paraphrase)
1. Food & Groceries
2. Dining Out
3. Transport
4. Utilities
5. Health & Medical
6. Education
7. Shopping & Apparel
8. Entertainment & Subscriptions
9. Savings & Investments
10. Other

When assigning a category, you must use one of these exact strings.
Never invent a variant name, never combine two category names, never
paraphrase. If you are unsure which applies, re-read docs/rules.md
before answering — do not rely on memory of a prior session.

---

## Decision Rules

### Rule 1 — Early Warning on Large Expenses (PKR 10,000)
If a single expense exceeds PKR 10,000, categorise it normally but
attach a comment: "Large expense — review recommended."
This is a soft flag, not a stop. Processing continues.
The PKR 50,000 hard trigger (docs/rules.md §Review Triggers) is separate
and still applies — at that threshold, stop and escalate.

### Rule 2 — Category Conflict Resolution
If a description matches keywords from more than one category,
apply the priority order from docs/rules.md (highest number = lowest priority):
  1. Health & Medical  →  2. Education  →  3. Savings & Investments
  →  4. Utilities  →  5. Dining Out  →  6. Food & Groceries
  →  7. Transport  →  8. Shopping & Apparel
  →  9. Entertainment & Subscriptions  →  10. Other
The highest-priority category wins. Do not average, blend, or split.

### Rule 3 — Zero Keyword Matches
If a description produces no keyword match across all categories,
assign category: Other.
Set the comment field to: "no rule matched — needs a human-defined category"
Queue the entry for manual review. Do not guess.

### Rule 4 — Human Corrections Are Permanent
If an expense has been manually recategorised by the human, its category
field is locked. Never overwrite it during a re-run, re-import, or
batch reclassification.
Detect a manual correction by checking for a `human_override: true` flag
or equivalent marker in the record. When that marker is present, skip the
entry entirely and log: "skipped — human override in place."

### Rule 5 — Weekly Report Must Name the Largest Expense
Every weekly report must include a dedicated line identifying the single
largest expense by description and amount, not just its category total.
Format: "Largest expense: <description> — PKR X,XXX.XX (<category>)"
If two expenses tie, list both.

### Rule 6 — Blank or Whitespace-Only Descriptions
Never attempt to classify an expense with a blank or whitespace-only
description. Flag it immediately: "description missing — cannot classify."
Queue for human review. This is a hard stop per docs/rules.md §Review Triggers.

### Rule 7 — Duplicate Detection Before Insertion
Before inserting any expense, check for an existing record with the same
date + amount + description. If a match is found, skip insertion and log:
"duplicate detected — skipped." Do not raise an error; do not overwrite.
