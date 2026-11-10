// Problem-owned `grade_setup`: node-pg-migrate, the project's own tool, applies only the baseline,
// and records it as it records any migration; then the hidden products go into it. `bootstrap`
// applies the rest afterwards, so your migrations must carry these rows forward. Hidden SKUs start
// with `x-`, which the statement reserves.
//
// The script lives outside the project, so it loads the project's packages from the project
// folder, its working directory.

import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const projectRequire = createRequire(join(process.cwd(), "package.json"));
const migrate = await import(pathToFileURL(projectRequire.resolve("node-pg-migrate")).href);
const pg = await import(pathToFileURL(projectRequire.resolve("pg")).href);

const HIDDEN_PRODUCTS =
  "INSERT INTO products (sku, name, stock) VALUES " +
  "('x-heater', 'Space heater', 7), ('x-fan', 'Desk fan', 0)";

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
  await database.query(HIDDEN_PRODUCTS);
} finally {
  await database.end();
}
