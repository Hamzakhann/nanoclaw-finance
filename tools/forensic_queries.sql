-- forensic_queries.sql
-- Diagnostic queries for nanoclaw-finance.
-- Run any of these directly against Neon to inspect pipeline health and data quality.

-- ── 1. Crashed agents ────────────────────────────────────────────────────────
-- Detects pipeline runs that started more than 10 minutes ago but never
-- recorded a finished_at timestamp.  These are either still running (unlikely
-- after 10 min) or crashed before the finally block could mark them complete.
SELECT id, started_at, error
FROM runs
WHERE status = 'running'
  AND finished_at IS NULL
  AND started_at < NOW() - INTERVAL '10 minutes';


-- ── 2. Most expensive category this month ────────────────────────────────────
-- Finds the single category with the highest total PKR spend in the current
-- calendar month.  Useful for the weekly report's proactive recommendation.
SELECT c.name, SUM(e.amount) AS total
FROM expenses e
JOIN categories c ON e.category_id = c.id
WHERE DATE_TRUNC('month', e.date) = DATE_TRUNC('month', NOW())
GROUP BY c.name
ORDER BY total DESC
LIMIT 1;


-- ── 3. Duplicate detection ───────────────────────────────────────────────────
-- Flags rows where the same date + amount + description combination appears
-- more than once.  Indicates a double-import, a failed idempotency key, or a
-- CSV file that was processed twice without deduplication.
SELECT date, amount, description, COUNT(*) AS count
FROM expenses
GROUP BY date, amount, description
HAVING COUNT(*) > 1;


-- ── 4. Review queue ──────────────────────────────────────────────────────────
-- Surfaces expenses that require a human decision before the weekly report is
-- finalised.  Three conditions trigger review (per rules.md):
--   • amount > PKR 50,000  — single large transaction flag
--   • description IS NULL  — cannot be categorised without a description
--   • category = 'Other'   — classifier gave up; manual assignment needed
SELECT id, date, amount, description
FROM expenses
WHERE amount > 50000
   OR description IS NULL
   OR category_id = (SELECT id FROM categories WHERE name = 'Other');
