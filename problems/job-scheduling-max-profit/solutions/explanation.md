# Job Scheduling for Maximum Profit: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| quadratic-dp | brute | O(n^2) | O(n) | first working version; a few thousand jobs at most |
| memoization | intermediate | O(n log n) | O(n) | you reason as "take this job or skip it", in start-time order |
| binary-search-dp | optimal | O(n log n) | O(n) | default answer |

This is weighted interval scheduling. Two greedy rules that work for related problems fail here: "most profitable job first" (jobs [1, 4) for 10, [3, 6) for 11 and [5, 8) for 10: greedy takes 11, the best is 20), and "earliest end first", which is optimal only when all profits are equal ([1, 3) for 1 and [2, 10) for 100). The dynamic program is House Robber with a different notion of "neighbor": taking a job rules out every job that overlaps it, and after sorting, the compatible earlier jobs form a prefix.

Trying every subset of jobs, 2^n of them, and keeping the best non-overlapping one is the brute force behind the progression; it is not a separate reference here.

## Approach: quadratic-dp (Sort by end and scan back for the last compatible job)

### Intuition

Sort the jobs by end time. Let `best[i]` be the most profit from the first `i` jobs in that order. Job `i` (the `i`-th by end time) is either skipped, giving `best[i - 1]`, or taken; then the other jobs taken must end by its start, and because ends are sorted, those jobs are exactly a prefix of the order.

State: `best[i]` over prefixes of the end-sorted jobs. Recurrence: `best[i] = max(best[i - 1], profit + best[p])`, where `p` is the number of jobs that end no later than job `i` starts.

### Algorithm

1. Sort the jobs by end time; `best[0] = 0`.
2. For each job `i` in order, walk back from `i - 1` while the job there ends after job `i` starts; the stopping point gives `p`.
3. Set `best[i + 1] = max(best[i], profit[i] + best[p])`.
4. Return `best[n]`.

### Correctness

By induction on `i`. An optimal schedule of the first `i + 1` jobs either omits job `i`, and is then a schedule of the first `i`, or contains it; then every other job in it ends at or before job `i` starts. Every job ending that early comes before job `i` in end order, and every job before position `p` ends that early, so the rest of the schedule is a schedule of exactly the first `p` jobs. Both cases are covered by the recurrence with optimal subproblems.

### Complexity

- Time: O(n^2) — sorting is O(n log n), but each backward walk can pass every earlier job when the jobs overlap heavily.
- Space: O(n) — the sorted jobs and the `best` table.

### Trade-offs

The recurrence is the important insight; the linear scan is the obvious first way to find `p`, and it is simple enough to be the oracle. On inputs where most jobs overlap, it is quadratic.

### Pitfalls and edge cases

- Compatibility is "ends at or before the start" (`end <= start`); a job ending at time 6 and one starting at 6 can both be taken.
- Sorting by start time breaks this recurrence: the compatible jobs are then not a prefix.
- Keep each job's start, end and profit together when sorting; sorting the three arrays separately scrambles them.

### Language notes

- Python: sorting tuples `(end, start, profit)` keeps each job together and orders by end.
- TypeScript: sort an index array with `(a, b) => endTime[a] - endTime[b]`; the difference stays well within the safe integer range.
- Java: `Integer[]` indexes sorted with `Comparator.comparingInt`; a primitive `int[]` cannot take a comparator.
- Kotlin: `startTime.indices.sortedBy { endTime[it] }` gives the order as a `List<Int>`.
- Go: a small `job` struct and `sort.Slice` order the jobs by end time. `sort.Slice` is not stable, which changes nothing here: two jobs with the same end time can never both be chosen, so the order between them does not affect any answer.
- Rust: a `Vec<(i32, i32, i32)>` of `(end, start, profit)` tuples; `sort()` orders tuples field by field, the same as Python's tuple sort.

## Approach: memoization (Top-down take-or-skip over jobs sorted by start)

### Intuition

Sort by start time and decide jobs from the earliest start onwards. Let `bestFrom(i)` be the most profit from the jobs at positions `i` and later. Skipping job `i` leaves `bestFrom(i + 1)`; taking it leaves the jobs that start once it has ended, which form a suffix beginning at the first start at or after its end. That position is a binary search away.

### Algorithm

1. Sort the jobs by start time.
2. `bestFrom(n) = 0`.
3. For position `i`: find `j`, the first position after `i` whose start is at least job `i`'s end (lower bound); return `max(bestFrom(i + 1), profit[i] + bestFrom(j))`, caching the result.
4. Return `bestFrom(0)`.

### Correctness

By induction from the last position. A schedule drawn from positions `i..n-1` either skips job `i`, and is then a schedule from `i + 1`, or takes it; every other job in it starts at or after job `i` (sorted order) and must not overlap it, so it starts at or after job `i`'s end, which is precisely the suffix from `j`. Jobs in that suffix never overlap job `i`, so any schedule of the suffix combines with it.

### Complexity

- Time: O(n log n) — sorting, plus `n` cached states each with one binary search.
- Space: O(n) — the cache and a recursion up to `n` frames deep.

### Trade-offs

A natural "decide each job" formulation with the optimal complexity. Its recursion depth equals the number of jobs, which is why the constraints stop at 2000 jobs; for the original 5 * 10^4, prefer the bottom-up version.

### Pitfalls and edge cases

- Use a lower bound (first start `>=` the end). A library binary search that returns any matching index may land in the middle of several equal starts and skip compatible jobs.
- Searching from `i + 1` is enough: job `i` itself starts before it ends.

### Language notes

- Python: `bisect_left(starts, end, lo=index + 1)` is the lower bound.
- TypeScript and Kotlin: a hand-written lower-bound loop.
- Java: the jobs become `{start, end, profit}` rows sorted by `row[0]`; fields hold the rows and the memo so the helper methods stay small.
- Go: `sort.Search(n, f)` returns the first index in `[0, n)` where `f` holds, so searching `jobs[index+1:]` means searching a count of `len(jobs)-index-1` and adding `index+1` back. The recursion is a closure declared with `var` first.
- Rust: `starts[index + 1..].partition_point(|&start| start < end)` is the lower bound over the tail of the sorted starts; add `index + 1` for the position in the whole slice. The recursion is a private function that takes the jobs, the starts and the memo.

## Approach: binary-search-dp (Bottom-up over end times with binary search)

### Intuition

Keep the quadratic DP but replace the backward walk. The end times of the sorted jobs are non-decreasing, so "how many of the first `i` jobs end at or before this start" is an upper-bound binary search over the sorted end times.

### Algorithm

1. Sort the jobs by end time and keep the sorted end times.
2. For each job `i`: `p` = the number of positions among the first `i` with end `<=` its start (upper bound).
3. `best[i + 1] = max(best[i], profit[i] + best[p])`.
4. Return `best[n]`.

### Correctness

The recurrence is the same as in the quadratic version; only the computation of `p` changes. Because the end times are sorted, the positions with end `<=` start form a prefix, and the upper bound returns its length exactly.

### Complexity

- Time: O(n log n) — the sort, plus one binary search over at most `n` end times per job.
- Space: O(n) — the sorted jobs, the end times and the `best` table.

### Trade-offs

The standard answer: iterative, no deep recursion, and optimal. An equivalent alternative sweeps the jobs by start time with a min-heap of (end, profit so far); it has the same complexity and is handy when jobs arrive as a stream.

### Pitfalls and edge cases

- Upper bound, not lower bound: jobs that end exactly at the start time are compatible and must be counted.
- Searching only the first `i` positions is enough: later jobs end no earlier than job `i`, which ends after it starts, so none of them can be compatible.
- Profits sum to at most 2000 * 10^4 here, so 32-bit integers suffice; with the original limits they still do (5 * 10^4 * 10^4 = 5 * 10^8).

### Language notes

- Python: `bisect_right(ends, start, hi=i)` counts the compatible prefix.
- TypeScript: a hand-written upper-bound loop over the sorted end times.
- Java: rows `{end, start, profit}` sorted by `row[0]`; `>>>` avoids overflow in the midpoint by habit.
- Kotlin: `ushr 1` is the unsigned shift for the midpoint; `withIndex()` walks the sorted order with positions.
- Go: `sort.Search(i, func(k int) bool { return jobs[k].end > current.start })` is the upper bound over the first `i` jobs, so no midpoint arithmetic is written by hand.
- Rust: `ends[..i].partition_point(|&end| end <= start)` is the same upper bound over the sorted prefix; `ends` is a separate `Vec<i32>` so the predicate reads plain integers.
