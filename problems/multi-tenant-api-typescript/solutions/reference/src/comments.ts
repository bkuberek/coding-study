// Comments on tasks. The task is looked for in the caller's organization first, and the author is
// the caller, whatever the body says.

import { type Answer, invalidRequest, notFound, ok } from "./answers.ts";
import type { Caller } from "./auth.ts";
import type { Connection } from "./db.ts";
import { commentRequest } from "./requests.ts";
import { findTask } from "./tasks.ts";

type CommentRow = { id: string; task: string; author: string; body: string };

const COMMENT_COLUMNS = "id, task_id AS task, author_id AS author, body";

export async function listComments(db: Connection, caller: Caller, taskId: string): Promise<Answer> {
  if ((await findTask(db, caller, taskId)) === undefined) {
    return notFound;
  }
  const found = await db.query<CommentRow>(
    `SELECT ${COMMENT_COLUMNS} FROM comments WHERE task_id = $1 AND tenant_id = $2`,
    [taskId, caller.tenant],
  );
  return ok(found.rows);
}

export async function addComment(
  db: Connection,
  caller: Caller,
  taskId: string,
  body: unknown,
): Promise<Answer> {
  if ((await findTask(db, caller, taskId)) === undefined) {
    return notFound;
  }
  const request = commentRequest(body);
  if (request === undefined) {
    return invalidRequest;
  }
  const created = await db.query<CommentRow>(
    "INSERT INTO comments (tenant_id, task_id, author_id, body) VALUES ($1, $2, $3, $4) " +
      `RETURNING ${COMMENT_COLUMNS}`,
    [caller.tenant, taskId, caller.user, request.body],
  );
  return ok(created.rows[0], 201);
}
