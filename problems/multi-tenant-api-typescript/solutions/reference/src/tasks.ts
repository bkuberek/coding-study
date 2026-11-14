// Tasks. A task's project comes from the path and is looked for in the caller's organization
// first, since the database would let a task of one organization name another's project if the
// key named the project alone.

import { type Answer, invalidRequest, notFound, ok } from "./answers.ts";
import type { Caller } from "./auth.ts";
import type { Connection } from "./db.ts";
import { findProject } from "./projects.ts";
import { taskChange, taskRequest } from "./requests.ts";

type TaskRow = { id: string; project: string; title: string; done: boolean };

const TASK_COLUMNS = "id, project_id AS project, title, done";

export async function findTask(
  db: Connection,
  caller: Caller,
  id: string,
): Promise<TaskRow | undefined> {
  const found = await db.query<TaskRow>(
    `SELECT ${TASK_COLUMNS} FROM tasks WHERE id = $1 AND tenant_id = $2`,
    [id, caller.tenant],
  );
  return found.rows[0];
}

export async function listTasks(db: Connection, caller: Caller, projectId: string): Promise<Answer> {
  if ((await findProject(db, caller, projectId)) === undefined) {
    return notFound;
  }
  const found = await db.query<TaskRow>(
    `SELECT ${TASK_COLUMNS} FROM tasks WHERE project_id = $1 AND tenant_id = $2`,
    [projectId, caller.tenant],
  );
  return ok(found.rows);
}

export async function task(db: Connection, caller: Caller, id: string): Promise<Answer> {
  const found = await findTask(db, caller, id);
  return found === undefined ? notFound : ok(found);
}

export async function createTask(
  db: Connection,
  caller: Caller,
  projectId: string,
  body: unknown,
): Promise<Answer> {
  if ((await findProject(db, caller, projectId)) === undefined) {
    return notFound;
  }
  const request = taskRequest(body);
  if (request === undefined) {
    return invalidRequest;
  }
  const created = await db.query<TaskRow>(
    `INSERT INTO tasks (tenant_id, project_id, title) VALUES ($1, $2, $3) RETURNING ${TASK_COLUMNS}`,
    [caller.tenant, projectId, request.title],
  );
  return ok(created.rows[0], 201);
}

export async function changeTask(
  db: Connection,
  caller: Caller,
  id: string,
  body: unknown,
): Promise<Answer> {
  if ((await findTask(db, caller, id)) === undefined) {
    return notFound;
  }
  const change = taskChange(body);
  if (change === undefined) {
    return invalidRequest;
  }
  const changed = await db.query<TaskRow>(
    "UPDATE tasks SET title = COALESCE($3, title), done = COALESCE($4, done) " +
      `WHERE id = $1 AND tenant_id = $2 RETURNING ${TASK_COLUMNS}`,
    [id, caller.tenant, change.title ?? null, change.done ?? null],
  );
  const row = changed.rows[0];
  return row === undefined ? notFound : ok(row);
}

export async function deleteTask(db: Connection, caller: Caller, id: string): Promise<Answer> {
  const deleted = await db.query<TaskRow>(
    `DELETE FROM tasks WHERE id = $1 AND tenant_id = $2 RETURNING ${TASK_COLUMNS}`,
    [id, caller.tenant],
  );
  const row = deleted.rows[0];
  return row === undefined ? notFound : ok(row);
}
