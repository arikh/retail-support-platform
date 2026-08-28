CREATE TABLE thread_metadata (
    thread_id        uuid        PRIMARY KEY,
    customer_id      text        NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    last_activity_at timestamptz
);

CREATE INDEX idx_thread_metadata_customer_id ON thread_metadata (customer_id);