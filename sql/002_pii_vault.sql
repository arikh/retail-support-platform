CREATE TABLE pii_vault (
    token         text        PRIMARY KEY,
    value         bytea       NOT NULL,        -- encryption-ready, NOT yet encrypted (crypto deferred — ADR-006)
    customer_id   text        NOT NULL,
    field_type    text        NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_pii_vault_customer_id ON pii_vault (customer_id);