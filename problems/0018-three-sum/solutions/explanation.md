# Three Sum: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^3) | O(n) | n is tiny, or as a correctness oracle |
| hash-set | intermediate | O(n^2) | O(n) | you want quadratic time and think in terms of Two Sum |
| two-pointers | optimal | O(n^2) | O(n) | default answer |

All three sort a copy of `nums` first; the O(n) space is that copy (and, for `hash-set`, the set). The returned triples are not counted.

## Approach: brute-force (Check every triple of distinct values)

### Intuition

Every answer is a choice of three positions, so trying all of them finds every answer. Sorting first gives a cheap way to report each triple of values once: if you never pick the same value twice at the same level of the loops, no triple can be produced twice.

### Algorithm

1. Sort a copy `values` of `nums`.
2. For each `i`, skipping `i` when `values[i] == values[i - 1]`:
   1. For each `j > i`, skipping `j` when `j > i + 1` and `values[j] == values[j - 1]`:
      1. Let `third = -values[i] - values[j]`.
      2. If `third` occurs at some position after `j`, record `[values[i], values[j], third]`.
3. Return the recorded triples.

### Correctness

Any zero-sum triple of values, sorted as `a <= b <= c`, appears in the sorted array at positions `i < j < k`. Taking `i` as the first occurrence of `a` and `j` as the first occurrence of `b` after `i` gives a pair that the loops visit (the skips only drop later copies of the same value at the same level), and `c` is found after `j`. So every triple is found. A triple is recorded only for the first `i` with value `a` and the first `j` with value `b` after it; `c` is then determined, so no triple is recorded twice.

### Complexity

- Time: O(n^3) — up to n^2/2 pairs `(i, j)`, each followed by a linear scan for the third value.
- Space: O(n) — the sorted copy; the scan itself needs no extra memory.

### Trade-offs

It is short and its deduplication rule is the same one the optimal solution uses, which makes it a good oracle. At n = 1000 it performs on the order of 10^8 steps, which is still well under a second on the JVM, but at the stated maximum of 3000 it is 27 times slower and cubic growth makes it unusable. In an interview, state it and move on.

### Pitfalls and edge cases

- Skipping duplicates at the second level must compare with `values[j - 1]` only when `j > i + 1`; otherwise `[-1, -1, 2]` loses its triple because the second `-1` is skipped against the first.
- Search for the third value only after `j`. Searching the whole array can reuse a position: in `[-2, 1, 3]`, the pair -2 and 1 needs a third value of 1, and finding the 1 at position `j` itself would report `[-2, 1, 1]`.
- Sums stay within ±3 * 10^5, so 32-bit integers suffice.

### Language notes

- Python: `third in values[j + 1:]` copies the tail and scans it in C. It is still one comparison per element, so still cubic, but about ten times faster than a hand-written third loop.
- TypeScript: `[...nums].sort((a, b) => a - b)` sorts a copy numerically. The default `sort()` compares strings and puts `-5` after `-10`.
- Java: `nums.clone()` then `Arrays.sort` sorts primitives without boxing; `List.of(a, b, c)` builds an immutable triple.
- Kotlin: `sortedArray()` returns a sorted `IntArray` copy; `(j + 1 until n).any { ... }` stops at the first match.
- Go: `slices.Clone` then `slices.Sort` sort a copy, and `slices.Contains(values[j+1:], third)` scans the suffix through a slice header, without copying it. A nil `triples` slice encodes as `[]`.
- Rust: `nums` is owned, so `sort_unstable` sorts it in place after a rename to `values`. `values[j + 1..].contains(&third)` scans the suffix through a borrowed subslice, and `n.saturating_sub(2)` keeps the loop bound from underflowing `usize`.

## Approach: hash-set (Fix one value and run two-sum with a hash set)

### Intuition

Once the first value `a` is fixed, the rest is Two Sum: find pairs `b + c == -a` among the later values. A hash set of the values already passed answers "have I seen the partner of `c`?" in O(1), so each first value costs one linear pass instead of a quadratic one.

### Algorithm

1. Sort a copy `values` of `nums`.
2. For each `i`, skipping repeated values of `values[i]`:
   1. Start an empty set `seen` and set `lastLargest` to none.
   2. For each `j > i`: let `middle = -values[i] - values[j]`. If `middle` is in `seen` and `values[j] != lastLargest`, record `[values[i], middle, values[j]]` and set `lastLargest = values[j]`. Then add `values[j]` to `seen`.
3. Return the recorded triples.

### Correctness

For a fixed first value `a = values[i]`, `seen` holds exactly the values between position `i + 1` and `j - 1`. A triple `a <= b <= c` with `b` at an earlier position than `c` is found when `j` reaches the first position of `c` that has some `b` before it, because `b` is then in `seen`. Within one `i`, the triple is determined by `c = values[j]`; the array is sorted, so equal values of `c` are consecutive and the `lastLargest` check records each `c` once. Skipping repeated first values keeps different `i` from producing the same triple.

### Complexity

- Time: O(n^2) — n first values, each followed by one pass with O(1) average set operations.
- Space: O(n) — the sorted copy and a set of up to n values.

### Trade-offs

Quadratic like the optimal solution, and natural if you already know Two Sum. Hash operations cost more than array comparisons, and the deduplication needs an extra variable, so in practice it runs about 1.5 to 2 times slower than the two-pointer scan and uses more memory. Its advantage appears in variants where sorting is not allowed or the array is huge and almost unique; for this problem the sort is needed anyway for deduplication.

### Pitfalls and edge cases

- Add `values[j]` to `seen` after the lookup, not before. In `[-2, 1, 3]` with first value -2, adding 1 before looking up its partner (also 1) would match the 1 with itself and report `[-2, 1, 1]`.
- Reset `seen` for every first value; values before `i` must not be used as the middle element.
- `lastLargest` must start as "none", not 0, since 0 is a valid third value.

### Language notes

- Python: a `set[int]` per first value; `last_largest = None` is distinct from every integer.
- TypeScript: `Set<number>` and `number | undefined` for the sentinel.
- Java: `HashSet<Integer>` boxes every value. A primitive sentinel needs a separate `appended` flag, because no `int` value is free to mean "none".
- Kotlin: `HashSet<Int>` and `Int?` for the sentinel; `values[j] != lastLargest` compares an `Int` with an `Int?` safely.
- Go: a `map[int]bool` is the per-`i` set, and a missing key reads as `false`. No `int` value is free to mean "none", so the last appended value travels with an `appended` flag, as in Java.
- Rust: `Option<i32>` is the "none" sentinel, and `last_largest != Some(values[j])` compares an `i32` with the option directly; the `HashSet` type is inferred from the later `contains` and `insert` calls.

## Approach: two-pointers (Sort and close in from both ends)

### Intuition

After sorting, fix the first value `values[i]` and look for pairs summing to `-values[i]` in the part to its right. In a sorted range, a pair search needs no hash set: start one pointer at each end. If the sum is too small, only moving the left pointer right can increase it; if it is too large, only moving the right pointer left can decrease it. Each step discards one position for good, so the search is linear.

### Algorithm

1. Sort a copy `values` of `nums`.
2. For each `i` while `values[i] <= 0`, skipping repeated values of `values[i]`:
   1. Set `left = i + 1` and `right = n - 1`.
   2. While `left < right`, let `total = values[i] + values[left] + values[right]`:
      - If `total < 0`, increase `left`.
      - If `total > 0`, decrease `right`.
      - Otherwise record the triple, move both pointers inward, and keep increasing `left` while `values[left] == values[left - 1]`.
3. Return the recorded triples.

### Correctness

For a fixed `i`, the pair search never skips a valid pair. When `total < 0`, `values[left]` cannot pair with any position at or left of `right`, because those values are all at most `values[right]`; so discarding `left` loses nothing. The case `total > 0` is symmetric for `right`. When a triple is found, skipping equal values at `left` discards only pairs that would repeat the same second value, and therefore the same triple. Skipping repeated first values prevents different `i` from repeating triples. Stopping once `values[i] > 0` is safe: three values that are all positive cannot sum to zero.

### Complexity

- Time: O(n^2) — the sort is O(n log n), and each first value is followed by one pass in which every step moves a pointer.
- Space: O(n) — the sorted copy; the pointer scan uses O(1).

### Trade-offs

Same growth as `hash-set`, smaller constants, no hashing, and deduplication falls out of the sorted order. It is the standard interview answer, and the same skeleton solves 3Sum Closest, 4Sum (one more fixed index, O(n^3)) and Two Sum on Sorted Input. Its cost is the sort, which also loses the original positions, which is fine here because the problem asks for values.

### Pitfalls and edge cases

- After recording a triple, move both pointers. Moving only one and relying on the comparison next time still works but repeats the duplicate check needlessly; moving neither loops forever.
- Skip duplicates only after a match. Skipping forward over equal values before checking the sum loses triples whose second and third values are equal, such as `[-2, 1, 1]`: the left pointer jumps onto the right one before the pair is ever tested.
- The early exit is `values[i] > 0`, not `values[i] >= 0`: `[0, 0, 0]` needs a first value of zero.
- Sort numerically. Lexicographic sorting breaks the pointer logic silently.

### Language notes

- Python: `sorted(nums)` copies and sorts; plain index arithmetic is the fastest form in CPython.
- TypeScript: always pass a comparator to `sort`; the loop condition `values[i] <= 0` folds the early exit into the `for` header.
- Java: `Arrays.sort(int[])` is a dual-pivot quicksort on primitives (no boxing). Return `List<List<Integer>>`, built with `List.of`, to match the generated stub.
- Kotlin: `when` with conditions keeps the three branches together; `listOf` builds each triple and the result is a `MutableList<List<Int>>` returned as `List<List<Int>>`.
- Go: a `switch` with no subject keeps the three sign cases flat, and the sorted copy keeps the caller's slice intact.
- Rust: `total.cmp(&0)` with a `match` on `Ordering` covers the three cases exhaustively. After a hit both pointers have already moved, so `right - 1` cannot underflow: `right` stays above `left`.
