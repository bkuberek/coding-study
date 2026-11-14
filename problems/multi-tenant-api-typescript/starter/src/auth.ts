// Who is calling: the organization and the user an API key belongs to, sent as
// `Authorization: Bearer <key>`. Keys live in `api_keys`, the one table read before the
// organization is known.

import { pool } from "./db.ts";

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
