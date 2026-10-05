-- Pricing-operations domain tables.
-- Ported from the capstone SQLite schema (retail-ai-support-agent,
-- data/setup_db.py). Same four tables and columns; Postgres types and
-- constraints added. The platform only READS these tables.

CREATE TABLE IF NOT EXISTS pricing_rules (
    rule_id     integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rule_name   text    NOT NULL UNIQUE,
    description text    NOT NULL,
    active      boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS materials (
    material_id   text    PRIMARY KEY,
    material_name text    NOT NULL,
    category      text    NOT NULL,
    expiry_months integer,
    active        boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS pricing_plans (
    plan_id          text    PRIMARY KEY,
    plan_name        text    NOT NULL UNIQUE,
    region           text    NOT NULL,
    market           text    NOT NULL,
    channel          text    NOT NULL,
    season           text    NOT NULL,
    status           text    NOT NULL
        CHECK (status IN ('COMPLETED', 'IN_PROGRESS')),
    created_at       date    NOT NULL,
    total_materials  integer NOT NULL,
    priced_materials integer NOT NULL,
    CHECK (priced_materials <= total_materials)
);

CREATE TABLE IF NOT EXISTS plan_materials (
    id                integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plan_id           text NOT NULL REFERENCES pricing_plans (plan_id),
    material_id       text NOT NULL REFERENCES materials (material_id),
    season            text NOT NULL,
    price_status      text NOT NULL
        CHECK (price_status IN ('PRICED', 'NOT_PRICED')),
    downstream_status text
        CHECK (downstream_status IN ('DOWNSTREAMED', 'PENDING', 'FAILED')),
    rejection_reason  text REFERENCES pricing_rules (rule_name),
    price_value       numeric(10, 2),
    UNIQUE (plan_id, material_id)
);

CREATE INDEX IF NOT EXISTS idx_plan_materials_plan_id
    ON plan_materials (plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_materials_material_id
    ON plan_materials (material_id);
