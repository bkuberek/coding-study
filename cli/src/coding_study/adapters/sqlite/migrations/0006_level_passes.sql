-- Level passes (docs/decisions/0024-level-passes.md): a pass through level N of M counts.
-- Rows written before this migration keep NULL: a `passed` attempt then passed every level, and
-- a test run counts every level when it passed every case.

ALTER TABLE attempts ADD COLUMN levels_passed INTEGER;   -- levels 1 to N passed, at cstudy done
ALTER TABLE attempts ADD COLUMN levels_total INTEGER;    -- the problem's levels, at cstudy done
ALTER TABLE test_runs ADD COLUMN levels_passed INTEGER;  -- progressive: levels 1 to N passed
