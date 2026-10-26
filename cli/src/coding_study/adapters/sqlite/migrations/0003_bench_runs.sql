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
