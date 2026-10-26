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
