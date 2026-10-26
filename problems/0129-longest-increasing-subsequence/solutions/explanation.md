# Longest Increasing Subsequence: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(n^2) | O(n) | you reason top-down: "what can follow this element?" |
| tabulation | intermediate | O(n^2) | O(n) | the classic DP answer, easy to extend to recover the subsequence |
| patience-sorting | optimal | O(n log n) | O(n) | default answer when n is large or the interviewer asks for better than quadratic |

The brute force tries every subsequence: each element is kept or dropped, 2^n choices, each checked in O(n). It is the first step of the progression and is not a separate reference here. Its recursive form, "take or skip `nums[i]` given the last value taken", repeats the same `(i, last)` questions many times. Fixing one endpoint of the subsequence, its first or its last element, reduces the subproblems to `n`.

## Approach: memoization (Top-down longest run starting at each index)

### Intuition

Let `longestFrom(s)` be the length of the longest increasing subsequence whose first element is `nums[s]`. Whatever comes second must be some later `nums[f] > nums[s]`, and from there the best continuation is `longestFrom(f)`. The question for `s` depends only on `s`, so it can be cached.

### Algorithm

1. Define `longestFrom(s)`: start with `best = 1` (the element alone).
2. For every `f > s` with `nums[f] > nums[s]`, set `best = max(best, 1 + longestFrom(f))`.
3. Cache and return `best`.
4. Return the maximum of `longestFrom(s)` over all `s`.

### Correctness

By induction from the right end. A subsequence starting at `s` is either `nums[s]` alone or `nums[s]` followed by an increasing subsequence starting at some `f > s` with `nums[f] > nums[s]`; every such option is examined, each with its optimal continuation by the induction hypothesis. The longest subsequence overall starts somewhere, so the maximum over all starts is the answer.

### Complexity

- Time: O(n^2) — each of the `n` starts is computed once and scans the elements after it.
- Space: O(n) — the memo, plus a recursion up to `n` frames deep on an increasing array.

### Trade-offs

A natural derivation that interviewers accept as a stepping stone, with the same cost as the table. It recurses as deep as the answer is long, which is fine for `n <= 2500` but adds call overhead; the bottom-up version is the more common way to write it.

### Pitfalls and edge cases

- Strictly increasing: the test is `>` not `>=`. With `>=`, the array `[6, 6, 6]` would report 3.
- The answer is the maximum over every start, not `longestFrom(0)`: in `[9, 1, 2]` the best run does not begin at index 0.
- A memo value of 0 can mean "not computed" because every real length is at least 1.

### Language notes

- Python: `functools.cache` on the nested function; the generator expression in `max` drives the top-level calls.
- TypeScript and Java: an explicit loop over the starts collects the maximum.
- Kotlin: `nums.indices.maxOf { longestFrom(it) }` expresses the final maximum in one call.

## Approach: tabulation (Quadratic table of runs ending at each index)

### Intuition

Flip the viewpoint to the last element. Let `ending[i]` be the length of the longest increasing subsequence that ends at index `i`. The element before `nums[i]`, if any, is some `nums[j] < nums[i]` with `j < i`, and the best subsequence ending there has length `ending[j]`. Every `ending[j]` with `j < i` is known when processing left to right.

### Algorithm

1. Set every `ending[i] = 1`.
2. For each `i` from 1 to `n - 1` and each `j < i`: if `nums[j] < nums[i]`, set `ending[i] = max(ending[i], ending[j] + 1)`.
3. Return the maximum of `ending`.

### Correctness

Invariant: when index `i` is processed, `ending[j]` is final for all `j < i`. An increasing subsequence ending at `i` is either `nums[i]` alone (length 1) or a subsequence ending at some `j < i` with `nums[j] < nums[i]`, extended by `nums[i]`; the loop takes the best of all these. The overall longest subsequence ends at some index, so the maximum entry is the answer.

### Complexity

- Time: O(n^2) — about n^2 / 2 pairs `(j, i)`, each O(1).
- Space: O(n) — one entry per index.

### Trade-offs

The textbook DP, short and reliable, so it is the oracle. Storing for each `i` the `j` that gave its best value lets you rebuild an actual subsequence. Quadratic time is fine for a few thousand elements but too slow for 10^5.

### Pitfalls and edge cases

- Initialize every entry to 1, not 0: a single element is an increasing subsequence.
- Return the maximum entry, not the last one.

### Language notes

- Python: two nested `range` loops; on large inputs the patience version is much faster in Python because `bisect` runs in C.
- TypeScript: `Math.max(...ending)` spreads at most 2500 values here; for very large arrays prefer a loop, since spreading has an argument-count limit.
- Java: the maximum is tracked during the loop.
- Kotlin: `IntArray(n) { 1 }` initializes the table and `ending.max()` returns the maximum.

## Approach: patience-sorting (Smallest tails with binary search)

### Intuition

Among all increasing subsequences of a given length `L`, the most useful one is the one with the smallest last value, because it is the easiest to extend. Keep `tails[L - 1]` = the smallest last value of any increasing subsequence of length `L` seen so far. These values are strictly increasing in `L`. A new value `v` either extends the longest subsequence (when it is larger than every tail) or improves the tail of the first length whose tail is at least `v`.

### Algorithm

1. Start with an empty `tails`.
2. For each value `v`, find the first position `p` with `tails[p] >= v` by binary search.
3. If `p` equals the length of `tails`, append `v`; otherwise set `tails[p] = v`.
4. Return the length of `tails`.

### Correctness

Invariant after each element: for every `L <= len(tails)`, `tails[L - 1]` is the smallest last value of an increasing subsequence of length `L` in the prefix, and `tails` is strictly increasing. When `v` arrives, it can end a subsequence of length `p + 1` exactly when some subsequence of length `p` ends below `v`, that is when `tails[p - 1] < v`; the binary search finds the largest such `p`. Replacing `tails[p]` (which is `>= v`) by `v` keeps it the smallest possible, and leaves the order strict because `tails[p - 1] < v <= tails[p]`. The length of `tails` is therefore the longest length achieved. Note that `tails` itself is generally not a subsequence: for `[5, 6, 7, 1, 2]` it ends as `[1, 2, 7]`.

### Complexity

- Time: O(n log n) — one binary search over at most `n` tails per element.
- Space: O(n) — the tails array.

### Trade-offs

The asymptotically best answer and short once understood. The invariant is less obvious than the quadratic DP, so explain it before writing the code. Recovering an actual subsequence needs extra arrays (the index stored at each tail position and a predecessor link per element).

### Pitfalls and edge cases

- Use a lower bound (first tail `>= v`), not an upper bound (first tail `> v`). The upper bound computes the longest non-decreasing subsequence, which counts duplicates.
- Do not report `tails` as the subsequence; it only has the right length.

### Language notes

- Python: `bisect.bisect_left` is the lower bound on a sorted list.
- TypeScript: no built-in binary search, so the reference writes the lower-bound loop; `tails[low] = value` appends when `low` equals the length.
- Java: `Arrays.binarySearch(tails, 0, size, value)` returns `-(insertion point) - 1` when the value is absent; the tails are distinct, so a found value is replaced by itself.
- Kotlin: `IntArray.binarySearch(element, fromIndex, toIndex)` has the same contract as Java's.
