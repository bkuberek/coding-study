// `GET /search/tasks?q=`: the tasks whose title holds `q`, whatever its case. Its query names no
// organization, on purpose, and must keep it that way: it stands for the query somebody forgets to
// scope. Level 2 makes the database scope it. You may change what it runs on, never what it asks.

import { type Answer, ok, refused } from "./answers.ts";
import type { Queryable } from "./db.ts";

const LONGEST_TERM = 100;

export async function searchTasks(db: Queryable, query: URLSearchParams): Promise<Answer> {
  const term = query.get("q");
  if (term === null || term.length === 0 || term.length > LONGEST_TERM) {
    return refused(400, "invalid_request");
  }
  const found = await db.query(
    "SELECT id, project_id AS project, title, done FROM tasks " +
      "WHERE strpos(lower(title), lower($1)) > 0",
    [term],
  );
  return ok(found.rows);
}
