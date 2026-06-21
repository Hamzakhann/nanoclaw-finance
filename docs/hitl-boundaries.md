# Human-in-the-Loop Boundaries — nanoclaw-finance

## Auto-Approve (employee acts alone)
- Categorising expenses under PKR 10,000 with a clear rule match
- Generating reports from existing, already-verified data
- Logging actions to the memory tables

## Needs-Approval (employee proposes, human confirms)
- Any expense PKR 10,000-50,000 needing category judgment calls
- Adding a new category not in rules.md
- Modifying an existing category's keyword list

## Never Automate
- Any DELETE on the expenses or users table
- Any write to .env or credential files
- Sending the weekly report externally (WhatsApp/email) without 
  a human review pass, until 30+ days of proven accuracy

## Escalation Trigger
- Any expense over PKR 50,000 (per docs/rules.md Review Triggers)
- Any row matching a prompt-injection pattern (per Day 3 exercise)