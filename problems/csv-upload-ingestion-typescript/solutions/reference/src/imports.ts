// The imports table: which uploads were loaded, and how many of their rows.

import type { PoolClient } from "pg";

import type { Upload } from "./events.ts";
import type { Outcome } from "./load.ts";
import { pool } from "./db.ts";

export type Answer = { status: number; body: unknown };

// Claims an upload for this transaction. False means another transaction already loaded it: the
// unique key makes a second claim of the same upload wait for the first to commit, then fail.
export async function claim(client: PoolClient, upload: Upload): Promise<boolean> {
  const claimed = await client.query(
    `INSERT INTO imports (bucket, key, sequencer) VALUES ($1, $2, $3)
     ON CONFLICT (bucket, key, sequencer) DO NOTHING`,
    [upload.bucket, upload.key, upload.sequencer],
  );
  return claimed.rowCount === 1;
}

export async function finish(client: PoolClient, upload: Upload, outcome: Outcome): Promise<void> {
  await client.query(
    `UPDATE imports SET status = $4, rows_total = $5, rows_loaded = $6, rows_rejected = $7
     WHERE bucket = $1 AND key = $2 AND sequencer = $3`,
    [
      upload.bucket,
      upload.key,
      upload.sequencer,
      outcome.status,
      outcome.rows,
      outcome.loaded,
      outcome.rejected,
    ],
  );
}

export function summary(key: string, outcome: Outcome) {
  return {
    key,
    status: outcome.status,
    rows: outcome.rows,
    loaded: outcome.loaded,
    rejected: outcome.rejected,
  };
}

export async function importsOf(key: string | null): Promise<Answer> {
  if (key === null || key === "") {
    return { status: 400, body: { error: "invalid_request" } };
  }
  const found = await pool.query<{
    key: string;
    status: "loaded" | "rejected";
    rows_total: number;
    rows_loaded: number;
    rows_rejected: number;
  }>(
    `SELECT key, status, rows_total, rows_loaded, rows_rejected FROM imports
     WHERE key = $1 ORDER BY id`,
    [key],
  );
  return {
    status: 200,
    body: found.rows.map((row) =>
      summary(row.key, {
        status: row.status,
        rows: row.rows_total,
        loaded: row.rows_loaded,
        rejected: row.rows_rejected,
        report: [],
      }),
    ),
  };
}
