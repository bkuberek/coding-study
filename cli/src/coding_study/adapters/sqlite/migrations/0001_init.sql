-- Phase 0 (docs/specs/progress-and-scheduling.md#schema)

CREATE TABLE meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE attempts (
  id                INTEGER PRIMARY KEY,
  slug              TEXT NOT NULL,
  lang              TEXT CHECK (lang IN ('python', 'typescript', 'java', 'kotlin')), -- NULL: not autograded
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
CREATE INDEX attempts_by_slug ON attempts (slug, ended_at);

CREATE TABLE test_runs (
  id          INTEGER PRIMARY KEY,
  attempt_id  INTEGER NOT NULL REFERENCES attempts (id),
  ran_at      TEXT NOT NULL,
  code_hash   TEXT NOT NULL,           -- sha256 of the user file(s)
  total       INTEGER NOT NULL,
  passed      INTEGER NOT NULL,
  failed      INTEGER NOT NULL,
  errored     INTEGER NOT NULL,
  timed_out   INTEGER NOT NULL,
  tle         INTEGER NOT NULL,
  time_limit  TEXT,                    -- "5x", "1500ms", or NULL when off
  duration_ms INTEGER NOT NULL
);
