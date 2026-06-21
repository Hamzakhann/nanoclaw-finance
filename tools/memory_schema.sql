-- Memory schema for nanoclaw-finance
-- action_log: records every agent action and its approval level.
-- knowledge:  stores subject-predicate-object facts the agent learns.
-- Safe to run multiple times: all statements use IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS action_log (
    id          SERIAL PRIMARY KEY,
    action_type VARCHAR(50)  NOT NULL,
    target      VARCHAR(200),
    trust_level VARCHAR(40)  NOT NULL
                    CHECK (trust_level IN ('auto_approved', 'needs_approval', 'escalated', 'unverified_skill_bypass')),
    result      TEXT,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge (
    id          SERIAL PRIMARY KEY,
    subject     VARCHAR(200) NOT NULL,
    predicate   VARCHAR(200) NOT NULL,
    object      VARCHAR(500) NOT NULL,
    source      VARCHAR(100),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
