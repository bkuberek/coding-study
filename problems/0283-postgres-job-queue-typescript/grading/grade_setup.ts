// Problem-owned `grade_setup`: node-pg-migrate, the project's own tool, applies only the baseline,
// and records it as it records any migration; then the hidden jobs go into it, waiting as the
// first version left them. `bootstrap` applies the rest afterwards, so your migrations must carry
// these rows forward. Hidden job ids and queues start with `x-`, which the statement reserves.
//
// The script lives outside the project, so it loads the project's packages from the project
// folder, its working directory.

import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const projectRequire = createRequire(join(process.cwd(), "package.json"));
const migrate = await import(pathToFileURL(projectRequire.resolve("node-pg-migrate")).href);
const pg = await import(pathToFileURL(projectRequire.resolve("pg")).href);

const HIDDEN_JOBS =
  "INSERT INTO jobs (id, queue, tenant, payload, urgent, enqueued_at) VALUES " +
  "('x-old-1', 'x-backlog', 'harbor', '{\"report\": \"audit\"}', false, '2027-02-27 08:00:00+00'), " +
  "('x-old-2', 'x-backlog', 'lumen', '{\"report\": \"payroll\"}', false, '2027-02-27 08:30:00+00'), " +
  "('x-r1', 'x-rush', 'harbor', '{\"report\": \"stock\"}', false, '2027-02-28 10:00:00+00'), " +
  "('x-r2', 'x-rush', 'harbor', '{\"report\": \"recall\"}', true, '2027-02-28 10:30:00+00')";

await migrate.runner({
  databaseUrl: process.env.DATABASE_URL,
  dir: join(import.meta.dirname, "baseline"),
  direction: "up",
  count: 1,
  migrationsTable: "pgmigrations",
  log: () => {},
});

const database = new pg.default.Client({ connectionString: process.env.DATABASE_URL });
await database.connect();
try {
  await database.query(HIDDEN_JOBS);
} finally {
  await database.end();
}
