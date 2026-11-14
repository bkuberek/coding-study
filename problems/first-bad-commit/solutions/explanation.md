# First Bad Commit: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| linear-scan | brute | O(n) | O(1) | the history is short, a test is cheap, or as a correctness oracle |
| binary-search | optimal | O(log n) with isolated skips, O(n) when long runs are skipped | O(1) | a test is slow and few commits are skipped |

Both rest on one fact about the tested commits: read in order, they are good commits followed by bad commits, with no good commit after a bad one. Only the commits marked `0` or `1` count; a `2` says nothing.

## Approach: linear-scan (Scan from the oldest commit to the first bad one)

### Intuition

Walk from the oldest commit towards the newest. Remember the position of the last good commit you passed. The first bad commit you meet ends the walk: nothing after it can change the answer, because the boundary is behind you.

### Algorithm

1. Set `lastGood = -1`, which stands for "no good commit yet".
2. For each position `i` from 0: if the status is good, set `lastGood = i`; if it is bad, return `[lastGood + 1, i]`.
3. The constraints guarantee that a bad commit exists, so the loop always returns.

### Correctness

When the loop meets the first bad commit at `i`, every commit before `i` is good or skipped, and `lastGood` is the position of the last good one. The commits strictly between `lastGood` and `i` are therefore all skipped. Each of them could be the first bad commit, since nothing contradicts it, and so can `i` itself. No commit up to `lastGood` can be it, because it is good or comes before a good commit, and no commit after `i` can be it, because `i` is already bad. That is exactly the range `[lastGood + 1, i]`.

### Complexity

- Time: O(n) — in the worst case the first bad commit is near the end and every status before it is read. The generator puts it in the middle third of the history, so at least n / 3 statuses are read at every seed.
- Space: O(1) — one integer.

### Trade-offs

It is the obvious solution and fine when reading a status is free, as it is in this exercise. In the real situation behind the problem, every status costs a test run that may take minutes, so reading n of them is what you want to avoid. The binary search turns "one test per commit" into "one test per halving".

### Pitfalls and edge cases

- Use `-1` for "no good commit", so that `lastGood + 1` is 0 when the history starts with skipped commits or with a bad commit.
- Do not stop at the first skipped commit, and do not treat a skipped commit as good or as bad: a skipped commit widens the answer.
- Skipped commits after the first bad commit do not matter.

### Language notes

- Python: `enumerate` gives the position and the status together; the function raises `ValueError` after the loop only to satisfy the type of the return.
- TypeScript, Java, Kotlin: the same loop over `number[]`, `int[]` or `IntArray`. Kotlin's `when` returns from inside the loop; Java and TypeScript use `if`/`else if`.
- Go: `switch` over the status with named constants; a `panic` after the loop satisfies the compiler, since a function with a result must end in a return or a panic.
- Rust: positions are `usize` from `enumerate`, converted to `i32` for the result, which fits the signature's `Vec<i32>`.

## Approach: binary-search (Two binary searches that step past skipped commits)

### Intuition

Think of the history as a line that changes once from good to bad. Looking at one commit in the middle tells you which half to discard: if it is bad, the first bad commit is that one or older; if it is good, everything older than it is good or skipped, so the first bad commit is newer. That is a binary search over a *monotone predicate*, "is the bug already present at this commit?", which is false for a prefix of the history and true after it. The only new difficulty is that the predicate cannot be evaluated at a skipped commit. The fix is small: when the middle commit is skipped, step to the nearest commit that was tested, inside the part of the history that is still open, and use that one instead.

Two searches are needed because the answer has two ends. The first finds the first bad commit. The second, restricted to the commits before it, finds the last good one; there, every commit that was tested is good, so it is the same search turned around: "is there a tested commit at or after this position?".

### Algorithm

1. Search for the first bad commit with `low = 0` and `high = n - 1`. While `low < high`: let `middle = (low + high) / 2` and move `probe` left from `middle` while the commit is skipped and `probe >= low`. If a tested commit was found and it is bad, set `high = probe`. Otherwise set `low = middle + 1`: either it is good, or every commit in `[low, middle]` is skipped, and in both cases the first bad commit is to the right of `middle`. When the loop ends, `low` is the first bad commit.
2. Search for the last good commit before it with `low = -1` (none) and `high = firstBad - 1`. While `low < high`: let `middle = (low + high + 1) / 2`, rounding up, and move `probe` right from `middle` while the commit is skipped and `probe <= high`. If `probe <= high`, that commit is good, so set `low = probe`. Otherwise every commit in `[middle, high]` is skipped, so set `high = middle - 1`. When the loop ends, `low` is the last good commit, or `-1`.
3. Return `[low + 1, firstBad]`.

### Correctness

Step 1 keeps the invariant "the first bad commit is in `[low, high]`". At the start it holds, because some commit is bad. When a tested bad commit is found at `probe <= middle`, the first bad commit is at `probe` or before, so `high = probe` keeps the invariant and strictly shrinks the range, since `probe <= middle < high`. When the probe is good, no commit up to `probe` is bad, because no good commit comes after a bad one; the commits between `probe` and `middle` are skipped, so none of them is known bad. In the other case, the whole range `[low, middle]` is skipped. In both cases the first bad commit is after `middle`, and `low = middle + 1` keeps the invariant and shrinks the range. The loop therefore ends with `low == high` equal to the first bad commit.

Step 2 works in the part of the history before the first bad commit, where a tested commit is always good. It keeps the invariant "the last good commit is in `[low, high]`, where `-1` means none". Rounding `middle` up guarantees that `middle > low`, so `low = probe` makes progress, and `high = middle - 1` does as well. If a tested commit exists at or after `middle` inside the range, the last good commit is at least that far right, and the nearest one found is a lower bound that is safe to adopt. If none exists, nothing in `[middle, high]` is good, so the last good commit is before `middle`. The loop ends with the last good commit.

The returned range is the same `[lastGood + 1, firstBad]` as the linear scan finds, by the correctness argument of that approach.

### Complexity

- Time: O(log n) with isolated skips, O(n) when long runs are skipped — each search halves its range about log2(n) times, and each halving steps over the skipped commits next to the middle. With scattered skips that is one or two extra steps, so the total stays logarithmic. With a long run of skipped commits, the step can cross the whole run, and no approach can avoid that: in `good, skipped x 98, bad` nothing but reading all 98 skipped statuses proves that none of them is good or bad. The generator skips one commit in ten, so the logarithmic case is what the ladder measures.
- Space: O(1) — a few integers.

### Trade-offs

With no skipped commits the idea is the textbook binary search for the first position where a monotone predicate turns true, and it needs about 17 looks for 10^5 commits (log2 of 10^5 is about 16.6) instead of up to 10^5. That is the same idea as searching a sorted array for the first value that is not below a target, with "bad" playing the part of "not below". Skipped commits cost extra looks and can make the answer a range; the range itself is information: it tells you which commits you would have to make testable to settle the question. The linear scan is simpler and has no worse cases, but its cost grows with the history, not with its logarithm.

### Pitfalls and edge cases

- Never treat a skipped commit as good or bad. Stepping past it is what keeps the invariant true.
- Stay inside `[low, high]` while stepping: a probe that leaves the range reads commits that are already discarded. In the first search, stepping left below `low` means the whole range `[low, middle]` is skipped.
- Round `middle` down in the first search and up in the second. A search that rounds the wrong way can loop forever when `high == low + 1`.
- The last good commit may not exist: the second search must be able to answer `-1`, so `low` starts at `-1`, not `0`.
- A history of one commit is a one-element range: the first loop does not run.

### Language notes

- All six languages use the same two loops. There is no library call to lean on: the standard binary searches (`bisect`, `Arrays.binarySearch`, `slices.BinarySearch`, `partition_point`) read a value or evaluate a predicate at every position they probe, and a skipped commit has neither.
- Python: two small helper functions keep each search readable.
- TypeScript: `>>> 1` and `>> 1` halve a non-negative integer without floating-point rounding; plain `/ 2` would need `Math.floor`.
- Java and Kotlin: `(low + high) >>> 1` is the usual overflow-safe midpoint; with at most 10^5 commits it never overflows, but the habit is worth keeping. Kotlin spells it `ushr`.
- Go: `low + (high-low)/2` is the midpoint; integer division truncates toward zero, which is the floor here because all operands are non-negative in the second search.
- Rust: positions are signed (`i32`) because the second search needs `-1`; the `as usize` casts happen only where a slice is indexed.
