-- Up Migration
-- A job is queued, claimed, or done, and counts its claims. `run_after` is the one time a job
-- keeps: when it is queued, the moment it may be claimed; when it is claimed, the moment the claim
-- runs out. The jobs already waiting may be claimed from the moment they were enqueued, so it is
-- copied from `enqueued_at` for them rather than given a default.
ALTER TABLE jobs
    ADD COLUMN status text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'claimed', 'done')),
    ADD COLUMN attempts integer NOT NULL DEFAULT 0,
    ADD COLUMN run_after timestamptz;

UPDATE jobs SET run_after = enqueued_at;

ALTER TABLE jobs ALTER COLUMN run_after SET NOT NULL;

CREATE INDEX claimable_jobs ON jobs (queue, seq) WHERE status IN ('queued', 'claimed');
