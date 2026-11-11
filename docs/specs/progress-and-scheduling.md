# Spec: Progress and Scheduling

Progress lives in SQLite (`progress.db`, gitignored). The database stores only facts about the user; problem metadata (patterns, difficulty, track) is always read from the content files, so editing content never requires a migration.

## Schema

Applied by numbered migrations in `cli/src/coding_study/adapters/sqlite/migrations/` (`0001_init.sql`, ...); `meta.schema_version` records the last applied number. Tables arrive by phase: `meta`, `attempts`, `test_runs` in Phase 0; `schedule` in Phase 1; `bench_runs` in Phase 2 (`0003_bench_runs.sql`, written with `IF NOT EXISTS` so it is safe to renumber or run again); `0004_go_and_rust.sql` rebuilds `attempts` so that `lang` accepts `go` and `rust` (SQLite cannot change a `CHECK` constraint in place); `0005_project_problems.sql` adds `submissions` and `level_unlocks` for [project attempts](#project-attempts), with `IF NOT EXISTS`; `0006_level_passes.sql` adds `attempts.levels_passed`, `attempts.levels_total`, `test_runs.levels_passed` and `schedule.levels` for [level passes](#level-passes) and [mastery per level](#mastery-per-level), NULL in the rows written before it. A script that adds a column the table already has, as one run again under a new number does, runs statement by statement, skipping that column. Processes that open a new database at the same time migrate it one after another, under a lock on its folder. A database migrates on the first command that opens it; `cstudy doctor` shows its schema (`progress database`: WARN when older, FAIL when newer than this `cstudy` knows) without migrating, and `cstudy doctor --fix` migrates it now, under the same lock ([workspace checks](installation-and-workspaces.md#cstudy-doctor-in-a-workspace)). Timestamps are ISO 8601 UTC strings; `due_on` is a local calendar date (`YYYY-MM-DD`) from the injected `Clock`. [`cstudy reset`](cli.md#cstudy-reset) empties every table but `meta` in one transaction and records the highest attempt id it deleted there as `attempt_id_floor`; a new attempt's id is one above the higher of that and the table's own, since `.archive/<slug>/<attempt_id>-<lang>/`, which a reset keeps by default, names old attempts by id.

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
  notes             TEXT,
  levels_passed     INTEGER,           -- problems with levels: levels 1 to N passed, at cstudy done
  levels_total      INTEGER            -- the problem's levels, at cstudy done
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
  duration_ms INTEGER NOT NULL,
  levels_passed INTEGER                -- progressive: levels 1 to N ran and passed
);

CREATE TABLE schedule (
  slug          TEXT PRIMARY KEY,
  ease          REAL NOT NULL,
  interval_days INTEGER NOT NULL,
  reps          INTEGER NOT NULL,
  lapses        INTEGER NOT NULL,
  due_on        TEXT NOT NULL,
  last_grade    INTEGER NOT NULL,
  updated_at    TEXT NOT NULL,
  levels        TEXT                 -- problems with levels: JSON [{level, ease, interval_days, reps, lapses, last_grade}] from level 2
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

CREATE TABLE submissions (             -- project problems: one row per cstudy submit
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
CREATE INDEX submissions_by_attempt ON submissions (attempt_id, submitted_at);

CREATE TABLE level_unlocks (           -- project problems: when each level opened
  attempt_id   INTEGER NOT NULL REFERENCES attempts (id),
  level        INTEGER NOT NULL,
  unlocked_at  TEXT NOT NULL,
  PRIMARY KEY (attempt_id, level)
);
```

## Attempt lifecycle

| Event | Effect |
|-------|--------|
| `cstudy start` | Insert `in_progress`; `mode` is `review` if a `schedule` row exists, `mock` under `cstudy mock`, else `new`. Same slug and language already `in_progress`: resume it. With `--fresh`: mark the old one `abandoned` (no grade, no schedule change). Progressive and project: a new attempt stores `level_unlocked = 1`; project: also a `level_unlocks` row for level 1, and `stub_path` is the folder `projects/<slug>` |
| `cstudy test` | Insert a `test_runs` row; set `first_pass_at` on the first all-pass run (progressive: of every level); progressive: store the row's `levels_passed` ([level passes](#level-passes)), and raise `level_unlocked` by one when a run passes every unlocked level. Project: the row holds the native suite's tally and changes nothing else |
| `cstudy submit` | Project only: insert a `submissions` row; when it graded every unlocked level and passed every case, raise `level_unlocked` by one and insert its `level_unlocks` row, or, at the last level, set `first_pass_at` |
| `cstudy mock` | One `cstudy start --fresh` per pick, mode `mock`, all with `time_limit_s` set to the shared timer; while it runs and a mock attempt is `in_progress`, `cstudy hint` and `cstudy solution` refuse ([cli](cli.md#cstudy-mock)) |
| `cstudy hint` | `hints_used += 1` |
| `cstudy solution` before a full pass | `solution_revealed = 1` |
| `cstudy done` | Set `ended_at`, `status` (`passed` or `failed`), `rating`, `grade`, and for a problem with levels `levels_passed` and `levels_total`; update `schedule` |
| `cstudy abort` | Set `ended_at` and `status` `abandoned`: no grade, no rating and no change to `schedule`; refused while a run or a job is active. The files stay, and the next `cstudy start` begins a new attempt |

Solve time is `ended_at - started_at` (wall clock; there is no pause).

## Grade

Grades: 0 `again`, 1 `hard`, 2 `ok`, 3 `easy`. Computed in order:

1. `--gave-up`, or `solution_revealed` before `first_pass_at`: grade 0.
2. Otherwise from the rating: `easy` 3, `ok` 2, `hard` 1.
3. Caps (minimum wins): any hint used caps at 2; finished over `--timer` caps at 1; with `schedule.penalize_suboptimal`, the attempt's latest bench verdict `suboptimal` at confidence `medium` or `high` caps at 1.

A problem with levels passes through level N of M with its own rating rule, and a mock adds a level cap ([level passes](#level-passes)). The solution step counts `first_pass_at`, which still means every level, so a solution revealed before then grades 0.

Non-autograded items use step 2 only: no `--gave-up`, and revealing the reference, hints and the timer never lower the grade. Their attempts have `lang` NULL and `stub_path` set to the notes file.

## Project attempts

A [project problem](problem-format.md#project-problems)'s attempt is graded from its submissions, not its test runs ([ADR 0014](../decisions/0014-project-problems.md)).

| Item | Rule |
|------|------|
| Counted submission | The latest submission with `every_level = 1`. Submissions with a lower `--level` never count |
| Levels finished | The largest L such that the counted submission passed every case of levels 1 to L; 0 without a counted submission. A [stress verdict](problem-format.md#stress-cases-in-projects) counts as a hidden case of its level, in `hidden_total` and `hidden_passed` of the level's tally |
| `cstudy done` | Levels finished is the N of a [level pass](#level-passes): a rating is required when it is at least 1, `--gave-up` otherwise |
| Level cap | A mock only: applied with the caps above, the minimum winning: every level finished, no cap; all but the last, `hard` (1); fewer, `again` (0) |
| Time box | Soft, as for every problem: finishing over `--timer` caps at `hard`; submissions are never refused |
| Status | `passed` when level 1 is finished; in a mock, only when every level is, `failed` otherwise, also when a rating was given |
| `test_runs` | Native suite runs: `total` counts every reported test but skipped ones, `errored` holds errors and crashes, `tle` is 0; `code_hash` hashes the folder (every file but `.venv`, `node_modules` and caches, by relative path and bytes in path order) |
| `level_unlocks` | One row per opened level, so `cstudy status` shows when each level opened |

Two levels of four finished, rated `ok`, under the time box and without hints: `passed` through level 2 of 4, grade 2. In a mock: two of four, grade 0; three of four, grade 1; four of four, grade 2.

## Level passes

A progressive or project problem passes through level N of M: N is the largest level such that every case of levels 1 to N passed, M the problem's last level ([ADR 0024](../decisions/0024-level-passes.md)).

| Item | Rule |
|------|------|
| What counts | Progressive: the latest test run, its `levels_passed`; a run recorded before that column counts M when it passed every case (as many as a run of every level stores), 0 otherwise. Project: the [counted submission](#project-attempts)'s levels finished. N can be below `level_unlocked` |
| A run's `levels_passed` | The largest L such that the run ran and passed every case of levels 1 to L, a stress case once per variant; 0 when a case of level 1 did not pass or the code did not build. A run of `--level 2`, or a `--case` run naming every case of levels 1 and 2, counts for them; only a run that passes every unlocked level opens the next |
| `cstudy done` | N at least 1: a rating, and the attempt is `passed`, graded by the [grade](#grade) steps with no level cap. N = 0: `--gave-up` only, grade 0, `failed`. It stores N and M as `levels_passed` and `levels_total` |
| Mock | A `mock` attempt keeps the rules from before level passes. Progressive: a rating only when N = M. Project: a rating from N = 1, with the level cap of [project attempts](#project-attempts). Both: `passed` only when N = M. N and M are stored all the same |
| Without levels | Function, design and concurrent problems, and items, store NULL in both columns and keep their rules |
| Older rows | An attempt with `levels_passed` NULL that is `passed` passed every level (of the problem's levels now, as it stored no M); one that is `failed` recorded no levels |

| Term | Over the finished attempts of one problem in one language |
|------|-------------------------------------------------------------|
| Best | The most levels a `passed` attempt passed, at most the problem's levels now; none before a pass |
| Last time | N of the latest attempt, by start, that passed at least level 1, in any mode and status |
| Goal | While last time is below M: `last time: through level 2 of 4; try level 3`. A new attempt, a review included, still starts at level 1 |

## Mastery per level

A problem with levels applies the recall test of `mastered` ([problem status](#problem-status)) to each level: an interval of at least `mastered_interval_days` after a grade of 2 or 3 ([ADR 0024](../decisions/0024-level-passes.md#mastery-per-level)).

| Item | Rule |
|------|------|
| Level 1 | The problem's `schedule` row, as for every problem |
| Levels 2 to M | `schedule.levels`, one review per level reached. At `cstudy done`, with the attempt's `levels_passed` N and grade G, each level L from 2 to M: L ≤ N takes G (from a fresh review the first time); L > N takes 0 when it has a review, and stays without one otherwise. The [scheduling algorithm](#scheduling-algorithm) and its settings apply to each |
| Mastered through | The largest L such that each of levels 1 to L passes the recall test; 0 when level 1 does not. A level without a review is not mastered |
| Older rows | A row with `levels` NULL was written before levels had reviews, by full passes, so every level follows the row's own review: mastered through M when the problem is mastered. The next `cstudy done` gives every level that review to start from |
| Without levels | `levels` stays NULL and `mastered` reads as it always has |

Levels mastered do not change the problem's status value: it is `mastered` exactly when level 1 is, so the `--status` filter, the weakness score, `cstudy next` and `cstudy stats` read it as before. Only the words change.

## Scheduling algorithm

A simplified SM-2, per problem and language-agnostic (the algorithm is what must be retained; the language is recorded on the attempt). Inputs: previous row (or `reps = 0`, `interval = 0`, `ease = 2.5`, `lapses = 0`) and the grade. The interval uses the old `ease`; `ease` is updated afterwards. `round` is round-half-up.

| Grade | New interval (days) | Ease | Reps | Lapses |
|-------|---------------------|------|------|--------|
| 0 again | 1 | `max(1.3, ease - 0.20)` | 0 | +1 |
| 1 hard | `reps == 0`: 2; else `max(interval + 1, round(interval * 1.2))` | `max(1.3, ease - 0.15)` | +1 | |
| 2 ok | `reps == 0`: 3; `reps == 1`: 7; else `round(interval * ease)` | unchanged | +1 | |
| 3 easy | `reps == 0`: 5; `reps == 1`: 12; else `round(interval * ease * 1.3)` | `min(3.0, ease + 0.10)` | +1 | |

Then `interval = min(interval, schedule.max_interval_days)` (default 180) and `due_on = local_date(ended_at) + interval`.

The fixed intervals in this table and the [mastered](#problem-status) threshold are the user's to change, under [`[schedule]`](cli.md#configuration). The defaults are the values above, so a config without these keys schedules exactly as this table reads.

| Table entry | Key | Default |
|-------------|-----|---------|
| again | `again_interval_days` | 1 |
| hard, `reps == 0` | `hard_first_interval_days` | 2 |
| ok, `reps == 0` | `ok_first_interval_days` | 3 |
| ok, `reps == 1` | `ok_second_interval_days` | 7 |
| easy, `reps == 0` | `easy_first_interval_days` | 5 |
| easy, `reps == 1` | `easy_second_interval_days` | 12 |
| the cap | `max_interval_days` | 180 |
| [mastered](#problem-status) | `mastered_interval_days` | 21 |

| Rule | Detail |
|------|--------|
| Values | Positive integers; anything else stops the command with an error that names the key. No order is enforced between the intervals: a second interval shorter than the first still schedules, and the cap still applies to each. A `mastered_interval_days` you set above `max_interval_days` is refused (`schedule.mastered_interval_days: 200 is above schedule.max_interval_days (180), so no problem could ever be mastered`), since no interval passes the cap. Left unset, a low `max_interval_days` stays valid and no problem is mastered, as before these keys existed |
| When a change applies | A new interval applies to reviews scheduled after the change: the next `cstudy done` of a problem. A `due_on` already stored never moves. `mastered_interval_days` is read each time a status is shown, so it applies at once, to every problem |
| Not configurable | The ease and its multipliers: the initial `2.5`, the bounds `1.3` and `3.0`, the steps `0.20`, `0.15` and `0.10`, the `1.2` of `hard` and the `1.3` of `easy`. These are what make it SM-2, and a wrong value would pull every later interval with it |

Worked sequence with the defaults (ok, ok, ok, hard, again, ok):

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
| `in_progress` | An attempt with status `in_progress` is open, in any language. It comes ahead of every status below, `due` included, and lasts while the attempt is open: `cstudy done`, `cstudy abort` or `cstudy start --fresh` ends it, and an `abandoned` attempt never counts |
| `new` | No attempt with status `passed` or `failed`, and none open |
| `attempted` | Finished attempts exist, none `passed` |
| `passed` | At least one `passed` attempt; not mastered |
| `mastered` | `schedule.interval_days >=` the config's `schedule.mastered_interval_days` (default 21) and `last_grade >= 2`. A problem with levels is mastered through the levels each of which passes this test ([mastery per level](#mastery-per-level)), level 1 by this row, and reads `mastered through level 2 of 4` (`mastered 2/4` in the table of `cstudy list`) until it is mastered through its last |
| `due` | `schedule.due_on <= today` (shown instead of `passed` or `mastered`) |

Only the display of `cstudy list` and its web page, and the `--status` filter, read the status. People read `in_progress` as `in progress` (the table, the badge and the Status filter of the page, the first line of `cstudy history`); the value `in_progress` stays in `--json`, the API and the route's query. `cstudy next` and the weakness score read the attempts themselves: a problem with an attempt in progress is still left out of the picks and still counts in its group, and a problem with no finished attempt is still `new` there. A review in progress shows `in_progress` rather than `due`, so `cstudy list --status due` lists the due problems that have no attempt open.

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

**Scope.** Tracks from `--track`, else every track when `--domain`, `--role` or `--scope` is given (the config's `next.tracks`, `dsa` by default, would leave out what a label names), else config `next.tracks`; content `status: ready` only; `--pattern` matches any listed pattern; `--domain` and `--role` match any listed [domain or job role](content.md#labels), `--scope` the scope, for problems and items alike, so a problem of your own without labels is out of scope under any of them; `--difficulty`; with `--lang`, problems whose `languages` include it (non-autograded items have no language and stay in scope; `--pattern` excludes them, since they have no patterns). When the language a problem starts in (`--lang`, else `default_lang`; a project problem's own) is Java or Kotlin, problems whose [JDK range](problem-format.md#jdk-range) does not contain the [selected JDK](cli.md#the-selected-jdk) are out of scope too, and so is every Java and Kotlin problem when no JDK is selected. Problems and items with an `in_progress` attempt are excluded. Items take part like problems: their group is their track, and ties on `id` use the slug.

**Step 0: resume** (skipped with `--new` or `--review`). The attempt in progress that was used most recently, among those whose problem is in scope: the later of its start and its last test run, a tie going to the later attempt. When one is open, nothing below runs, and the other attempts in progress in scope are listed after it, most recently used first, to pick another. The weakness score and steps 1 and 2 do not change: they still leave out the problems with an attempt in progress, and they decide the pick when none is open (after a `cstudy done` or a [`cstudy abort`](cli.md#cstudy-abort)).

**Step 1: reviews** (skipped with `--new`). Candidates: `schedule.due_on <= today`. Priority `(today - due_on + 1) / interval_days + weakness(group)`. Highest wins; ties by smaller `interval_days`, then `id`.

**Step 2: new problems** (skipped with `--review`).

1. Groups with at least one `new` problem in scope; choose the highest weakness; ties by taxonomy order ([content](content.md#pattern-taxonomy)), then track order.
2. Difficulty gate within the group: `easy` always eligible; `medium` once a group `easy` is passed or the group has no `easy`; `hard` once a group `medium` is passed or the group has no `medium`. If the gate excludes everything, use the lowest available difficulty.
3. Sort eligible problems by difficulty, `order`, `id`; take the first.

**Step 3.** Nothing found: print `nothing due and no new problems in scope` and exit 0.

The printed reason names the step, the overdue days or the weakness value.

### With `--set`

[`cstudy next --set`](cli.md#cstudy-next) picks from a [set](cli.md#cstudy-set), in the set's order, since a hand-picked list is a plan ([ADR 0023](../decisions/0023-problem-sets.md)).

| Step | Pick |
|------|------|
| 0: resume (skipped with `--new` or `--review`) | As above, among the attempts in progress on the set's entries; the others in progress there are listed after it |
| 1: the set's order (skipped with `--review`) | The first entry in the set's order that is in scope, has no attempt in progress and has no passed attempt. An entry with only failed attempts isn't passed, so it stays the pick until it passes or moves |
| 2: reviews (skipped with `--new`) | The due entries of the set, ranked as in step 1 above |
| 3 | The set is finished, or empty, or the scope holds nothing to pick: see [the messages](cli.md#cstudy-next) |

| Rule | Detail |
|------|--------|
| Scope | As above, but for two things: the tracks are every track unless `--track` is given, and an entry of the set counts as `ready` whatever its `status`, as a problem of your own you marked `draft` and chose stays chosen. A slug the catalog no longer has is left out |
| Weakness | Unchanged: the score of a group is over the same problems as without `--set`, so a set changes no score and the priority of a review reads the same |
| Passed | The attempts decide, not the status: an entry with a passed attempt counts as passed while it is `due` or has a review open |

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
