// `commands.reset`, run by cstudy with your app stopped. `prepare` keeps a copy of the migrated
// database once, before the app starts; `apply` puts that copy back before a case that starts
// fresh. You should not need to change it.

import pg from "pg";

const SNAPSHOT = "app_snapshot";

const url = new URL(process.env.DATABASE_URL ?? "");
const name = url.pathname.slice(1);
url.pathname = "/postgres";
const server = new pg.Client({ connectionString: url.toString() });

await server.connect();
try {
  if (process.env.CSTUDY_RESET_PHASE === "prepare") {
    await server.query(`DROP DATABASE IF EXISTS ${SNAPSHOT}`);
    await server.query(`CREATE DATABASE ${SNAPSHOT} TEMPLATE ${name}`);
  } else {
    await server.query(`DROP DATABASE ${name} WITH (FORCE)`);
    await server.query(`CREATE DATABASE ${name} TEMPLATE ${SNAPSHOT}`);
  }
} finally {
  await server.end();
}
