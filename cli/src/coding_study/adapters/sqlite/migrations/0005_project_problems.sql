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
