// The connection pool every route shares. `DATABASE_URL` comes from the sandbox's settings and
// connects as `tracker_app`, which owns no table and cannot bypass row-level security.

import pg from "pg";

export const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL, max: 10 });

// What a query runs on: the pool, or one connection taken from it.
export type Queryable = pg.Pool | pg.PoolClient;
