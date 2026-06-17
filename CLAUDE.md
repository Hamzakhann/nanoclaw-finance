# nanoclaw-finance

Personal finance AI Employee for a Pakistani user.
Tracks PKR expenses, categorises them, reports weekly.

## What This Project Is
nanoclaw-finance is an AI-powered personal finance employee.
It processes expense data in PKR, categorises transactions,
stores records in SQLite (later Neon PostgreSQL), and delivers
autonomous weekly reports via WhatsApp.

## Tech Stack
- Language: Python 3.10+
- Database: SQLite (Days 1-4), Neon PostgreSQL (Day 5+)
- Tools: custom Python scripts in /tools
- Currency: always PKR, formatted as PKR X,XXX.XX
- Platform: Linux server, systemd daemon (Day 7+)

## File Structure
nanoclaw-finance/
├── data/
│   ├── raw/          # incoming unorganised expense files
│   └── organised/    # processed and categorised data
├── tools/            # reusable Python pipeline scripts
├── docs/             # reports, logs, specs
└── .claude/          # settings and guardrails

## Commands
- Run a tool: python tools/[script_name].py
- Run tests: python -m pytest tests/
- Git status: git status && git diff

## NEVER Do These
1. Never hardcode credentials or API keys in any file
2. Never run DELETE or DROP without explicit human approval
3. Never commit .env files
4. Never present money without PKR prefix and 2 decimal places
5. Never modify raw data — always work on copies in organised/

## v1.0 Definition of Done
I can send a WhatsApp message with my expenses for the week
and receive an autonomous structured PKR report with category
totals and one proactive recommendation — without me asking.