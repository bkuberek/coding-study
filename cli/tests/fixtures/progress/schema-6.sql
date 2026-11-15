-- progress.db at schema 6: migrations 0001 to 0006, then rows in every table.
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

-- 0004_go_and_rust.sql
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

-- 0005_project_problems.sql
-- Phase 8 (docs/specs/progress-and-scheduling.md#project-attempts): `cstudy submit` and the levels it opens.
-- IF NOT EXISTS keeps the script safe to run again, whatever number it ends up with.

CREATE TABLE IF NOT EXISTS submissions (             -- project problems: one row per cstudy submit
  id            INTEGER PRIMARY KEY,
  attempt_id    INTEGER NOT NULL REFERENCES attempts (id),
  submitted_at  TEXT NOT NULL,
  code_hash     TEXT NOT NULL,         -- sha256 of the project folder
  graded_up_to  INTEGER NOT NULL,      -- levels 1 to this one were graded
  every_level   INTEGER NOT NULL,      -- 1 when graded_up_to was the unlocked level
  levels        TEXT NOT NULL,         -- JSON [{level, total, passed, visible_total, visible_passed, hidden_total, hidden_passed}]
  total         INTEGER NOT NULL,
  passed        INTEGER NOT NULL,
  failed        INTEGER NOT NULL,
  errored       INTEGER NOT NULL,
  timed_out     INTEGER NOT NULL,
  duration_ms   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS submissions_by_attempt ON submissions (attempt_id, submitted_at);

CREATE TABLE IF NOT EXISTS level_unlocks (           -- project problems: when each level opened
  attempt_id   INTEGER NOT NULL REFERENCES attempts (id),
  level        INTEGER NOT NULL,
  unlocked_at  TEXT NOT NULL,
  PRIMARY KEY (attempt_id, level)
);

-- 0006_level_passes.sql
-- Level passes (docs/decisions/0024-level-passes.md): a pass through level N of M counts.
-- Rows written before this migration keep NULL: a `passed` attempt then passed every level, and
-- a test run counts every level when it passed every case.

ALTER TABLE attempts ADD COLUMN levels_passed INTEGER;   -- levels 1 to N passed, at cstudy done
ALTER TABLE attempts ADD COLUMN levels_total INTEGER;    -- the problem's levels, at cstudy done
ALTER TABLE test_runs ADD COLUMN levels_passed INTEGER;  -- progressive: levels 1 to N passed
ALTER TABLE schedule ADD COLUMN levels TEXT;             -- JSON [{level, ease, interval_days, reps, lapses, last_grade}] from level 2

-- Rows
INSERT INTO meta (key, value) VALUES
  ('schema_version', '6');

INSERT INTO attempts (id, slug, lang, mode, status, started_at, ended_at, first_pass_at, time_limit_s, rating, grade, hints_used, solution_revealed, level_unlocked, stub_path, archive_path, notes, levels_passed, levels_total) VALUES
  (1, 'two-sum', 'python', 'new', 'passed', '2026-10-01T09:00:00+00:00', '2026-10-01T09:25:00+00:00', '2026-10-01T09:24:00+00:00', 1500, 'easy', 3, 0, 0, NULL, 'python/practice/two_sum.py', '.archive/two-sum/1-python', 'hash map, one pass', NULL, NULL),
  (2, 'valid-parentheses', 'typescript', 'review', 'failed', '2026-10-02T09:00:00+00:00', '2026-10-02T09:40:00+00:00', NULL, NULL, 'hard', 1, 2, 1, NULL, 'typescript/practice/valid-parentheses.ts', NULL, 'forgot the empty string', NULL, NULL),
  (3, 'lru-cache', 'java', 'mock', 'in_progress', '2026-10-03T09:00:00+00:00', NULL, NULL, 2700, NULL, NULL, 0, 0, NULL, 'jvm/java/src/main/java/practice/LruCache.java', NULL, NULL, NULL, NULL),
  (4, 'merge-intervals', 'kotlin', 'new', 'abandoned', '2026-10-04T09:00:00+00:00', '2026-10-04T09:10:00+00:00', NULL, NULL, 'ok', 0, 3, 0, NULL, 'jvm/kotlin/src/main/kotlin/practice/MergeIntervals.kt', NULL, 'switched to review first', NULL, NULL),
  (5, 'design-url-shortener', NULL, 'new', 'passed', '2026-10-05T09:00:00+00:00', '2026-10-05T10:00:00+00:00', '2026-10-05T10:00:00+00:00', NULL, 'ok', 2, 0, 0, NULL, NULL, NULL, 'notes/design-url-shortener.md', NULL, NULL),
  (6, 'word-ladder', 'go', 'review', 'passed', '2026-10-06T09:00:00+00:00', '2026-10-06T09:35:00+00:00', '2026-10-06T09:35:00+00:00', 1800, 'ok', 2, 1, 0, NULL, 'go/practice/word_ladder/word_ladder.go', NULL, NULL, NULL, NULL),
  (7, 'matrix-spiral', 'rust', 'mock', 'failed', '2026-10-07T09:00:00+00:00', '2026-10-07T09:50:00+00:00', NULL, 2400, 'hard', 0, 0, 1, NULL, 'rust/practice/matrix_spiral.rs', NULL, 'off by one at the corners', NULL, NULL),
  (8, 'bank-project-python', 'python', 'new', 'passed', '2026-10-08T09:00:00+00:00', '2026-10-08T12:00:00+00:00', '2026-10-08T12:00:00+00:00', NULL, 'ok', 2, 1, 0, 3, 'projects/bank-project-python', '.archive/bank-project-python/8-python', NULL, 2, 3);

INSERT INTO test_runs (id, attempt_id, ran_at, code_hash, total, passed, failed, errored, timed_out, tle, time_limit, duration_ms, levels_passed) VALUES
  (1, 1, '2026-10-01T09:10:00+00:00', 'a1b2c3', 12, 12, 0, 0, 0, 0, NULL, 840, NULL),
  (2, 2, '2026-10-02T09:30:00+00:00', 'd4e5f6', 12, 9, 2, 1, 0, 0, '5x', 1310, NULL),
  (3, 3, '2026-10-03T09:20:00+00:00', '0a1b2c', 8, 6, 0, 0, 1, 1, '1500ms', 4200, NULL),
  (4, 8, '2026-10-08T11:30:00+00:00', '9f8e7d', 30, 30, 0, 0, 0, 0, NULL, 5100, 2);

INSERT INTO schedule (slug, ease, interval_days, reps, lapses, due_on, last_grade, updated_at, levels) VALUES
  ('two-sum', 2.5, 6, 2, 0, '2026-10-07', 3, '2026-10-01T09:25:00+00:00', NULL),
  ('valid-parentheses', 2.1, 1, 0, 1, '2026-10-03', 1, '2026-10-02T09:40:00+00:00', NULL),
  ('bank-project-python', 2.36, 3, 1, 0, '2026-10-11', 2, '2026-10-08T12:00:00+00:00', '[{"level": 2, "ease": 2.3, "interval_days": 3, "reps": 1, "lapses": 0, "last_grade": 2}, {"level": 3, "ease": 2.5, "interval_days": 1, "reps": 0, "lapses": 1, "last_grade": 1}]');

INSERT INTO bench_runs (id, attempt_id, slug, lang, ran_at, code_hash, sizes, results, user_time_band, user_mem_band, slope, r2, reference_id, ratio, verdict, confidence, env) VALUES
  (1, 1, 'two-sum', 'python', '2026-10-01T09:12:00+00:00', 'a1b2c3', '[100, 1000]', '{"user": {"1000": {"median_ns": 120000, "status": "ok"}}}', 'O(n)', 'O(n)', 1.02, 0.99, 'hash-map', 1.1, 'optimal', 'high', '{"cpu": "test", "cores": 8}'),
  (2, 2, 'valid-parentheses', 'typescript', '2026-10-02T09:32:00+00:00', 'd4e5f6', '[100, 1000]', '{"user": {"1000": {"median_ns": 120000, "status": "ok"}}}', 'O(n)', 'O(n)', 1.1, 0.97, 'stack', 1.4, 'near-optimal', 'medium', '{"cpu": "test", "cores": 8}'),
  (3, 3, 'lru-cache', 'java', '2026-10-03T09:22:00+00:00', '0a1b2c', '[100, 1000]', '{"user": {"1000": {"median_ns": 120000, "status": "ok"}}}', 'O(n^2)', 'O(n)', 2.0, 0.95, 'linked-hash-map', 9.5, 'suboptimal', 'low', '{"cpu": "test", "cores": 8}'),
  (4, NULL, 'two-sum', 'python', '2026-10-09T09:00:00+00:00', NULL, '[100, 1000]', '{"user": {"1000": {"median_ns": 120000, "status": "ok"}}}', NULL, NULL, NULL, NULL, NULL, NULL, 'unknown', 'low', '{"cpu": "test", "cores": 8}');

INSERT INTO submissions (id, attempt_id, submitted_at, code_hash, graded_up_to, every_level, levels, total, passed, failed, errored, timed_out, duration_ms) VALUES
  (1, 8, '2026-10-08T10:00:00+00:00', '11aa22', 1, 1, '[{"level": 1, "total": 10, "passed": 10, "visible_total": 6, "visible_passed": 6, "hidden_total": 4, "hidden_passed": 4}]', 10, 10, 0, 0, 0, 3100),
  (2, 8, '2026-10-08T11:45:00+00:00', '33bb44', 3, 1, '[{"level": 1, "total": 10, "passed": 10, "visible_total": 6, "visible_passed": 6, "hidden_total": 4, "hidden_passed": 4}]', 30, 30, 0, 0, 0, 5100);

INSERT INTO level_unlocks (attempt_id, level, unlocked_at) VALUES
  (8, 1, '2026-10-08T09:00:00+00:00'),
  (8, 2, '2026-10-08T10:00:00+00:00'),
  (8, 3, '2026-10-08T11:00:00+00:00');
