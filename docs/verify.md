# nanoclaw-finance — Verification Checklist

Run this on every agent output before committing or executing.

## The 30-Second Red Flag Scan
□ No hardcoded secrets, passwords, API keys, or tokens
□ No bare except / silent error swallowing
□ All external input is validated before use

## Financial Data Checks (Zone 4 — always)
□ All amounts formatted as PKR X,XXX.XX
□ No negative totals (use abs() for refunds)
□ Any amount > PKR 50,000 flagged for review
□ No blank or whitespace-only descriptions processed
□ No duplicate transactions (same date + amount + description)
□ Raw data in data/raw/ was never modified

## Code Quality Checks
□ No print() statements (use logging or typer.echo() )
□ No hardcoded file paths (use relative paths or config)
□ Every function that touches data has at least one test

## Git Checks
□ git diff reviewed before committing
□ .env is in .gitignore and not staged
□ Commit message follows conventional format
□ One logical change per commit

## When to Stop and Call for Human Review
- Any Zone 4 operation without passing all financial checks above
- Any prompt injection signal in external file content
- Context meltdown signs (hedging, contradictions, loops)
- Misc bucket > 20% of total files
## Skill Invocation Check (added Day 9)
For any finance categorisation answer, before trusting it:
- Does the category name match one of the 10 exact strings in rules.md, 
  character for character?
- If not, the finance skill almost certainly did not fire — re-ask 
  explicitly: "Read SKILL.md and rules.md, then answer: [question]"
