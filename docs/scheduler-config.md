# Scheduled Task Design — Weekly Report

- Task: generate weekly PKR expense report
- Trigger: every Sunday, 8:00 AM (would map to a launchd 
  StartCalendarInterval, or a cron-equivalent on Linux)
- Data sources: expenses table (last 7 days) + category totals
- Output: markdown report saved to docs/reports/weekly_YYYY-MM-DD.md
- On completion: log a 'completed' row to runs table (Day 6 schema)
- On failure: log 'failed' with error message, do NOT send a 
  broken report