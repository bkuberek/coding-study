# Majority Element: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | n is tiny, or as a correctness oracle |
| sorting | intermediate | O(n log n) | O(n) | the array is already sorted, or may be sorted in place |
| hash-map | intermediate | O(n) | O(n) | you also need the counts of other values |
| boyer-moore | optimal | O(n) | O(1) | default answer |

The guarantee that a majority value exists is what makes the last two shortcuts valid: sorting can read the middle position, and the vote can skip a verification pass.

## Approach: brute-force (Count every candidate)

### Intuition

The answer is one of the values in the array. Take each element in turn as a candidate, count how often it occurs, and return the first candidate whose count exceeds `n / 2`.

### Algorithm

1. Let `half = n / 2`, rounded down.
2. For each element `candidate` of `nums`:
   1. Count the positions holding `candidate` with a full scan.
   2. If the count exceeds `half`, return `candidate`.
3. Unreachable when a majority exists; the references raise an error.

### Correctness

Every value of the array is tried as a candidate, including the majority value, and the test "count exceeds `half`" is exactly the definition of the answer. No other value can pass it: two values each filling more than half of the positions would need more than `n` positions. So the first candidate that passes is the majority value.

### Complexity

- Time: O(n^2) — up to n candidates, each counted with a scan of n elements. The generator places between half and all of the minority elements before the first copy of the majority value, so the scan counts at least about n/5 candidates.
- Space: O(1) — one counter.

### Trade-offs

Easy to get right and memory-free, which suits an oracle. It repeats the same counting work for every copy of a value; at n = 30,000 that is 10^8 or more comparisons. The hash map removes the repetition, and the vote removes the memory.

### Pitfalls and edge cases

- The comparison is strict: in `[-4, 6, 6, -4, 6, 6]` the answer needs 4 copies, and a value with exactly `n / 2` copies is not a majority.
- Use integer division for `half`. In TypeScript, `nums.length / 2` is a fraction for odd lengths; `Math.floor` it, or compare `2 * count > n` instead.

### Language notes

- Python: `nums.count(candidate)` does the inner scan in C, roughly ten times faster than a Python loop, with the same O(n^2) growth.
- Kotlin: `nums.count { it == candidate }` is an inline function over the `IntArray`, so the predicate does not box.
- Go: there is no `count` helper on a slice, so the inner loop counts matches itself; the function ends in `panic`, since Go demands a return on every path and the input always has a majority.
- Rust: `iter().filter(..).count()` is the counting loop. The constraints guarantee a majority, so the final `panic!` is unreachable on valid input and only satisfies the return type.

## Approach: sorting (Sort a copy and take the middle)

### Intuition

In sorted order, all copies of the majority value form one contiguous block of more than `n / 2` positions. A block that long must cover the middle position `n / 2`, wherever it starts.

### Algorithm

1. Copy `nums` and sort the copy.
2. Return the element at index `n / 2` (rounded down).

### Correctness

Let the majority block occupy indices `s` to `s + c - 1` with `c > n / 2`, so `c >= floor(n / 2) + 1`. Since the block fits in the array, `s <= n - c <= n - floor(n / 2) - 1 <= floor(n / 2)`, so the block starts at or before the middle index `m = floor(n / 2)`. It ends at `s + c - 1 >= c - 1 >= floor(n / 2) = m`. The block therefore contains `m`.

### Complexity

- Time: O(n log n) — the sort dominates; reading one index is O(1).
- Space: O(n) — the sorted copy. Sorting in place would need only the sort's own stack space.

### Trade-offs

A one-line answer that is easy to justify, but a log factor slower than the linear approaches and dependent on the guarantee: without a majority, the middle element is just the median. If the array arrives sorted, it is O(1).

### Pitfalls and edge cases

- Index `n / 2` is correct for both odd and even lengths; `(n - 1) / 2` also works, because the block covers both middle positions of an even-length array.
- Sorting the caller's array in place is a side effect; the references sort a copy.

### Language notes

- TypeScript: `Int32Array.from(nums).sort()` copies and sorts numerically. A plain `nums.sort()` would compare as strings and reorder the caller's array.
- Java: `nums.clone()` then `Arrays.sort`. Kotlin: `nums.sortedArray()` returns a sorted copy.
- Go: `slices.Clone` and `slices.Sort` sort a copy, so the caller's slice keeps its order.
- Rust: `nums` is an owned `Vec<i32>`, so `sort_unstable` sorts the argument itself; equal values are interchangeable, so stability does not matter.

## Approach: hash-map (Count occurrences in a hash map)

### Intuition

Counting each value once, instead of once per copy, removes the brute force's repeated work. A hash map from value to count does it in one pass, and the pass can stop as soon as some count exceeds `n / 2`.

### Algorithm

1. Create an empty map `counts`.
2. For each value `v` in `nums`:
   1. Set `counts[v]` to its previous count plus one.
   2. If `counts[v]` exceeds `n / 2`, return `v`.

### Correctness

Invariant: before each iteration, `counts` maps every value seen so far to the number of times it has been seen. The majority value reaches a count above `n / 2` no later than at its last occurrence, so the loop returns. No other value can ever reach that count, so the returned value is the majority value.

### Complexity

- Time: O(n) — one pass with O(1) average work per element.
- Space: O(n) — one entry per distinct value, up to about n/2 entries.

### Trade-offs

Linear and general: the same map answers "how often does each value occur?", which also solves variants such as "every value above n/3" or "is there a majority at all?". It pays for that with memory proportional to the number of distinct values; the vote solves this exact problem in O(1) space.

### Pitfalls and edge cases

- Returning only after the full pass and then searching the map works too, but the early exit keeps the common case shorter.
- In Java, compare counts as `int`, not as two `Integer` objects with `==`.

### Language notes

- Python: `dict.get(value, 0) + 1`; `collections.Counter(nums).most_common(1)[0][0]` is the idiomatic one-liner without the early exit.
- TypeScript: `counts.get(value) ?? 0` handles absent keys; a `Map` keeps number keys as numbers.
- Java: `counts.merge(value, 1, Integer::sum)` inserts or increments and returns the new count, which unboxes to `int`.
- Kotlin: `getOrDefault(value, 0) + 1`, then `counts[value] = count`.
- Go: a missing key reads as the zero value, so `counts[value]++` needs no existence check.
- Rust: `entry(value).or_insert(0)` returns a `&mut usize` to the count, which is then incremented and compared through the same borrow.

## Approach: boyer-moore (Boyer-Moore majority vote)

### Intuition

Pair each copy of the majority value with a different value and cancel the pair. Because the majority value fills more than half of the positions, it runs out of opponents before it runs out of copies, so something of it always survives. The vote performs this cancelling on the fly with one candidate and one counter.

### Algorithm

1. Set `votes = 0`.
2. For each value `v` in `nums`:
   1. If `votes == 0`, make `v` the new `candidate`.
   2. If `v == candidate`, increment `votes`; otherwise decrement it.
3. Return `candidate`.

### Correctness

Split the scan into segments that end each time `votes` returns to zero. Inside such a segment, the candidate occurs exactly as often as all other values together, so the segment holds at most half of its positions with any single value, in particular with the majority value `m`. Removing all finished segments therefore removes at most half of their positions' worth of `m`, so `m` still fills more than half of the final, unfinished segment. In that last segment `votes` never returns to zero, so its candidate occupies more than half of it as well. Two values cannot both fill more than half of the same segment, so the final candidate is `m`.

### Complexity

- Time: O(n) — one pass with constant work per element.
- Space: O(1) — one candidate and one counter.

### Trade-offs

Optimal in time and memory, and the answer interviewers look for after the hash map. It depends on the guarantee: without it, the vote still returns some candidate, and a second counting pass is needed to confirm or reject it. It does not generalize to "most frequent value" when no majority exists. The `n / 3` follow-up uses the same idea with two candidates and two counters.

### Pitfalls and edge cases

- Check `votes == 0` before comparing with the candidate; otherwise the first element after a reset is counted against the old candidate.
- The initial candidate value does not matter, since `votes` starts at zero and the first element replaces it; the references start from `nums[0]` only to have a valid value.

### Language notes

- All four references are the same loop over primitives. In Kotlin, `votes += if (value == candidate) 1 else -1` uses `if` as an expression; Java and TypeScript use the conditional operator.
- Go: the vote is a plain `int` that goes up and down; no map or sort is involved, so the loop allocates nothing.
- Rust: `votes` is an `i32` that can go negative only transiently; the loop moves the owned `Vec` into `for value in nums` and copies each `i32`.
