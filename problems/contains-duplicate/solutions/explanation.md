# Contains Duplicate: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | n is tiny, the input must not be copied or reordered, or as a correctness oracle |
| sorting | intermediate | O(n log n) | O(n) | memory for a hash set is tight, or you may sort the input in place |
| hash-set | optimal | O(n) | O(n) | default answer |

The three approaches answer the same question, "do two positions hold equal values?", with three different ways of bringing equal values together: try every pair, make them adjacent by sorting, or remember every value in a structure with constant-time lookup.

## Approach: brute-force (Compare every pair)

### Intuition

A duplicate is a pair of distinct positions `i < j` with `nums[i] == nums[j]`. There are n(n - 1)/2 such pairs, so checking them all is guaranteed to find a duplicate when one exists.

### Algorithm

1. For each index `i` from 0 to n - 1:
   1. For each index `j` from `i + 1` to n - 1, if `nums[j] == nums[i]`, return `true`.
2. Return `false`.

### Correctness

Every unordered pair of positions `{i, j}` with `i < j` is examined exactly once, when the outer loop is at `i` and the inner loop at `j`. The inner loop starts at `i + 1`, so a position is never compared with itself. If a duplicate exists, its pair is examined and the method returns `true`; if the loops finish, no pair holds equal values, so `false` is correct.

### Complexity

- Time: O(n^2) — up to n(n - 1)/2 comparisons when there is no duplicate. The test generator puts any duplicate in the last tenth of the array, so the scan does about n^2/2 comparisons at every seed.
- Space: O(1) — two indices; nothing is copied.

### Trade-offs

It is the only approach that needs no extra memory and leaves the input untouched, which makes it a dependable oracle. At n = 30,000 it compares about 4.5 * 10^8 pairs: a few seconds in Python and a fraction of a second on the JVM, while the hash set needs a few milliseconds. Mention it first in an interview, then improve on it.

### Pitfalls and edge cases

- Starting the inner loop at `i` instead of `i + 1` compares every element with itself and always returns `true`.
- An array of one element has no pair and must return `false`.
- Returning early on the first match matters: a duplicate near the front makes the scan short.

### Language notes

- Python: the reference uses `nums.index(value, i + 1)`, which scans the rest of the list in C and raises `ValueError` when the value is absent. It is still one comparison per later element, so still O(n^2), but each comparison costs about 6 ns instead of about 50 ns for a hand-written inner `for` loop. Constant factors change; the growth does not.
- TypeScript: compare with `===`. Plain index loops are the fastest form in V8.
- Java and Kotlin: nested loops over `int[]` (Kotlin `IntArray`) compare primitives, with no boxing.
- Go: `nums[i+1:]` is a slice header over the same array, not a copy, so ranging over the rest of the slice allocates nothing.
- Rust: `nums[i + 1..].contains(value)` is the same linear scan over a borrowed subslice; when `i` is the last index the range is empty, not out of bounds.

## Approach: sorting (Sort a copy and compare neighbors)

### Intuition

After sorting, equal values sit next to each other. A duplicate exists exactly when some element equals its immediate neighbor, which one linear pass can check.

### Algorithm

1. Copy `nums` and sort the copy in ascending order.
2. For each index `i` from 1 to n - 1, if `ordered[i] == ordered[i - 1]`, return `true`.
3. Return `false`.

### Correctness

Sorting permutes the values without changing how many times each occurs, so the copy has a duplicate exactly when `nums` does. In a sorted sequence, all copies of a value form one contiguous block: any element strictly between two copies of `v` must be at least `v` and at most `v`, so it equals `v`. A block of two or more copies therefore contains two adjacent equal elements, which step 2 finds. Conversely, two adjacent equal elements are a duplicate.

### Complexity

- Time: O(n log n) — the sort dominates; the neighbor pass is O(n).
- Space: O(n) — the sorted copy. Sorting `nums` in place would cut this to the sort's own stack space (O(log n) for an introsort or dual-pivot quicksort), at the price of reordering the caller's array.

### Trade-offs

Slower than the hash set by a log factor, but its memory is a flat array of primitives, which is several times smaller than a hash set of boxed integers on the JVM. When the input may be modified, sorting in place gives O(1) extra memory beyond the sort itself: the best option under a tight memory limit. It also naturally extends to "find all duplicated values" in sorted order.

### Pitfalls and edge cases

- Sorting the input in place is a side effect. The references sort a copy, because nothing in the statement allows reordering the caller's array.
- Start the neighbor loop at index 1; an array of one element has no neighbors.
- In TypeScript, `Array.prototype.sort` without a comparator sorts as strings (`[10, 9]` stays `[10, 9]`). This does not break duplicate detection, since equal numbers have equal strings, but it is slower and a classic bug in other problems. The reference avoids it with a typed array.

### Language notes

- Python: `sorted(nums)` returns a new list (Timsort, O(n) extra memory). `itertools.pairwise` (Python 3.10+) yields adjacent pairs without index arithmetic.
- TypeScript: `Int32Array.from(nums).sort()` copies into a typed array, which sorts numerically by default. The values fit in 32 bits by the constraints.
- Java: `nums.clone()` copies the primitive array; `Arrays.sort(int[])` is a dual-pivot quicksort with no boxing.
- Kotlin: `nums.sortedArray()` returns a sorted copy of the `IntArray`; `nums.sort()` would sort in place.
- Go: `slices.Clone` copies the slice and `slices.Sort` sorts the copy in place (pattern-defeating quicksort, no boxing); sorting `nums` itself would reorder the caller's slice.
- Rust: `nums` is an owned `Vec<i32>`, so the function sorts its own argument with `sort_unstable` and needs no copy; equal `i32`s are indistinguishable, so the unstable sort loses nothing. `windows(2)` yields the adjacent pairs.

## Approach: hash-set (Hash set of values seen so far)

### Intuition

The brute force asks, for each element, "did this value already appear?" by scanning. A hash set answers that question in O(1) on average. Walking the array once and checking each value against the set before adding it finds the first repeat as soon as it is reached.

### Algorithm

1. Create an empty set `seen`.
2. For each value `v` in `nums`:
   1. If `v` is in `seen`, return `true`.
   2. Otherwise add `v` to `seen`.
3. Return `false`.

### Correctness

Invariant: at the start of each iteration, `seen` holds exactly the values of the elements already visited. If the current value is in `seen`, an earlier position holds the same value, so a duplicate exists. If the loop finishes, every value was absent from `seen` when it was visited, so no value appeared at an earlier position: all values are distinct.

### Complexity

- Time: O(n) — one pass; each membership test and insertion is O(1) on average.
- Space: O(n) — the set holds up to n values when all are distinct.

### Trade-offs

Linear time for linear memory, which is the expected interview answer. It stops at the first repeat, unlike `len(set(nums)) != len(nums)`, which always builds the full set. On the JVM each entry costs tens of bytes (a boxed `Integer` plus a hash-table node), so for very large inputs with no duplicates the sorting approach can be faster in practice despite its log factor.

### Pitfalls and edge cases

- Check before inserting. Inserting first and then checking finds every value, so it always returns `true`.
- Adversarial inputs can degrade hash tables (many keys in one bucket). Python's integer hashing is predictable, but interview settings treat set operations as O(1).

### Language notes

- Python: `set` membership with `in` and `add`. The one-liner `len(set(nums)) < len(nums)` is correct and fast in C, but it cannot stop early.
- TypeScript: `Set<number>` compares numbers by value (SameValueZero), so `has` works as expected. Do not use a plain object as a set: its keys become strings and it inherits prototype keys.
- Java: `HashSet<Integer>` boxes each value. `Set.add` returns `false` when the value is already present, which fuses the check and the insert into one call.
- Kotlin: `HashSet<Int>` is `java.util.HashSet<Integer>`, so it boxes too. `add` returns `false` for a value already present, as in Java.
- Go: there is no set type; `map[int]struct{}` is the idiom, and the empty struct takes no memory for the value. The comma-ok lookup `_, ok := seen[value]` is the membership test.
- Rust: `HashSet::insert` returns `false` when the value was already present, so `any(|value| !seen.insert(value))` checks and inserts in one call and stops at the first duplicate.
