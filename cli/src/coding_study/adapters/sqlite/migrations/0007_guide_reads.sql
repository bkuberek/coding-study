-- Concept guides (docs/specs/guides.md#reading-progress): a guide is read once
-- `cstudy learn <guide> --done` marks it. IF NOT EXISTS keeps the script safe to run again,
-- whatever number it ends up with.

CREATE TABLE IF NOT EXISTS guide_reads (
  slug     TEXT PRIMARY KEY,
  read_at  TEXT NOT NULL               -- the first time it was marked
);
