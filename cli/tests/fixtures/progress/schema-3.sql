-- progress.db at schema 3: migrations 0001 to 0003, then rows in every table.
PRAGMA journal_mode = WAL;

-- 0001_init.sql
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

-- 0002_schedule.sql
-- Phase 1 (docs/specs/progress-and-scheduling.md#schema): `cstudy done` schedules reviews

CREATE TABLE schedule (
  slug          TEXT PRIMARY KEY,
  ease          REAL NOT NULL,
  interval_days INTEGER NOT NULL,
  reps          INTEGER NOT NULL,
  lapses        INTEGER NOT NULL,
  due_on        TEXT NOT NULL,
  last_grade    INTEGER NOT NULL,
  updated_at    TEXT NOT NULL
);

-- 0003_bench_runs.sql
-- Phase 2 (docs/specs/progress-and-scheduling.md#schema): `cstudy bench` and `cstudy test --perf` runs.
-- IF NOT EXISTS keeps the script safe to run again, whatever number it ends up with.

CREATE TABLE IF NOT EXISTS bench_runs (
  id             INTEGER PRIMARY KEY,
  attempt_id     INTEGER REFERENCES attempts (id), -- NULL for --refs-only
  slug           TEXT NOT NULL,
  lang           TEXT NOT NULL,
  ran_at         TEXT NOT NULL,
  code_hash      TEXT,
  sizes          TEXT NOT NULL,        -- JSON array
  results        TEXT NOT NULL,        -- JSON {target_id: {size: {median_ns, spread, cpu_ns, calls, mem_bytes, mem_metric, status, exceeded_ns}}}
  user_time_band TEXT,
  user_mem_band  TEXT,
  slope          REAL,
  r2             REAL,
  reference_id   TEXT,                 -- optimal approach compared against
  ratio          REAL,                 -- user / reference at the largest common size
  verdict        TEXT NOT NULL CHECK (verdict IN ('optimal', 'near-optimal', 'suboptimal', 'unknown')),
  confidence     TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
  env            TEXT NOT NULL         -- JSON: cpu, power, load, cores, runtime, references_hash
);
CREATE INDEX IF NOT EXISTS bench_runs_by_problem ON bench_runs (slug, lang, ran_at);

-- Rows
INSERT INTO meta (key, value) VALUES
  ('schema_version', '3');

INSERT INTO attempts (id, slug, lang, mode, status, started_at, ended_at, first_pass_at, time_limit_s, rating, grade, hints_used, solution_revealed, level_unlocked, stub_path, archive_path, notes) VALUES
  (1, 'two-sum', 'python', 'new', 'passed', '2026-10-01T09:00:00+00:00', '2026-10-01T09:25:00+00:00', '2026-10-01T09:24:00+00:00', 1500, 'easy', 3, 0, 0, NULL, 'python/practice/two_sum.py', '.archive/two-sum/1-python', 'hash map, one pass'),
  (2, 'valid-parentheses', 'typescript', 'review', 'failed', '2026-10-02T09:00:00+00:00', '2026-10-02T09:40:00+00:00', NULL, NULL, 'hard', 1, 2, 1, NULL, 'typescript/practice/valid-parentheses.ts', NULL, 'forgot the empty string'),
  (3, 'lru-cache', 'java', 'mock', 'in_progress', '2026-10-03T09:00:00+00:00', NULL, NULL, 2700, NULL, NULL, 0, 0, NULL, 'jvm/java/src/main/java/practice/LruCache.java', NULL, NULL),
  (4, 'merge-intervals', 'kotlin', 'new', 'abandoned', '2026-10-04T09:00:00+00:00', '2026-10-04T09:10:00+00:00', NULL, NULL, 'ok', 0, 3, 0, NULL, 'jvm/kotlin/src/main/kotlin/practice/MergeIntervals.kt', NULL, 'switched to review first'),
  (5, 'design-url-shortener', NULL, 'new', 'passed', '2026-10-05T09:00:00+00:00', '2026-10-05T10:00:00+00:00', '2026-10-05T10:00:00+00:00', NULL, 'ok', 2, 0, 0, NULL, NULL, NULL, 'notes/design-url-shortener.md');

INSERT INTO test_runs (id, attempt_id, ran_at, code_hash, total, passed, failed, errored, timed_out, tle, time_limit, duration_ms) VALUES
  (1, 1, '2026-10-01T09:10:00+00:00', 'a1b2c3', 12, 12, 0, 0, 0, 0, NULL, 840),
  (2, 2, '2026-10-02T09:30:00+00:00', 'd4e5f6', 12, 9, 2, 1, 0, 0, '5x', 1310),
  (3, 3, '2026-10-03T09:20:00+00:00', '0a1b2c', 8, 6, 0, 0, 1, 1, '1500ms', 4200);

INSERT INTO schedule (slug, ease, interval_days, reps, lapses, due_on, last_grade, updated_at) VALUES
  ('two-sum', 2.5, 6, 2, 0, '2026-10-07', 3, '2026-10-01T09:25:00+00:00'),
  ('valid-parentheses', 2.1, 1, 0, 1, '2026-10-03', 1, '2026-10-02T09:40:00+00:00');

INSERT INTO bench_runs (id, attempt_id, slug, lang, ran_at, code_hash, sizes, results, user_time_band, user_mem_band, slope, r2, reference_id, ratio, verdict, confidence, env) VALUES
  (1, 1, 'two-sum', 'python', '2026-10-01T09:12:00+00:00', 'a1b2c3', '[100, 1000]', '{"user": {"1000": {"median_ns": 120000, "status": "ok"}}}', 'O(n)', 'O(n)', 1.02, 0.99, 'hash-map', 1.1, 'optimal', 'high', '{"cpu": "test", "cores": 8}'),
  (2, 2, 'valid-parentheses', 'typescript', '2026-10-02T09:32:00+00:00', 'd4e5f6', '[100, 1000]', '{"user": {"1000": {"median_ns": 120000, "status": "ok"}}}', 'O(n)', 'O(n)', 1.1, 0.97, 'stack', 1.4, 'near-optimal', 'medium', '{"cpu": "test", "cores": 8}'),
  (3, 3, 'lru-cache', 'java', '2026-10-03T09:22:00+00:00', '0a1b2c', '[100, 1000]', '{"user": {"1000": {"median_ns": 120000, "status": "ok"}}}', 'O(n^2)', 'O(n)', 2.0, 0.95, 'linked-hash-map', 9.5, 'suboptimal', 'low', '{"cpu": "test", "cores": 8}'),
  (4, NULL, 'two-sum', 'python', '2026-10-09T09:00:00+00:00', NULL, '[100, 1000]', '{"user": {"1000": {"median_ns": 120000, "status": "ok"}}}', NULL, NULL, NULL, NULL, NULL, NULL, 'unknown', 'low', '{"cpu": "test", "cores": 8}');
