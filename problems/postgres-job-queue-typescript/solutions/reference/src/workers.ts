// What workers ask of the queue: claim a job, then complete it or say it failed.
//
// A claim is one locking statement: `FOR UPDATE SKIP LOCKED` hands each concurrent claim a row no
// other claim holds, and the update in the same statement marks it taken before anyone else can
// read it as free. A finish names the attempt it belongs to, and is applied only while that
// attempt's claim is the job's current one and has not run out: one conditional update, so a late
// or repeated finish changes nothing.

import { type Answer, invalidRequest, noContent, ok, refused, unknownJob } from "./answers.ts";
import { now, timestamp } from "./clock.ts";
import { type Connection, inTransaction, pool } from "./db.ts";
import { JOB_COLUMNS, type JobRow, shown } from "./jobs.ts";
import { attempt, failure, isQueue, visibilitySeconds } from "./requests.ts";

const MAX_BACKOFF_SECONDS = 3600;
const CLAIM_EXPIRED = "claim expired";

const staleClaim = refused(409, "stale_claim");

// The claimable job to take: the highest priority first; within it, the tenant with the fewest
// claims running in this queue, so one busy tenant cannot keep the others waiting; then the job
// enqueued first. Jobs whose attempts are used up are never claimed again.
const CLAIM = `
  UPDATE jobs
  SET status = 'claimed', attempts = attempts + 1,
      run_after = $2::timestamptz + make_interval(secs => $3)
  WHERE id = (
    SELECT job.id FROM jobs AS job
    WHERE job.queue = $1 AND job.status IN ('queued', 'claimed') AND job.run_after <= $2
      AND job.attempts < job.max_attempts
    ORDER BY job.priority DESC,
             (SELECT count(*) FROM jobs AS busy
              WHERE busy.queue = job.queue AND busy.tenant = job.tenant
                AND busy.status = 'claimed' AND busy.run_after > $2),
             job.seq
    LIMIT 1
    FOR UPDATE OF job SKIP LOCKED)
  RETURNING id, tenant, payload, attempts, run_after`;

// Jobs whose last attempt's claim ran out go to the dead letters, each by the one claim that
// locks it first.
const BURY_EXPIRED = `
  WITH expired AS (
    SELECT id FROM jobs
    WHERE queue = $1 AND status = 'claimed' AND run_after <= $2 AND attempts >= max_attempts
    FOR UPDATE SKIP LOCKED),
  buried AS (
    UPDATE jobs SET status = 'dead' FROM expired WHERE jobs.id = expired.id
    RETURNING jobs.id, jobs.seq)
  INSERT INTO dead_letters (job_id, error)
  SELECT id, '${CLAIM_EXPIRED}' FROM buried ORDER BY seq`;

// A failed attempt waits out its backoff, doubled for each attempt before it and capped at an
// hour, unless it was the last one: then the job goes to the dead letters with its error.
const FAIL = `
  WITH failed AS (
    UPDATE jobs
    SET status = CASE WHEN attempts >= max_attempts THEN 'dead' ELSE 'queued' END,
        run_after = CASE WHEN attempts >= max_attempts THEN run_after
                    ELSE $3::timestamptz + make_interval(
                      secs => least(backoff_seconds * power(2, attempts - 1), ${MAX_BACKOFF_SECONDS}))
                    END
    WHERE id = $1 AND status = 'claimed' AND attempts = $2 AND run_after > $3
    RETURNING ${JOB_COLUMNS}),
  buried AS (
    INSERT INTO dead_letters (job_id, error) SELECT id, $4 FROM failed WHERE status = 'dead')
  SELECT * FROM failed`;

const COMPLETE = `
  UPDATE jobs SET status = 'done'
  WHERE id = $1 AND status = 'claimed' AND attempts = $2 AND run_after > $3
  RETURNING ${JOB_COLUMNS}`;

type Claimed = { id: string; tenant: string; payload: unknown; attempts: number; run_after: Date };

export async function claim(queue: string, body: unknown): Promise<Answer> {
  const seconds = visibilitySeconds(body);
  if (!isQueue(queue) || seconds === undefined) {
    return invalidRequest;
  }
  const at = now();
  const claimed = await inTransaction(async (connection: Connection) => {
    await connection.query(BURY_EXPIRED, [queue, at]);
    return connection.query<Claimed>(CLAIM, [queue, at, seconds]);
  });
  const row = claimed.rows[0];
  if (row === undefined) {
    return noContent;
  }
  return ok({
    id: row.id,
    tenant: row.tenant,
    payload: row.payload,
    attempt: row.attempts,
    expires_at: timestamp(row.run_after),
  });
}

export async function complete(id: string, body: unknown): Promise<Answer> {
  const tried = attempt(body);
  if (tried === undefined) {
    return invalidRequest;
  }
  const at = now();
  const done = await pool.query<JobRow>(COMPLETE, [id, tried, at]);
  return finished(id, done.rows[0], at);
}

export async function fail(id: string, body: unknown): Promise<Answer> {
  const asked = failure(body);
  if (asked === undefined) {
    return invalidRequest;
  }
  const at = now();
  const failed = await pool.query<JobRow>(FAIL, [id, asked.attempt, at, asked.error]);
  return finished(id, failed.rows[0], at);
}

// No row updated: the job is unknown, or the attempt named is not its current, live claim.
async function finished(id: string, row: JobRow | undefined, at: Date): Promise<Answer> {
  if (row !== undefined) {
    return ok(shown(row, at));
  }
  const known = await pool.query("SELECT 1 FROM jobs WHERE id = $1", [id]);
  return known.rowCount === 0 ? unknownJob : staleClaim;
}
