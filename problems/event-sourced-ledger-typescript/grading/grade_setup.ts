// Problem-owned `grade_setup`: node-pg-migrate, the project's own tool, applies only the baseline,
// and records it as it records any migration; then the hidden events are appended to the store,
// as another service writing to it would. `bootstrap` applies the rest afterwards, so your
// projection must come from the events the store holds, not from what your code wrote. Hidden
// account ids start with `x-`, which the statement reserves.
//
// The script lives outside the project, so it loads the project's packages from the project
// folder, its working directory.

import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const projectRequire = createRequire(join(process.cwd(), "package.json"));
const migrate = await import(pathToFileURL(projectRequire.resolve("node-pg-migrate")).href);
const pg = await import(pathToFileURL(projectRequire.resolve("pg")).href);

const APPEND =
  "INSERT INTO events (stream_id, version, event_id, type, data, recorded_at) " +
  "VALUES ($1, $2, $3, $4, $5, $6)";

const hidden = JSON.parse(await readFile(join(import.meta.dirname, "hidden_events.json"), "utf8"));

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
  for (const event of hidden) {
    await database.query(APPEND, [
      event.stream_id,
      event.version,
      event.event_id,
      event.type,
      event.data,
      event.recorded_at,
    ]);
  }
} finally {
  await database.end();
}
