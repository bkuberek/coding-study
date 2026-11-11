import assert from "node:assert/strict";
import { test } from "node:test";

import { groupCells, importedText, reviewsAhead, statsCommand, summaryLines } from "../src/page/stats.ts";
import type { ListEntry, StatsDocument } from "../src/page/types.ts";

const STATS: StatsDocument = {
  today: "2026-10-24",
  by: "pattern",
  since: null,
  groups: [
    { group: "arrays-hashing", problems: 17, attempted: 5, passed: 4, mastered: 1, recent_attempts: 5, recent_passed: 4, pass_rate: 0.8, median_solve_s: 850, weakness: 0.42 },
    { group: "two-pointers", problems: 10, attempted: 0, passed: 0, mastered: 0, recent_attempts: 0, recent_passed: 0, pass_rate: null, median_solve_s: null, weakness: 0.75 },
  ],
  attempts: { finished: 6, last_7_days: 5, streak_days: 3 },
  reviews: { due_today: 1, overdue: 1 },
  bench: { optimal: 2, "near-optimal": 1, suboptimal: 1, unknown: 0 },
};

function entry(slug: string, status: string, due_on: string | null): ListEntry {
  return {
    id: "0001",
    slug,
    title: slug,
    track: "dsa",
    kind: "function",
    difficulty: "easy",
    patterns: [],
    domains: ["algorithms"],
    job_roles: ["general"],
    scope: "function",
    languages: [],
    content: "ready",
    source: "catalog",
    status,
    levels: null,
    due_on,
    in_progress: [],
    jdk: null,
    requires: null,
  };
}

test("a group's cells read as the cstudy stats row", () => {
  assert.deepEqual(groupCells(STATS.groups[0]!), ["arrays-hashing", "17", "5", "4", "1", "80%", "14m 10s", "0.42"]);
});

test("a group without attempts shows dashes", () => {
  assert.deepEqual(groupCells(STATS.groups[1]!).slice(5), ["-", "-", "0.75"]);
});

test("a pass rate rounds half up, as cstudy stats does", () => {
  assert.equal(groupCells({ ...STATS.groups[0]!, pass_rate: 0.125 })[5], "13%");
});

test("the summary reads as the three lines under the table", () => {
  assert.deepEqual(summaryLines(STATS), [
    ["attempts", "6 finished · 5 in the last 7 days · streak 3 days"],
    ["reviews", "1 due today · 1 overdue"],
    ["bench", "4 benched · 2 optimal · 1 near-optimal · 1 suboptimal · 0 unknown"],
  ]);
});

test("since names its date in the attempts line", () => {
  const since = { ...STATS, since: "2026-10-01", attempts: { finished: 1, last_7_days: 1, streak_days: 1 } };
  assert.deepEqual(summaryLines(since)[0], ["attempts", "1 finished since 2026-10-01 · 1 in the last 7 days · streak 1 day"]);
});

test("reviews ahead are the due ones, then the next 14 days by date", () => {
  const entries = [
    entry("later", "passed", "2026-11-20"),
    entry("soon", "passed", "2026-10-30"),
    entry("overdue", "due", "2026-10-20"),
    entry("sooner", "passed", "2026-10-26"),
    entry("never", "new", null),
  ];
  const ahead = reviewsAhead(entries, "2026-10-24");
  assert.deepEqual([ahead.due.map((item) => item.slug), ahead.upcoming.map((item) => item.slug)], [
    ["overdue"],
    ["sooner", "soon"],
  ]);
});

test("a due review with an attempt in progress stays among the reviews due", () => {
  const entries = [entry("under-review", "in_progress", "2026-10-20"), entry("open-later", "in_progress", "2026-10-30")];
  const ahead = reviewsAhead(entries, "2026-10-24");
  assert.deepEqual([ahead.due.map((item) => item.slug), ahead.upcoming.map((item) => item.slug)], [
    ["under-review"],
    ["open-later"],
  ]);
});

test("the imported rows read as cstudy import counts them", () => {
  assert.equal(importedText({ attempts: 6, test_runs: 4, schedule: 3 }), "attempts 6 · test_runs 4 · schedule 3");
});

test("the stats command names a grouping and a date only when set", () => {
  assert.deepEqual([statsCommand("pattern", ""), statsCommand("track", "2026-10-01")], [
    "cstudy stats",
    "cstudy stats --by track --since 2026-10-01",
  ]);
});
