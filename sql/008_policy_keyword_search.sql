-- 008_policy_keyword_search.sql
-- Keyword search over the policy passages (Piece 2 of the build plan, step 2).
--
-- Why: dense search (sql/007) finds passages by meaning. Keyword search finds
-- passages that contain the words of the question. The two fail on different
-- questions, so the search uses both and merges the two result lists.
--
-- content_tsv is the passage text prepared for word search: the words are
-- lower-cased, cut to their stem ("mapping" and "mapped" both become "map")
-- and common words ("the", "is", "what") are dropped. Postgres fills the
-- column itself from content, on every insert. The ingest does not name it.
--
-- The GIN index lets Postgres find the rows that contain a word without
-- reading every row. With 16 rows Postgres will not use it; it is here
-- because this is how the column is used on a table of real size.
--
-- Safe to run again.

ALTER TABLE policy_passages
    ADD COLUMN IF NOT EXISTS content_tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

CREATE INDEX IF NOT EXISTS idx_policy_passages_content_tsv
    ON policy_passages USING gin (content_tsv);
