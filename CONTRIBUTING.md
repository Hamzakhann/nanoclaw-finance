# Contributing to nanoclaw-finance

## Branch Naming
- feature/<name>   — new functionality
- fix/<name>       — bug fixes
- experiment/<name> — exploratory work, may be discarded

## Rules
- Never commit directly to main for anything non-trivial
- One logical change per commit (see git log for examples)
- Run docs/verify.md checklist before any commit touching 
  financial data or database writes
- Experiments that don't pan out get deleted, not merged half-working



## Webhook Setup
To set up your Telegram webhook, run the following curl command:
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "<YOUR_WEBHOOK_URL>"}'
```