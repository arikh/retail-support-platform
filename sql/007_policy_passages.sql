-- 007_policy_passages.sql
-- The FAQ and policy texts, cut into passages, each with its embedding
-- (Piece 2 of the build plan: the policy search).
--
-- Why: the support worker answers questions about rules and terms from these
-- passages, not from the model's memory. A question is turned into a vector
-- and the nearest passages are returned (dense search).
--
-- The rows are a copy of the files in data/policies/. They are replaced as a
-- whole by scripts/ingest_policies.py. Never edit them by hand.
--
-- Needs a Postgres image that includes pgvector (see docker-compose.yml).
-- Safe to run again.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS policy_passages (
    source          text        NOT NULL,   -- file name, for example pricing_rules.md
    heading         text        NOT NULL,   -- the "## " heading of the section
    content         text        NOT NULL,   -- heading and body: what is embedded and shown
    embedding_model text        NOT NULL,   -- the model that made the vector
    embedding       vector(384) NOT NULL,   -- 384 numbers: the size this model returns
    PRIMARY KEY (source, heading)           -- a section is named by its file and heading
);

-- No index on the vector column. Without one, pgvector compares the question
-- with every row and returns exact results. An approximate index (HNSW) is
-- for tables far larger than this one.
