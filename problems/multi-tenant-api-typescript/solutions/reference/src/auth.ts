// Who is calling: the organization and the user an API key belongs to, sent as
// `Authorization: Bearer <key>`. Keys live in `api_keys`, the one table read before the
// organization is known; a role is read afterwards, inside the organization's transaction.

import { type Connection, pool } from "./db.ts";

export type Caller = { tenant: string; user: string };

const BEARER = /^Bearer (\S+)$/;

export async function authenticate(header: string | undefined): Promise<Caller | undefined> {
  const key = header === undefined ? undefined : BEARER.exec(header)?.[1];
  if (key === undefined) {
    return undefined;
  }
  const found = await pool.query<{ tenant_id: string; user_id: string }>(
    "SELECT tenant_id, user_id FROM api_keys WHERE key = $1",
    [key],
  );
  const row = found.rows[0];
  return row === undefined ? undefined : { tenant: row.tenant_id, user: row.user_id };
}

// Read on each request, so a role an admin just changed applies to the very next one.
export async function isAdmin(db: Connection, caller: Caller): Promise<boolean> {
  const found = await db.query<{ role: string }>(
    "SELECT role FROM users WHERE id = $1 AND tenant_id = $2",
    [caller.user, caller.tenant],
  );
  return found.rows[0]?.role === "admin";
}
