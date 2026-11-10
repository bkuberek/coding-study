// `GET /search/tasks` and `GET /search/comments`. Their queries name no organization, as the
// statement requires: they run on the request's transaction, where `app.tenant_id` says whose
// rows exist, and the policies on `tasks` and `comments` scope them. That is the point: a query
// somebody forgets to scope still answers for one organization.

import { type Answer, invalidRequest, ok } from "./answers.ts";
import type { Queryable } from "./db.ts";
import { searchTerm } from "./requests.ts";

async function search(db: Queryable, sql: string, query: URLSearchParams): Promise<Answer> {
  const term = searchTerm(query);
  if (term === undefined) {
    return invalidRequest;
  }
  const found = await db.query(sql, [term]);
  return ok(found.rows);
}

export function searchTasks(db: Queryable, query: URLSearchParams): Promise<Answer> {
  const sql =
    "SELECT id, project_id AS project, title, done FROM tasks " +
    "WHERE strpos(lower(title), lower($1)) > 0";
  return search(db, sql, query);
}

export function searchComments(db: Queryable, query: URLSearchParams): Promise<Answer> {
  const sql =
    "SELECT id, task_id AS task, author_id AS author, body FROM comments " +
    "WHERE strpos(lower(body), lower($1)) > 0";
  return search(db, sql, query);
}
