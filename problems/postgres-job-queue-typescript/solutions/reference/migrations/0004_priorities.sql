-- Up Migration
-- A priority from 0 to 9 replaces the first version's `urgent` flag: the jobs it marked urgent
-- get 9, every other job 5. The column is added with the default every job already there should
-- have, and only then are the urgent ones raised, before the flag is dropped. The claim reads
-- jobs by priority and then by when they were enqueued, and counts each tenant's running claims,
-- so both have an index.
ALTER TABLE jobs
    ADD COLUMN priority integer NOT NULL DEFAULT 5 CHECK (priority BETWEEN 0 AND 9);

UPDATE jobs SET priority = 9 WHERE urgent;

ALTER TABLE jobs DROP COLUMN urgent;

DROP INDEX claimable_jobs;

CREATE INDEX claimable_jobs ON jobs (queue, priority DESC, seq)
    WHERE status IN ('queued', 'claimed');

CREATE INDEX running_claims ON jobs (queue, tenant) WHERE status = 'claimed';
