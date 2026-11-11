# ADR 0024: A pass through level N of M is a pass

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-11-11 |
| Spec | [progress-and-scheduling](../specs/progress-and-scheduling.md#level-passes) ([mastery per level](../specs/progress-and-scheduling.md#mastery-per-level)), [cli](../specs/cli.md#cstudy-done) ([`cstudy status`](../specs/cli.md#cstudy-status), [`cstudy history`](../specs/cli.md#cstudy-history), [`cstudy list`](../specs/cli.md#cstudy-list), [`cstudy set`](../specs/cli.md#cstudy-set)), [web-ui](../specs/web-ui.md#problem-view) |
| Amends | [ADR 0014](0014-project-problems.md): a project's levels cap the grade, and fail the attempt, only in a mock. [ADR 0023](0023-problem-sets.md): a set's entry may name a target level |
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

Migration `0006_level_passes.sql` adds four nullable columns:

| Column | Holds |
|--------|-------|
| `attempts.levels_passed` | N, set by `cstudy done` for a problem with levels |
| `attempts.levels_total` | M, set by `cstudy done`, so a later change to the problem's levels does not rewrite the past |
| `test_runs.levels_passed` | For a progressive problem: the highest level such that the run ran and passed every case of levels 1 to it. A stress case counts once per variant. 0 when level 1 did not pass, or when the code did not build |
| `schedule.levels` | For a problem with levels: the review of each level after the first, as JSON ([mastery per level](#mastery-per-level)) |

A test run had only its totals, which cannot say which levels passed when one case of level 3 failed. So the run stores its N when it is recorded.

SQLite has no `ADD COLUMN IF NOT EXISTS`, so the migration runner runs a script that adds a column the table already has statement by statement, skipping that column. A merge that renumbers 0006 can then run it again on a database that has it.

Rows written before the migration keep NULL, and stay valid:

- A `passed` attempt with NULL passed every level, since that was the only way to pass.
- A `failed` one recorded no levels.
- A test run with NULL counts every level when it passed every case, and none otherwise, which was the rule before.

### The best level and the next goal

Neither is stored. Both are read from the attempts of one problem in one language.

| Term | Meaning |
|------|---------|
| Best | The most levels a `passed` attempt in that language passed, up to the problem's levels now |
| Last time | N of the latest finished attempt that passed level 1, in any mode |
| Goal | While last time is below M: `last time: through level 2 of 4; try level 3` |

A review, or any new attempt, still starts at level 1, because a review means solving the problem again. The goal says how far to aim.

### Mastery per level

Added on 2026-11-11, after the owner's decision: mastery is "the ability to recall at your level".

The recall test stays the one of the [problem status](../specs/progress-and-scheduling.md#problem-status): a review interval of at least `mastered_interval_days` (21 by default) after a grade of `ok` or `easy`. A problem with levels applies it to each level, and is **mastered through level L of M** for the largest L such that each of levels 1 to L passes it. It reads `mastered` with no qualifier only when L = M. Problems without levels are unchanged.

| Rule | Detail |
|------|--------|
| Level 1 | Its review is the problem's own `schedule` row, which every graded attempt updates, as before. So the problem is `mastered`, in any status filter, the weakness score, `cstudy next` and `cstudy stats`, exactly when it was before, through level 1 at least |
| Levels 2 to M | Each has a review of its own, kept on the `schedule` row as `levels` (JSON). A graded attempt that passed through level N gives each level up to N its grade, a level reached before but not passed now `again`, and leaves a level never reached without a review. A level's first review starts fresh, at the first interval |
| Rows before this | A `schedule` row with no `levels`, written before levels had reviews, was earned by full passes only, so every level counts as reached with the problem's own review, and mastery reads as before |

So climbing does not inherit mastery: a level's interval grows only from the reviews that reached it.

Worked example, with the default intervals and every review graded `ok` on a problem of 4 levels:

| Review | Passed through | Level 1 (the problem) | Level 2 | Level 3 | Reads |
|--------|----------------|-----------------------|---------|---------|-------|
| 1 | 2 | 3 days | 3 | - | passed through level 2 of 4 |
| 2 | 2 | 7 | 7 | - | passed through level 2 of 4 |
| 3 | 2 | 18 | 18 | - | passed through level 2 of 4 |
| 4 | 2 | 45 | 45 | - | mastered through level 2 of 4 |
| 5 | 3 | 113 | 113 | 3 | mastered through level 2 of 4, passed through level 3 |
| 6 | 3 | 180 (the cap) | 180 | 7 | the same |
| 7 | 3 | 180 | 180 | 18 | the same |
| 8 | 3 | 180 | 180 | 45 | mastered through level 3 of 4 |

Had review 6 passed through level 2 only, level 3 would have taken `again` (1 day) and started over, while levels 1 and 2 kept growing.

| Alternative | Why not |
|-------------|---------|
| Replay the reviews of each level from the attempts each time | Needs the attempts, the problem's levels and the current intervals wherever a status shows, and a changed interval setting would rewrite past mastery, unlike the schedule, whose due dates never move |
| The minimum level over the problem's current review streak | Passing level 3 after mastering level 2 would never master level 3 without a lapse first |
| A table of level reviews | The `schedule` row already belongs to the problem and is what resets, exports and imports carry; one JSON column follows it at no extra cost |

### Target levels in sets

Added on 2026-11-11 with mastery per level. An entry of a [set](0023-problem-sets.md) may name the level a progressive or project problem is done at, beside the plain slug, whose target is every level:

```yaml
sets:
  ledger-loop:
    problems:
      - two-sum
      - {slug: tamper-evident-ledger, level: 2}
```

| Rule | Detail |
|------|--------|
| Done | An entry is done once a `passed` attempt, in any language, passed through its target level: every level without one, and at most the problem's last. An entry without levels, or an item, is done once it passed, as before |
| Counts | A set's `passed of total`, the Sets view's bar and the pick of `cstudy next --set` (the first entry not done) follow it |
| Writing | `cstudy set add <name> <slug>... --level N` adds each slug done at level N, or changes the target of one already there. A level the problem lacks, or a problem without levels, is refused. The writer keeps a targeted entry on one line, as a flow mapping, so a change still touches only the lines it must; an entry written by hand as a block mapping keeps its lines when it moves |
| Showing | `cstudy set show` writes `target  through level 2` under the row, its `--json` gives each row `level`, and `cstudy set list --json` each set `levels` by slug; the Sets view says `through level 2 (target)` beside the row's status |
| The same `level` as a path | A learning path's problem step carries the same optional `level`, "done once this level passes". A set's entry names its problem with `slug`, since a set holds only slugs, where a path's step needs `problem` to tell it from a `guide` step |

### Where it shows

| Where | What |
|-------|------|
| `cstudy done` | `passed · through level 2 of 4` when N < M |
| `cstudy status` | `goal`, `passed` (the best) and `mastered` lines, a `next` line that says `cstudy done` now passes through level N, and `levels.passed`, `best`, `last_time`, `try_level` and `mastered` in `--json` |
| `cstudy history` | The header reads `mastered through level 2 of 4`, the status column `passed through level 2 of 4`, a `passed` line gives the best per language, and `--json` adds `levels_passed` and `levels_total` to each attempt and `levels.mastered` |
| `cstudy list` | The status column reads `mastered 2/4`, and `--json` gives each entry `levels`: `last`, `passed` (the best in any language) and `mastered` |
| The statement | The goal, under the title, while an attempt is in progress |
| The page | The Done dialog's line, the History of the Problem view, and the goal in its Practise panel; the Attempt view shows the goal through the statement; the status badge of the Problems, Problem and Sets views reads `mastered through level 2 of 4` |

The done API keeps `levels_finished`, a project's levels finished, for compatibility, and adds `levels_passed` and `levels_total`, N and M for any problem with levels, which the page writes the done line from.

## Consequences

- A problem passed through level 2 of 4 is `passed`, not `attempted`, and becomes `mastered` through the levels its reviews keep reaching, as [mastery per level](#mastery-per-level) says.
- `cstudy next`, the weakness score and the sets' `passed of total` follow, since they read the attempts' statuses and grades.
- A run that passed every case of levels 1 and 2 counts, whatever selected it: a full run, `--level 2`, or `--case` naming each of those cases. Only a run that passes every unlocked level opens the next one, as before.
- Data written by an older `cstudy` reads the same as before. An export from this version imports only into a `cstudy` at schema 6 or later.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Keep the level cap, and only pass the attempt | A clean pass of the first levels would still come back the next day as `again`, which is the problem the owner raised |
| Read N from `level_unlocked` | It records the highest level a run ever opened, not what the latest code passes; a later run that breaks level 1 would still count |
| Store the best per (problem, language) in a table | It can be read from the attempts at any time, and a table would need keeping in step with imports, resets and old rows |
| Start a review at the level after last time | A review means solving again from the start. The goal tells you where to aim instead |
| Apply level passes to mock attempts too | A mock simulates an interview, where an unfinished problem is not a pass |
