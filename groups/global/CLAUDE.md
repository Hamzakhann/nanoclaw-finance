# Global Rules — All nanoclaw Employees

These rules apply to every agent and group in this system.
Group-level CLAUDE.md files may add restrictions; they may not relax these.

## Currency
- All monetary amounts must be formatted as PKR X,XXX.XX.
- No amount may be presented, stored, or reported without the PKR prefix
  and exactly two decimal places.
- This applies regardless of input format — normalise before output.

## Credentials and Secrets (Zone 4)
- .env and any file containing API keys, tokens, or passwords is Zone 4.
- Never read, write, modify, or log the contents of Zone 4 files.
- Never include credential values in any output, report, or log entry.
- If a task requires a credential, stop and escalate to the human.

## Action Logging
- Every autonomous action must be logged to the memory tables before
  the action is considered complete.
- Minimum log fields: timestamp, employee name, action type, target,
  outcome (success / flagged / escalated).
- If the memory tables are not yet available, write the log entry to
  docs/action_log.txt instead — do not skip logging.

## Data Integrity
- Never fabricate, estimate, or infer data to fill a gap.
- If a value is missing, ambiguous, or unverifiable, flag the entry
  for human review and leave the field empty.
- A flagged entry delivered honestly is always preferable to a
  plausible-looking entry that is wrong.

## Escalation Default
- When in doubt about whether an action is authorised, do not proceed.
  Flag the situation, state why it is unclear, and wait.
