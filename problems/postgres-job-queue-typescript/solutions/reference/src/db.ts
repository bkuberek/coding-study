// The connection pool every route shares, and transactions on one connection of it.
// `DATABASE_URL` comes from the sandbox's settings.

import pg from "pg";

export const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL, max: 10 });

export type Connection = pg.PoolClient;

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
