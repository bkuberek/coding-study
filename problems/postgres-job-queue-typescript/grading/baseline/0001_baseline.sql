-- Up Migration
-- The queue as the first version of the service left it: producers enqueue into this table, and
-- nothing runs the jobs yet. This file is the problem's: leave it as it is and add your own
-- migrations after it. Grading loads more jobs into this table before your migrations run.
CREATE TABLE jobs (
    id text PRIMARY KEY,
    seq bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
    queue text NOT NULL,
    tenant text NOT NULL,
    payload jsonb NOT NULL,
    urgent boolean NOT NULL DEFAULT false,
    enqueued_at timestamptz NOT NULL
);

INSERT INTO jobs (id, queue, tenant, payload, urgent, enqueued_at) VALUES
    ('inv-1001', 'invoices', 'acme', '{"invoice": 1001}', false, '2027-02-28 09:00:00+00'),
    ('inv-1002', 'invoices', 'birch', '{"invoice": 1002}', false, '2027-02-28 09:10:00+00'),
    ('inv-1003', 'invoices', 'acme', '{"invoice": 1003}', true, '2027-02-28 09:20:00+00');
