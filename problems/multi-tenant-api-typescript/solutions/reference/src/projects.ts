// Projects. Each query names the caller's organization, and the policy on `projects` would hide
// another organization's rows even if one did not.

import { type Answer, forbidden, invalidRequest, notFound, ok } from "./answers.ts";
import { type Caller, isAdmin } from "./auth.ts";
import type { Connection } from "./db.ts";
import { projectRequest } from "./requests.ts";

type ProjectRow = { id: string; name: string };

export async function findProject(
  db: Connection,
  caller: Caller,
  id: string,
): Promise<ProjectRow | undefined> {
  const found = await db.query<ProjectRow>(
    "SELECT id, name FROM projects WHERE id = $1 AND tenant_id = $2",
    [id, caller.tenant],
  );
  return found.rows[0];
}

export async function listProjects(db: Connection, caller: Caller): Promise<Answer> {
  const found = await db.query<ProjectRow>("SELECT id, name FROM projects WHERE tenant_id = $1", [
    caller.tenant,
  ]);
  return ok(found.rows);
}

export async function project(db: Connection, caller: Caller, id: string): Promise<Answer> {
  const found = await findProject(db, caller, id);
  return found === undefined ? notFound : ok(found);
}

export async function createProject(db: Connection, caller: Caller, body: unknown): Promise<Answer> {
  const request = projectRequest(body);
  if (request === undefined) {
    return invalidRequest;
  }
  const created = await db.query<ProjectRow>(
    "INSERT INTO projects (tenant_id, name) VALUES ($1, $2) RETURNING id, name",
    [caller.tenant, request.name],
  );
  return ok(created.rows[0], 201);
}

// The project is looked for before the role is checked, so a member hears 403 only about a
// project of their own organization, and 404 about any other id, as an admin would.
export async function deleteProject(db: Connection, caller: Caller, id: string): Promise<Answer> {
  if ((await findProject(db, caller, id)) === undefined) {
    return notFound;
  }
  if (!(await isAdmin(db, caller))) {
    return forbidden;
  }
  const deleted = await db.query<ProjectRow>(
    "DELETE FROM projects WHERE id = $1 AND tenant_id = $2 RETURNING id, name",
    [id, caller.tenant],
  );
  const row = deleted.rows[0];
  return row === undefined ? notFound : ok(row);
}
