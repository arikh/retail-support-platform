-- The schema that holds LangGraph's checkpoint tables.
-- DATABASE_URL points at it with search_path=checkpoints, so the checkpoint
-- tables stay out of the public schema, where the business tables live.
-- Run this before scripts/init_db.py.

CREATE SCHEMA IF NOT EXISTS checkpoints;
