-- Up Migration
-- The event store and the club's history so far, and the problem's: leave this file as it is and
-- add your own migrations after it. Grading appends more events to this table before your
-- migrations run.
CREATE TABLE events (
    position bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    stream_id text NOT NULL,
    version integer NOT NULL,
    event_id text NOT NULL,
    type text NOT NULL,
    data jsonb NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO events (stream_id, version, event_id, type, data, recorded_at) VALUES
    ('ana', 1, 'seed-1', 'deposited', '{"amount": 5000}', '2026-01-05T09:00:00Z'),
    ('ben', 1, 'seed-2', 'deposited', '{"amount": 2000}', '2026-01-20T10:00:00Z'),
    ('ana', 2, 'seed-3', 'withdrawn', '{"amount": 1200}', '2026-02-10T18:30:00Z'),
    ('ana', 3, 'seed-4', 'transferred_out', '{"amount": 800, "to": "ben"}', '2026-03-02T12:00:00Z'),
    ('ben', 2, 'seed-4', 'transferred_in', '{"amount": 800, "from": "ana"}', '2026-03-02T12:00:00Z'),
    ('cleo', 1, 'seed-5', 'deposited', '{"amount": 500}', '2026-04-01T08:15:00Z');
