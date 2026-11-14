// The connection pool every route shares, and the transaction every request runs in.
// `DATABASE_URL` connects as `tracker_app`, which owns no table, so every policy applies to it.

import pg from "pg";

export const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL, max: 10 });

// What a query runs on: the pool, or one connection taken from it.
export type Queryable = pg.Pool | pg.PoolClient;
export type Connection = pg.PoolClient;

// Runs `work` in one transaction on one connection, for one organization: committed when it
// returns, rolled back when it throws. `set_config(..., true)` is `SET LOCAL` with a parameter:
// the setting ends with the transaction, so the connection goes back to the pool serving nobody.
export async function asTenant<T>(
  tenant: string,
  work: (connection: Connection) => Promise<T>,
): Promise<T> {
  const connection = await pool.connect();
  try {
    await connection.query("BEGIN");
    await connection.query("SELECT set_config('app.tenant_id', $1, true)", [tenant]);
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
