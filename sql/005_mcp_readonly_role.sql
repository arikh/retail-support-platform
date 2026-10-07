-- 005_mcp_readonly_role.sql
-- Read-only role for the MCP server (Piece 1 of the build plan).
--
-- Why a separate role: the MCP server is its own process. The database, not
-- the code, must refuse writes (least privilege). The role can read the four
-- pricing tables and nothing else: not pii_vault, not thread_metadata, not
-- the checkpoints schema.
--
-- The password is NOT set here, so no secret is committed. Set it by hand:
--   docker exec -it retail-postgres psql -U retail -d retail_support -c "\password retail_mcp_ro"
--
-- Safe to run again.

-- Roles belong to the whole Postgres server, not to one database,
-- and CREATE ROLE has no IF NOT EXISTS. So check pg_roles first.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'retail_mcp_ro') THEN
        CREATE ROLE retail_mcp_ro WITH LOGIN;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO retail_mcp_ro;

GRANT SELECT ON TABLE pricing_plans, materials, plan_materials, pricing_rules
    TO retail_mcp_ro;

-- A lookup that runs longer than 5 seconds is a fault. Stop it.
ALTER ROLE retail_mcp_ro SET statement_timeout = '5s';
