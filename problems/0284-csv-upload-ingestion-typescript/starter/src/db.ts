// The connection pool. `DATABASE_URL` comes from the sandbox's settings.

import pg from "pg";

export const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL, max: 5 });
