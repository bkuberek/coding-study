// An organization's members. A role changes only through an admin's `PATCH /members/{id}`:
// `PATCH /me` reads a name and nothing else, whatever else its body says.

import { type Answer, forbidden, invalidRequest, notFound, ok } from "./answers.ts";
import { type Caller, isAdmin } from "./auth.ts";
import type { Connection } from "./db.ts";
import { nameChange, roleChange } from "./requests.ts";

type MemberRow = { id: string; name: string; role: string };

const MEMBER_COLUMNS = "id, name, role";

export async function listMembers(db: Connection, caller: Caller): Promise<Answer> {
  const found = await db.query<MemberRow>(
    `SELECT ${MEMBER_COLUMNS} FROM users WHERE tenant_id = $1`,
    [caller.tenant],
  );
  return ok(found.rows);
}

export async function changeMe(db: Connection, caller: Caller, body: unknown): Promise<Answer> {
  const change = nameChange(body);
  if (change === undefined) {
    return invalidRequest;
  }
  const changed = await db.query<MemberRow>(
    `UPDATE users SET name = $3 WHERE id = $1 AND tenant_id = $2 RETURNING ${MEMBER_COLUMNS}`,
    [caller.user, caller.tenant, change.name],
  );
  return ok(changed.rows[0]);
}

export async function changeRole(
  db: Connection,
  caller: Caller,
  userId: string,
  body: unknown,
): Promise<Answer> {
  const found = await db.query("SELECT 1 FROM users WHERE id = $1 AND tenant_id = $2", [
    userId,
    caller.tenant,
  ]);
  if (found.rowCount === 0) {
    return notFound;
  }
  if (!(await isAdmin(db, caller))) {
    return forbidden;
  }
  const change = roleChange(body);
  if (change === undefined) {
    return invalidRequest;
  }
  const changed = await db.query<MemberRow>(
    `UPDATE users SET role = $3 WHERE id = $1 AND tenant_id = $2 RETURNING ${MEMBER_COLUMNS}`,
    [userId, caller.tenant, change.role],
  );
  return ok(changed.rows[0]);
}
