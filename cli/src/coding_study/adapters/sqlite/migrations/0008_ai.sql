-- The AI preview (docs/specs/ai.md#records-and-progress): AI review records, the log of requests
-- to a provider's model, and consents to send. IF NOT EXISTS keeps the script safe to run again,
-- whatever number it ends up with. `purpose`, `tier` and `error` carry no CHECK, so a later
-- milestone adds values without rebuilding a table.

CREATE TABLE IF NOT EXISTS ai_reviews (              -- AI review records: public, format 1 (docs/specs/ai.md#the-record)
  id              INTEGER PRIMARY KEY,
  attempt_id      INTEGER NOT NULL REFERENCES attempts (id),
  format          INTEGER NOT NULL,    -- 1
  created_at      TEXT NOT NULL,
  provider        TEXT NOT NULL,       -- anthropic, google, openai, openrouter
  model           TEXT NOT NULL,       -- the provider's model id
  prompt_version  TEXT NOT NULL,       -- the instructions' version: review-1
  rubric_sha256   TEXT NOT NULL,       -- the rubric version: sha256 of rubric.md as reviewed against
  notes_sha256    TEXT NOT NULL,       -- sha256 of the notes reviewed
  items           TEXT NOT NULL,       -- JSON [{number, area, criterion, verdict, evidence, gaps}] in rubric order
  summary         TEXT NOT NULL,
  quotes_dropped  INTEGER NOT NULL DEFAULT 0,
  input_tokens    INTEGER,
  output_tokens   INTEGER,
  cost_usd        REAL,                -- as the provider reported it; NULL when it reported none
  dismissed_at    TEXT
);
CREATE INDEX IF NOT EXISTS ai_reviews_by_attempt ON ai_reviews (attempt_id, created_at);

CREATE TABLE IF NOT EXISTS ai_calls (                -- every request to an AI provider's model: usage and the daily cap
  id              INTEGER PRIMARY KEY,
  purpose         TEXT NOT NULL,       -- review, check; later milestones add theirs
  provider        TEXT NOT NULL,
  model           TEXT NOT NULL,
  tier            TEXT,                -- fast or strong; NULL under fixed routing
  attempt_id      INTEGER REFERENCES attempts (id),  -- the attempt an AI review reviewed
  local_day       TEXT NOT NULL,       -- YYYY-MM-DD on this machine's clock: the day the cap counts it in
  started_at      TEXT NOT NULL,
  ended_at        TEXT NOT NULL,
  outcome         TEXT NOT NULL CHECK (outcome IN ('ok', 'failed', 'interrupted')),
  error           TEXT,                -- auth, rate_limit, model, refused, length, network, timeout, provider, invalid_reply
  input_tokens    INTEGER,             -- as the provider reported them; NULL without a usage report
  output_tokens   INTEGER,
  counted_tokens  INTEGER NOT NULL,    -- what the cap counts: the reported tokens, else the request's estimate
  cost_usd        REAL                 -- as the provider reported it; NULL when it reported none
);
CREATE INDEX IF NOT EXISTS ai_calls_by_day ON ai_calls (local_day);

CREATE TABLE IF NOT EXISTS ai_consents (             -- consent to send, per provider, model and purpose
  provider    TEXT NOT NULL,
  model       TEXT NOT NULL,
  purpose     TEXT NOT NULL,
  granted_at  TEXT NOT NULL,
  PRIMARY KEY (provider, model, purpose)
);
