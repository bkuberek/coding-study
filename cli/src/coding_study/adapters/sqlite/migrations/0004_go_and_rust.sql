-- Go and Rust attempts (docs/decisions/0012-go-and-rust.md). SQLite cannot change a CHECK
-- constraint, so `attempts` is rebuilt the documented way: foreign keys off, copy into a new table,
-- drop, rename and recreate the index. test_runs and bench_runs refer to `attempts` by name, so
-- their foreign keys point at the new table.

PRAGMA foreign_keys = OFF;
BEGIN;

CREATE TABLE attempts_with_go_and_rust (
  id                INTEGER PRIMARY KEY,
  slug              TEXT NOT NULL,
  lang              TEXT CHECK (lang IN ('python', 'typescript', 'java', 'kotlin', 'go', 'rust')), -- NULL: not autograded
  mode              TEXT NOT NULL CHECK (mode IN ('new', 'review', 'mock')),
  status            TEXT NOT NULL CHECK (status IN ('in_progress', 'passed', 'failed', 'abandoned')),
  started_at        TEXT NOT NULL,
  ended_at          TEXT,
  first_pass_at     TEXT,
  time_limit_s      INTEGER,           -- --timer
  rating            TEXT CHECK (rating IN ('easy', 'ok', 'hard')),
  grade             INTEGER CHECK (grade BETWEEN 0 AND 3),
  hints_used        INTEGER NOT NULL DEFAULT 0,
  solution_revealed INTEGER NOT NULL DEFAULT 0,
  level_unlocked    INTEGER,           -- progressive problems
  stub_path         TEXT,
  archive_path      TEXT,
  notes             TEXT
);
INSERT INTO attempts_with_go_and_rust SELECT * FROM attempts;
DROP TABLE attempts;
ALTER TABLE attempts_with_go_and_rust RENAME TO attempts;
CREATE INDEX attempts_by_slug ON attempts (slug, ended_at);

COMMIT;
PRAGMA foreign_keys = ON;
