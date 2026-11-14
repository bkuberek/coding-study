// What producers and readers ask of the queue: enqueue a job, read one, list the dead letters.
//
// A job is stored with one time, `run_after`, which means "not claimable before": when it is
// queued, the moment it may first or next run; when it is claimed, the moment its claim runs out.
// So a claim that ran out needs no write to make the job claimable again, and one condition,
// `run_after <= now`, finds every job a worker may take.

import { type Answer, invalidRequest, ok, refused, unknownJob } from "./answers.ts";
import { now, timestamp } from "./clock.ts";
import { pool } from "./db.ts";
import { isQueue, newJob } from "./requests.ts";

type Stored = "queued" | "claimed" | "done" | "dead";

export type JobRow = {
  id: string;
  queue: string;
  tenant: string;
  payload: unknown;
  status: Stored;
  attempts: number;
  run_after: Date;
};

export const JOB_COLUMNS = "id, queue, tenant, payload, status, attempts, run_after";

const jobExists = refused(409, "job_exists");

// A claim that ran out reads as queued, since any worker may take the job again; a job that is
// done or dead has no next run.
export function shown(row: JobRow, at: Date): Record<string, unknown> {
  const ranOut = row.status === "claimed" && row.run_after.getTime() <= at.getTime();
  const finished = row.status === "done" || row.status === "dead";
  return {
    id: row.id,
    queue: row.queue,
    tenant: row.tenant,
    payload: row.payload,
    status: ranOut ? "queued" : row.status,
    attempts: row.attempts,
    run_after: finished ? null : timestamp(row.run_after),
  };
}

// The primary key settles a job enqueued twice at once: the second insert waits for the first
// transaction and does nothing if it committed.
export async function enqueue(queue: string, body: unknown): Promise<Answer> {
  const asked = newJob(body);
  if (!isQueue(queue) || asked === undefined) {
    return invalidRequest;
  }
  const at = now();
  const added = await pool.query<JobRow>(
    `INSERT INTO jobs
       (id, queue, tenant, payload, enqueued_at, run_after, max_attempts, backoff_seconds, priority)
     VALUES ($1, $2, $3, $4, $5, $5, $6, $7, $8)
     ON CONFLICT (id) DO NOTHING
     RETURNING ${JOB_COLUMNS}`,
    [
      asked.id,
      queue,
      asked.tenant,
      asked.payload,
      at,
      asked.maxAttempts,
      asked.backoffSeconds,
      asked.priority,
    ],
  );
  const row = added.rows[0];
  return row === undefined ? jobExists : ok(shown(row, at), 201);
}

export async function job(id: string): Promise<Answer> {
  const found = await pool.query<JobRow>(`SELECT ${JOB_COLUMNS} FROM jobs WHERE id = $1`, [id]);
  const row = found.rows[0];
  return row === undefined ? unknownJob : ok(shown(row, now()));
}

export async function deadLetters(queue: string): Promise<Answer> {
  if (!isQueue(queue)) {
    return invalidRequest;
  }
  const found = await pool.query(
    `SELECT job.id, job.tenant, job.payload, job.attempts, dead.error
     FROM dead_letters AS dead JOIN jobs AS job ON job.id = dead.job_id
     WHERE job.queue = $1
     ORDER BY dead.seq`,
    [queue],
  );
  return ok(found.rows);
}
