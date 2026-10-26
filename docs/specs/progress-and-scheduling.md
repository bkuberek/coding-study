# Spec: Progress and Scheduling

Progress lives in SQLite (`progress.db`, gitignored). The database stores only facts about the user; problem metadata (patterns, difficulty, track) is always read from the content files, so editing content never requires a migration.

## Schema

Applied by numbered migrations in `cli/src/coding_study/adapters/sqlite/migrations/` (`0001_init.sql`, ...); `meta.schema_version` records the last applied number. Tables arrive by phase: `meta`, `attempts`, `test_runs` in Phase 0; `schedule` in Phase 1; `bench_runs` in Phase 2 (`0003_bench_runs.sql`, written with `IF NOT EXISTS` so it is safe to renumber or run again). Timestamps are ISO 8601 UTC strings; `due_on` is a local calendar date (`YYYY-MM-DD`) from the injected `Clock`.

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

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

CREATE TABLE bench_runs (
  id             INTEGER PRIMARY KEY,
  attempt_id     INTEGER REFERENCES attempts (id), -- NULL for --refs-only
  slug           TEXT NOT NULL,
  lang           TEXT NOT NULL,
  ran_at         TEXT NOT NULL,
  code_hash      TEXT,
  sizes          TEXT NOT NULL,        -- JSON array
  results        TEXT NOT NULL,        -- JSON {target_id: {size: {median_ns, spread, cpu_ns, calls, mem_bytes, mem_metric, status, exceeded_ns}}}; the user is "user"
  user_time_band TEXT,
  user_mem_band  TEXT,
  slope          REAL,
  r2             REAL,
  reference_id   TEXT,                 -- optimal approach compared against
  ratio          REAL,                 -- user / reference at the largest common size
  verdict        TEXT NOT NULL CHECK (verdict IN ('optimal', 'near-optimal', 'suboptimal', 'unknown')),
  confidence     TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
  env            TEXT NOT NULL         -- JSON: cpu, power, load, cores, runner, runtime, references_hash
);
CREATE INDEX bench_runs_by_problem ON bench_runs (slug, lang, ran_at);
```

## Attempt lifecycle

| Event | Effect |
|-------|--------|
| `cstudy start` | Insert `in_progress`; `mode` is `review` if a `schedule` row exists, `mock` under `cstudy mock`, else `new`. Same slug and language already `in_progress`: resume it. With `--fresh`: mark the old one `abandoned` (no grade, no schedule change). Progressive: a new attempt stores `level_unlocked = 1` |
| `cstudy test` | Insert a `test_runs` row; set `first_pass_at` on the first all-pass run (progressive: of every level); progressive: raise `level_unlocked` by one when a run passes every unlocked level |
| `cstudy mock` | One `cstudy start --fresh` per pick, mode `mock`, all with `time_limit_s` set to the shared timer; while it runs and a mock attempt is `in_progress`, `cstudy hint` and `cstudy solution` refuse ([cli](cli.md#cstudy-mock)) |
| `cstudy hint` | `hints_used += 1` |
| `cstudy solution` before a full pass | `solution_revealed = 1` |
| `cstudy done` | Set `ended_at`, `status` (`passed` or `failed`), `rating`, `grade`; update `schedule` |

Solve time is `ended_at - started_at` (wall clock; there is no pause).

## Grade

Grades: 0 `again`, 1 `hard`, 2 `ok`, 3 `easy`. Computed in order:

1. `--gave-up`, or `solution_revealed` before `first_pass_at`: grade 0.
2. Otherwise from the rating: `easy` 3, `ok` 2, `hard` 1.
3. Caps (minimum wins): any hint used caps at 2; finished over `--timer` caps at 1; with `schedule.penalize_suboptimal`, the attempt's latest bench verdict `suboptimal` at confidence `medium` or `high` caps at 1.

Non-autograded items use step 2 only: no `--gave-up`, and revealing the reference, hints and the timer never lower the grade. Their attempts have `lang` NULL and `stub_path` set to the notes file.

## Scheduling algorithm

A simplified SM-2, per problem and language-agnostic (the algorithm is what must be retained; the language is recorded on the attempt). Inputs: previous row (or `reps = 0`, `interval = 0`, `ease = 2.5`, `lapses = 0`) and the grade. The interval uses the old `ease`; `ease` is updated afterwards. `round` is round-half-up.

| Grade | New interval (days) | Ease | Reps | Lapses |
|-------|---------------------|------|------|--------|
| 0 again | 1 | `max(1.3, ease - 0.20)` | 0 | +1 |
| 1 hard | `reps == 0`: 2; else `max(interval + 1, round(interval * 1.2))` | `max(1.3, ease - 0.15)` | +1 | |
| 2 ok | `reps == 0`: 3; `reps == 1`: 7; else `round(interval * ease)` | unchanged | +1 | |
| 3 easy | `reps == 0`: 5; `reps == 1`: 12; else `round(interval * ease * 1.3)` | `min(3.0, ease + 0.10)` | +1 | |

Then `interval = min(interval, schedule.max_interval_days)` (default 180) and `due_on = local_date(ended_at) + interval`.

Worked sequence (ok, ok, ok, hard, again, ok):

| # | Grade | Interval | Ease after | Reps after |
|---|-------|----------|------------|------------|
| 1 | ok | 3 | 2.50 | 1 |
| 2 | ok | 7 | 2.50 | 2 |
| 3 | ok | 18 | 2.50 | 3 |
| 4 | hard | 22 | 2.35 | 4 |
| 5 | again | 1 | 2.15 | 0 |
| 6 | ok | 3 | 2.15 | 1 |

## Problem status

| Status | Definition |
|--------|------------|
| `new` | No attempt with status `passed` or `failed` |
| `attempted` | Finished attempts exist, none `passed` |
| `passed` | At least one `passed` attempt; not mastered |
| `mastered` | `schedule.interval_days >= 21` and `last_grade >= 2` |
| `due` | `schedule.due_on <= today` (shown instead of `passed` or `mastered`) |

## Weakness score

Computed per group key: the primary pattern for `dsa` problems, the track id for other tracks. Over problems in the current scope:

| Term | Definition |
|------|------------|
| `fail_rate` | Share of the last 10 finished attempts in the group with grade at most 1; 0.5 when there are none |
| `mastery` | Mastered problems / problems in the group |
| `staleness` | `min(1, days since the group's last finished attempt / 30)`; 1 when never attempted |
| `weakness` | `0.5 * fail_rate + 0.3 * (1 - mastery) + 0.2 * staleness`, in [0, 1] |

The current scope is the `cstudy next` scope below, including problems with an `in_progress` attempt (they are only excluded as candidates). Scores are exact fractions, so equally weak groups tie exactly and fall through to the tie-breaks.

An untouched group scores 0.75. After one passed attempt (grade 2 or 3) it drops to 0.30, so `cstudy next` rotates through untouched groups before deepening one; after one failed attempt it rises to 0.80, so a group the user just failed outranks untouched ones.

## `cstudy next` selection

Deterministic: the same database, content, date and flags give the same answer.

**Scope.** Tracks from `--track` or config `next.tracks`; content `status: ready` only; `--pattern` matches any listed pattern; `--difficulty`; with `--lang`, problems whose `languages` include it (non-autograded items have no language and stay in scope; `--pattern` excludes them, since they have no patterns). Problems and items with an `in_progress` attempt are excluded. Items take part like problems: their group is their track, and ties on `id` use the slug.

**Step 1: reviews** (skipped with `--new`). Candidates: `schedule.due_on <= today`. Priority `(today - due_on + 1) / interval_days + weakness(group)`. Highest wins; ties by smaller `interval_days`, then `id`.

**Step 2: new problems** (skipped with `--review`).

1. Groups with at least one `new` problem in scope; choose the highest weakness; ties by taxonomy order ([content](content.md#pattern-taxonomy)), then track order.
2. Difficulty gate within the group: `easy` always eligible; `medium` once a group `easy` is passed or the group has no `easy`; `hard` once a group `medium` is passed or the group has no `medium`. If the gate excludes everything, use the lowest available difficulty.
3. Sort eligible problems by difficulty, `order`, `id`; take the first.

**Step 3.** Nothing found: print `nothing due and no new problems in scope` and exit 0.

The printed reason names the step, the overdue days or the weakness value.

## Statistics

What `cstudy stats` reports ([cli](cli.md#cstudy-stats)). The content is every `ready` problem and item of every track, the content `cstudy next` can pick, so a group's weakness under `--by pattern` equals the score `cstudy next` uses for it with the default filters. Attempts on other slugs (draft or removed content) count only in the totals. Dates are local calendar dates from the injected `Clock`; "finished" means status `passed` or `failed`.

| Value | Definition |
|-------|------------|
| Group | `--by pattern`: the [weakness group](#weakness-score) (primary pattern of a `dsa` problem, else the track); `track`; `difficulty`; `lang`: every language in a problem's `languages` (items have none and are left out), and an attempt belongs to the group of its language |
| problems | Content in the group |
| attempted | Content with a finished attempt in the group |
| passed | Content with a `passed` attempt in the group |
| mastered | Mastered content ([status](#problem-status)); by language, only where it has a `passed` attempt in that language |
| pass rate | `passed` share of the group's last 10 finished attempts (by `ended_at`, then id), rounded half up to a whole percent; `-` without attempts |
| solve time | Median of `ended_at - started_at` over the group's `passed` attempts, shown like `cstudy done` (`18m 40s`); `-` without passes |
| weakness | [Weakness score](#weakness-score) over the group's content and finished attempts, today; 2 decimals |
| finished | Every finished attempt, also on slugs outside the content |
| last 7 days | Finished attempts that ended today or in the 6 days before (the practice cadence KPI) |
| streak | Consecutive days with a finished attempt, ending today, or yesterday while today has none yet; 0 otherwise |
| due today, overdue | Content whose `schedule.due_on` is today, or before today |
| bench | Per (problem, language), the verdict of the latest bench run of the user's code (not `--refs-only`), by `ran_at` then id; counted per verdict |

`--since DATE` leaves out attempts that ended, and bench runs that ran, before `DATE`: it narrows attempted, passed, pass rate, solve time, finished and the bench line. Problems, mastered, weakness, last 7 days, streak, due today and overdue always describe today.
