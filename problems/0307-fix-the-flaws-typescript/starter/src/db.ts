// The service's one SQLite database, in CSTUDY_DATA_DIR, created on the first start.

import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { DatabaseSync } from "node:sqlite";

const folder = process.env.CSTUDY_DATA_DIR ?? "data";
mkdirSync(folder, { recursive: true });

export const db = new DatabaseSync(join(folder, "notes.db"));

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL
  );
  CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id)
  );
  CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users (id),
    title TEXT NOT NULL,
    body TEXT NOT NULL
  );
`);
