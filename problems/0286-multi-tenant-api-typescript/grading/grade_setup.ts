// Problem-owned `grade_setup`: node-pg-migrate, the project's own tool, applies only the baseline,
// as the owner, and records it as it records any migration; then a third organization goes into
// it, with its own key, project and tasks. `bootstrap` applies the rest afterwards, so your
// policies must hold for rows you never saw, and your app must find keys in the database. Hidden
// ids and keys start with `x-`, which the statement reserves.
//
// The script lives outside the project, so it loads the project's packages from the project
// folder, its working directory.

import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const projectRequire = createRequire(join(process.cwd(), "package.json"));
const migrate = await import(pathToFileURL(projectRequire.resolve("node-pg-migrate")).href);
const pg = await import(pathToFileURL(projectRequire.resolve("pg")).href);

const HIDDEN_ORGANIZATION = [
  "INSERT INTO tenants (id, name) VALUES ('x-cedar', 'Cedar Labs')",
  "INSERT INTO users (id, tenant_id, name, role) VALUES ('x-u-cy', 'x-cedar', 'Cy', 'admin')",
  "INSERT INTO api_keys (key, tenant_id, user_id) VALUES ('x-key-cy', 'x-cedar', 'x-u-cy')",
  "INSERT INTO projects (id, tenant_id, name) VALUES ('x-p-1', 'x-cedar', 'Launch week')",
  "INSERT INTO tasks (id, tenant_id, project_id, title, done) VALUES " +
    "('x-t-1', 'x-cedar', 'x-p-1', 'Plan the launch party', false), " +
    "('x-t-2', 'x-cedar', 'x-p-1', 'Print the badges', true)",
];

await migrate.runner({
  databaseUrl: process.env.OWNER_DATABASE_URL,
  dir: join(import.meta.dirname, "baseline"),
  direction: "up",
  count: 1,
  migrationsTable: "pgmigrations",
  log: () => {},
});

const database = new pg.default.Client({ connectionString: process.env.OWNER_DATABASE_URL });
await database.connect();
try {
  for (const statement of HIDDEN_ORGANIZATION) {
    await database.query(statement);
  }
} finally {
  await database.end();
}
