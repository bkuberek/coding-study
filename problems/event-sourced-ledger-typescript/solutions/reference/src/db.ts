// The connection pool every route shares, transactions on one connection of it, and the retry that
// optimistic concurrency needs. `DATABASE_URL` comes from the sandbox's settings.

import pg from "pg";

export const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL, max: 10 });

export type Connection = pg.PoolClient;
// The pool or one of its connections: a read needs no transaction of its own.
export type Queryable = Pick<pg.Pool, "query">;

const UNIQUE_VIOLATION = "23505";
// More than a burst of writers to one stream can force: each lost race means that another
// transaction appended and committed, so the attempts stop long before this.
const MAX_ATTEMPTS = 100;

// Runs `work` in one transaction on one connection: committed when it returns, rolled back when
// it throws.
export async function inTransaction<T>(work: (connection: Connection) => Promise<T>): Promise<T> {
  const connection = await pool.connect();
  try {
    await connection.query("BEGIN");
    const result = await work(connection);
    await connection.query("COMMIT");
    return result;
  } catch (error) {
    await connection.query("ROLLBACK");
    throw error;
  } finally {
    connection.release();
  }
}

// Runs `work` in a transaction until it commits without losing a race. An append at a version, or
// with an event id, that another transaction wrote first fails on a unique index; `work` then
// starts over from what is committed now, and sees the version or the event id the winner wrote.
export async function untilAppended<T>(work: (connection: Connection) => Promise<T>): Promise<T> {
  for (let attempt = 1; ; attempt += 1) {
    try {
      return await inTransaction(work);
    } catch (error) {
      if (!lostRace(error) || attempt === MAX_ATTEMPTS) {
        throw error;
      }
    }
  }
}

function lostRace(error: unknown): boolean {
  return error instanceof pg.DatabaseError && error.code === UNIQUE_VIOLATION;
}
