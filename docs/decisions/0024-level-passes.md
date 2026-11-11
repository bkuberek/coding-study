# ADR 0024: A pass through level N of M is a pass

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-11-11 |
| Spec | [progress-and-scheduling](../specs/progress-and-scheduling.md#level-passes), [cli](../specs/cli.md#cstudy-done) ([`cstudy status`](../specs/cli.md#cstudy-status), [`cstudy history`](../specs/cli.md#cstudy-history)), [web-ui](../specs/web-ui.md#problem-view) |
| Amends | [ADR 0014](0014-project-problems.md): a project's levels cap the grade, and fail the attempt, only in a mock |
| Builds on | [ADR 0014](0014-project-problems.md), [ADR 0015](0015-local-web-ui.md) |

## Context

cstudy is for everyone, beginner to expert. Until now, for a problem with levels, only finishing every level counted as a pass:

- A progressive problem took a rating only after a test run that passed every case of every level. Otherwise the only way out was `--gave-up`, graded `again`.
- A project problem took a rating once level 1 passed, but the levels capped the grade (all but the last at `hard`, fewer at `again`), and the attempt was stored as failed unless every level passed.

So a beginner who cleanly passed levels 1 and 2 of 4 was graded as a failure and got the problem back the next day. The owner agreed on 2026-11-10 to change this, and settled the rules on 2026-11-11.

## Decision

### A pass through level N is a pass

N is the highest level whose cases, and the cases of every level below it, all passed. M is the problem's last level. When N is at least 1:

| Rule | Detail |
|------|--------|
| What counts | A progressive problem: the latest test run, as before. A project: the counted submission, as before (the latest one that graded every unlocked level). N can be below the unlocked level, when the newest level does not pass yet |
| `cstudy done` | Takes a rating. The attempt is `passed`, and records N and M |
| Grade | The rating's, with the caps that do not come from levels: a hint, a solution revealed before every level passed, the time box, and a confident `suboptimal` bench. No level cap |
| Review | Scheduled from that grade, as for any pass |
| `--gave-up` | Only when no level passed (N = 0), graded `again` |

A problem without levels (function, design, concurrent) is unchanged.

A solution revealed before every level passed still grades `again`: `first_pass_at` still means every level, because the reference solves every level, including those you have not reached.

### A mock keeps the rules of an interview

A `cstudy mock` attempt (mode `mock`) simulates an interview, so it keeps the rules from before:

| Kind | Rule in a mock |
|------|----------------|
| Progressive | A rating only once the latest run passed every case of every level; `--gave-up` otherwise |
| Project | A rating once level 1 passed; the levels cap the grade (all but the last at `hard`, fewer at `again`) |
| Both | `passed` only when every level passed, `failed` otherwise. The attempt still records N and M |

### What is stored

Migration `0006_level_passes.sql` adds three nullable columns:

| Column | Holds |
|--------|-------|
| `attempts.levels_passed` | N, set by `cstudy done` for a problem with levels |
| `attempts.levels_total` | M, set by `cstudy done`, so a later change to the problem's levels does not rewrite the past |
| `test_runs.levels_passed` | For a progressive problem: the highest level such that the run ran and passed every case of levels 1 to it. A stress case counts once per variant. 0 when level 1 did not pass, or when the code did not build |

A test run had only its totals, which cannot say which levels passed when one case of level 3 failed. So the run stores its N when it is recorded.

Rows written before the migration keep NULL, and stay valid:

- A `passed` attempt with NULL passed every level, since that was the only way to pass.
- A `failed` one recorded no levels.
- A test run with NULL counts every level when it passed every case, and none otherwise, which was the rule before.

### Mastery and the next goal

Neither is stored. Both are read from the attempts of one problem in one language.

| Term | Meaning |
|------|---------|
| Mastery (`best`) | The most levels a `passed` attempt passed, up to the problem's levels now |
| Last time | N of the latest finished attempt that passed level 1, in any mode |
| Goal | While last time is below M: `last time: through level 2 of 4; try level 3` |

A review, or any new attempt, still starts at level 1, because a review means solving the problem again. The goal says how far to aim.

### Where it shows

| Where | What |
|-------|------|
| `cstudy done` | `passed · through level 2 of 4` when N < M |
| `cstudy status` | `best` and `goal` lines, a `next` line that says `cstudy done` now passes through level N, and `levels.passed`, `best`, `last_time` and `try_level` in `--json` |
| `cstudy history` | The status column reads `passed through level 2 of 4`, a `best` line per language, and `levels_passed` and `levels_total` on each attempt in `--json` |
| The statement | The goal, under the title, while an attempt is in progress |
| The page | The Done dialog's line, the History of the Problem view, and the goal in its Practise panel; the Attempt view shows the goal through the statement |

`cstudy list` and the Problems view show no levels today, so they get no mastery column. The done API's `levels_finished`, a project's until now, holds N for a progressive problem too, so the page can write the done line without a new field in `schemas/web-api.schema.json`.

## Consequences

- A problem passed through level 2 of 4 is `passed`, not `attempted`, and can become `mastered` once its interval is long enough. Mastery per level shows how far that goes.
- `cstudy next`, the weakness score and the sets' `passed of total` follow, since they read the attempts' statuses and grades.
- A run that passed every case of levels 1 and 2 counts, whatever selected it: a full run, `--level 2`, or `--case` naming each of those cases. Only a run that passes every unlocked level opens the next one, as before.
- Data written by an older `cstudy` reads the same as before. An export from this version imports only into a `cstudy` at schema 6 or later.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Keep the level cap, and only pass the attempt | A clean pass of the first levels would still come back the next day as `again`, which is the problem the owner raised |
| Read N from `level_unlocked` | It records the highest level a run ever opened, not what the latest code passes; a later run that breaks level 1 would still count |
| Store mastery per (problem, language) in a table | It can be read from the attempts at any time, and a table would need keeping in step with imports, resets and old rows |
| Start a review at the level after last time | A review means solving again from the start. The goal tells you where to aim instead |
| Apply level passes to mock attempts too | A mock simulates an interview, where an unfinished problem is not a pass |
