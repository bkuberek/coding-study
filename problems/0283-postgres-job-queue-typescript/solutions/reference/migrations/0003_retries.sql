-- Up Migration
-- Each job carries its retry policy, and a job that runs out of attempts is dead: its row stays,
-- so its id stays taken, and the dead letters record why it died, in the order jobs died.
ALTER TABLE jobs
    ADD COLUMN max_attempts integer NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 10),
    ADD COLUMN backoff_seconds integer NOT NULL DEFAULT 30
        CHECK (backoff_seconds BETWEEN 0 AND 3600),
    DROP CONSTRAINT jobs_status_check,
    ADD CONSTRAINT jobs_status_check CHECK (status IN ('queued', 'claimed', 'done', 'dead'));

CREATE TABLE dead_letters (
    seq bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id text NOT NULL UNIQUE REFERENCES jobs (id),
    error text NOT NULL
);
