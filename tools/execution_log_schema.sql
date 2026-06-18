-- Execution log schema for nanoclaw-finance
-- Tracks every pipeline run, its conversation turns, and tool calls made.
-- Safe to run multiple times: all statements use IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS runs (
    id          SERIAL PRIMARY KEY,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status      VARCHAR(20) NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running', 'completed', 'failed')),
    trigger     VARCHAR(50) NOT NULL DEFAULT 'manual',
    error       TEXT
);

CREATE TABLE IF NOT EXISTS turns (
    id             SERIAL PRIMARY KEY,
    run_id         INTEGER     NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    turn_number    INTEGER     NOT NULL,
    input_summary  TEXT,
    output_summary TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tool_calls (
    id          SERIAL PRIMARY KEY,
    turn_id     INTEGER      NOT NULL REFERENCES turns(id) ON DELETE CASCADE,
    tool_name   VARCHAR(100) NOT NULL,
    input_data  JSONB,
    output_data JSONB,
    status      VARCHAR(20)  NOT NULL DEFAULT 'success'
                    CHECK (status IN ('success', 'error')),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
