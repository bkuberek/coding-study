-- Up Migration
-- One row per upload loaded. An upload is its bucket, key and sequencer: the same event delivered
-- twice names the same three, and a new upload of the same key carries a new sequencer. The row
-- is claimed at the start of the load's transaction, so a second delivery of the same event waits
-- on the unique key and then finds it taken.
CREATE TABLE imports (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  bucket text NOT NULL,
  key text NOT NULL,
  sequencer text NOT NULL,
  status text NOT NULL DEFAULT 'loading' CHECK (status IN ('loading', 'loaded', 'rejected')),
  rows_total integer NOT NULL DEFAULT 0,
  rows_loaded integer NOT NULL DEFAULT 0,
  rows_rejected integer NOT NULL DEFAULT 0,
  UNIQUE (bucket, key, sequencer)
);

CREATE INDEX imports_by_key ON imports (key);
