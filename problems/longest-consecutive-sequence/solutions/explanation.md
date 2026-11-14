# Longest Consecutive Run: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| linear-search | brute | O(n^2) | O(1) | n is tiny, memory is extremely tight, or as a correctness oracle |
| sorting | intermediate | O(n log n) | O(n) | simplest correct answer; the input is already sorted |
| hash-set | optimal | O(n) | O(n) | default answer |

All three count each run once, from its smallest value. The brute force and the hash set find those smallest values with the same test, "is `x - 1` absent?"; they differ only in how fast a membership check is.

## Approach: linear-search (Run starts with linear membership checks)

### Intuition

Every run has a smallest value `x`, recognizable because `x - 1` is absent. From there, the run extends to `x + 1`, `x + 2`, ... for as long as those values are present. Answering "is this value present?" with a linear scan needs no extra memory.

### Algorithm

1. Set `longest = 0`.
2. For each position `i` with value `x`:
   1. If `x - 1` occurs in `nums`, skip: `x` is not the start of a run.
   2. If `x` also occurs at an earlier position, skip: that copy already counted this run.
   3. Otherwise count `length = 1` and increase it while `x + length` occurs in `nums`.
   4. Update `longest` with `length`.
3. Return `longest`.

Each "occurs" test is a scan over the whole array.

### Correctness

Take any run of present values `s, s + 1, ..., e` that cannot be extended, so `s - 1` and `e + 1` are absent. Its start `s` passes step 2.1 and, at its first occurrence, step 2.2, and step 2.3 counts exactly `e - s + 1`: it stops at `e + 1`, the first absent value. Any value counted from passes 2.1, so it is the start of a maximal run, and the count is that run's length. Every maximal run is therefore counted, nothing longer is ever counted, and `longest` is the maximum.

### Complexity

- Time: O(n^2) — the start test and the first-occurrence test cost one scan per position, and the run extensions together cost one scan per distinct value, because each distinct value is extended over at most once. That is at most about 3n scans of n elements. The test generator adds nothing that changes this: the start test alone scans about n/2 elements per position.
- Space: O(1) — a few counters.

### Trade-offs

It needs no memory at all, which makes it a dependable oracle, but at n = 10,000 it already scans about 10^8 elements. It isolates the algorithmic idea of the optimal solution (count only from run starts) from the data structure (constant-time membership), which is a useful way to present the solution in an interview.

### Pitfalls and edge cases

- Without the run-start test, every value of a run counts its own tail: a sorted run of length n costs n^2/2 extensions, each a linear scan, O(n^3) in total.
- Without the first-occurrence test, repeated copies of a start re-count the same run: `n/2` copies of `1` followed by `2..n/2 + 1` is again O(n^3).
- The empty array has no run and must return 0.

### Language notes

- Python: `value - 1 in nums` and `nums.index(value)` scan the list in C, about ten times faster than a Python loop, with the same O(n) cost per check.
- TypeScript: `includes` and `indexOf` are linear scans. They differ on `NaN`, which cannot occur here.
- Java: the reference writes the scan as a small `indexOf` helper over `int[]`; `Arrays.asList(nums)` would not work, because it wraps the whole `int[]` as a single element.
- Kotlin: `value in nums` calls `IntArray.contains`, a linear scan without boxing; `withIndex()` provides the position.
- Go: `slices.Contains` is a linear scan over the `[]int`; `nums[:i]` is a subslice header, so checking for an earlier copy of the start allocates nothing. `max` is a builtin since Go 1.21.
- Rust: `nums.contains(&(value - 1))` borrows the probe value and scans the `Vec<i32>`; `nums[..i].contains(&value)` checks only the earlier positions. `value + length` stays inside `i32` because the values are at most 10^9 in magnitude.

## Approach: sorting (Sort a copy and count runs)

### Intuition

In sorted order, the values of a run sit next to each other, interrupted only by repeats. One pass over the sorted values counts how long each stretch of "+1 steps" lasts.

### Algorithm

1. If `nums` is empty, return 0.
2. Sort a copy of `nums`.
3. Set `longest = current = 1`.
4. For each sorted value `v` after the first, with predecessor `p`:
   1. If `v == p`, skip it (a repeat neither extends nor breaks the run).
   2. If `v == p + 1`, increment `current`; otherwise reset `current = 1`.
   3. Update `longest` with `current`.
5. Return `longest`.

### Correctness

After removing repeats, the sorted values are strictly increasing, and a maximal run is exactly a maximal stretch in which each value is its predecessor plus one. Skipping a repeat leaves `current` unchanged, which is the same as deleting it. Invariant: after processing a value, `current` is the length of the run of distinct values ending at that value. A `+1` step extends that run; any larger step ends it and starts a new run of length 1. `longest` tracks the maximum over all prefixes.

### Complexity

- Time: O(n log n) — the sort dominates; the pass is O(n).
- Space: O(n) — the sorted copy.

### Trade-offs

Easy to get right and memory-friendly on the JVM (a primitive array instead of a hash set of boxed integers), so it can beat the hash set in wall-clock time for moderate n. It is a log factor slower asymptotically, and interviewers usually ask for the O(n) solution after it.

### Pitfalls and edge cases

- Repeats must be skipped, not treated as a break: `[1, 2, 2, 3]` has a run of length 3.
- Initialize `longest` to 1 for a non-empty array, so that a single element counts.
- Sorting in place would reorder the caller's array; the references sort a copy.

### Language notes

- TypeScript: `Int32Array.from(nums).sort()` copies and sorts numerically; the default `Array.prototype.sort` compares as strings.
- Java: `nums.clone()` and `Arrays.sort`. Kotlin: `nums.sortedArray()`.
- Python: `sorted(nums)`, then `zip(ordered, ordered[1:])` walks adjacent pairs.
- Go: `slices.Clone` and `slices.Sort` sort a copy, and the loop compares each element with its predecessor by index.
- Rust: `nums` is owned, so `sort_unstable` sorts it in place with no copy, and `windows(2)` yields each predecessor and value pair.

## Approach: hash-set (Hash set with run starts)

### Intuition

Put every value into a hash set, so that "is `x + 1` present?" costs O(1). Then do exactly what the brute force does, but iterate over the set, so each distinct value is considered once: start counting only at values whose predecessor is absent.

### Algorithm

1. Build `present`, the set of values in `nums`.
2. Set `longest = 0`.
3. For each value `x` in `present`:
   1. If `x - 1` is in `present`, skip it.
   2. Otherwise let `end = x + 1` and increment `end` while it is in `present`.
   3. Update `longest` with `end - x`.
4. Return `longest`.

### Correctness

Identical to the brute force: each maximal run `s..e` is counted exactly once, from `s`, and the count stops at `e + 1`. Iterating over the set removes repeats, so no run is counted twice, and only run starts are ever extended.

### Complexity

- Time: O(n) — building the set is O(n); the loop does one start test per distinct value, and the extensions together visit each distinct value at most once, because every value belongs to exactly one maximal run, which is extended from its start only.
- Space: O(n) — the set.

### Trade-offs

Linear time, which is what the follow-up asks for. Hash sets of boxed integers are memory-hungry on the JVM and have a large constant factor, so for moderate n the sorting solution can be faster in practice. Both the start test and iterating over the set (not over `nums`) are needed for the O(n) bound.

### Pitfalls and edge cases

- Iterating over `nums` instead of the set re-counts a run once per copy of its start; with many copies that is quadratic again.
- Forgetting the start test makes the loop O(n^2) on a single long run, even with O(1) lookups.
- An empty array gives an empty set and `longest` stays 0.

### Language notes

- Python: `set(nums)` builds the set in C; `x - 1 in present` is an O(1) average lookup.
- TypeScript: `new Set(nums)` iterates in insertion order and `has` compares numbers by value.
- Java: `HashSet<Integer>` boxes each value; `contains(value - 1)` autoboxes the `int` argument. With values up to 10^9 in magnitude, `value - 1` and `end++` stay inside `int`.
- Kotlin: `nums.toHashSet()` converts the `IntArray` into a `HashSet<Int>`; `value - 1 in present` reads like the Python version.
- Go: a `map[int]bool` is the set: a missing key reads as `false`, so `present[end]` is the membership test with no comma-ok. `for value := range present` visits each distinct value once in random order, which does not matter because every run is counted from its start.
- Rust: `collect()` builds a `HashSet<i32>` from the owned `Vec`, which also removes duplicates; iterating `&present` visits each distinct value once in arbitrary order.
