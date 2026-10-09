-- 006_llm_calls.sql
-- Per-call log of every LLM call (Piece 4 of the build plan).
--
-- Why: to see what each call costs and how long it takes, by agent (node)
-- and by prompt version. Token counts come from the model's reply; cost is
-- tokens times the price table in code. No prompt or answer text is stored,
-- so this table holds no user content (ADR-0015).
--
-- prompts holds the prompt files the call was built from, as name -> version:
--   {"routing_system": "v1"}
--   {"format_findings": "v1", "support_status_guide": "v1"}
-- One column, because a call can use more than one prompt file and each name
-- must stay paired with its own version.
--
-- Written by the application; never read by the agent's tools. The MCP role
-- has no grant on it.
--
-- Safe to run again.

CREATE TABLE IF NOT EXISTS llm_calls (
    run_id           uuid           PRIMARY KEY,      -- LangChain run id: one row per model call
    created_at       timestamptz    NOT NULL DEFAULT now(),
    thread_id        text,                            -- the conversation, when known
    node             text           NOT NULL,         -- the graph node: supervisor, support, analysis
    model            text           NOT NULL,
    prompts          jsonb          NOT NULL          -- prompt name -> version; at least one
        CHECK (jsonb_typeof(prompts) = 'object' AND prompts <> '{}'::jsonb),
    input_tokens     integer        NOT NULL CHECK (input_tokens >= 0),
    output_tokens    integer        NOT NULL CHECK (output_tokens >= 0),
    reasoning_tokens integer        NOT NULL DEFAULT 0 CHECK (reasoning_tokens >= 0),
    cached_tokens    integer        NOT NULL DEFAULT 0 CHECK (cached_tokens >= 0),
    latency_ms       integer        NOT NULL CHECK (latency_ms >= 0),
    cost_usd         numeric(12, 8) NOT NULL CHECK (cost_usd >= 0)
);

-- "What did yesterday cost?"
CREATE INDEX IF NOT EXISTS idx_llm_calls_created_at ON llm_calls (created_at);

-- "Which calls used this prompt at this version?"
--   WHERE prompts @> '{"support_status_guide": "v2"}'
CREATE INDEX IF NOT EXISTS idx_llm_calls_prompts ON llm_calls USING gin (prompts);
