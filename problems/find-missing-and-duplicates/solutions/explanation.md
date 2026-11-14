# Find All Missing and Duplicate Numbers: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| hash-set | brute | O(n) | O(n) | the input must stay untouched and memory is available, or as a correctness oracle |
| sort | intermediate | O(n log n) | O(1) | memory is tight, the input may be reordered and a log factor does not matter |
| cyclic-sort | optimal | O(n) | O(1) | default answer; the statement asks for linear time and constant memory |

One fact drives every approach: the array has `n` slots and the values come from `1..n`, so every value is a valid index in disguise. Value `v` has a natural home at index `v - 1`. Each missing value leaves one slot that has to hold something else, and each spare copy of a repeated value is that something else. So the number of spare copies equals the number of missing values, and they pair up slot by slot once the array has been put in order.

## Approach: hash-set (Two hash sets of the values seen and the values repeated)

### Intuition

Remember every value you have met. A value that is already in the set when it comes again is repeated. Afterwards, a value from `1` to `n` that is not in the set is missing. Reading the answers by walking `1..n` makes them sorted for free.

### Algorithm

1. Create `seen` and `repeated`, both empty.
2. For each `value` in `nums`: if `value` is already in `seen`, add it to `repeated`; add it to `seen`.
3. `missing` is every `v` in `1..n`, in order, that is not in `seen`.
4. `duplicated` is every `v` in `1..n`, in order, that is in `repeated`.
5. Return both lists.

### Correctness

After step 2, `seen` holds exactly the values that occur, and `repeated` holds the values met at least twice: the second copy and every later one finds the value in `seen`. Steps 3 and 4 read those facts for each possible value in ascending order, so both lists are exact and sorted. A value with three copies is added to the set `repeated` twice, which changes nothing, so it is listed once.

### Complexity

- Time: O(n) — one pass over the array and one pass over `1..n`, with O(1) average cost per set operation.
- Space: O(n) — up to `n` distinct values in `seen`.

### Trade-offs

Simple, obviously correct and read-only, which makes it the oracle. It spends memory the statement forbids: the sets can hold all `n` values, and that is what the memory column of the bench shows against the other two approaches. It is the right first answer in an interview, as it shows that only membership matters, and the follow-up question is how to store membership in the array itself.

### Pitfalls and edge cases

- Walk `1..n`, not the sets: iterating a hash set gives no order, and sorting the repeated values afterwards costs a log factor.
- A value that occurs three times must be listed once, so `repeated` is a set, not a list appended to on every extra copy.

### Language notes

- Python: `set` literals and comprehensions keep this short; membership tests are O(1) average.
- TypeScript: `Set<number>` with `has` and `add`; the values are plain numbers, so no boxing is needed.
- Java: `HashSet<Integer>` boxes every value, and `Set.add` returns false when the value was already there, which is the repeat test in one call.
- Kotlin: `HashSet<Int>` boxes in the same way; `values.filter { it !in seen }` over the range reads as the statement does.
- Go: `map[int]bool` is the set, and a missing key reads as `false`, so the tests need no comma-ok.
- Rust: `HashSet<i32>`; `insert` returns false when the value was present. The range `1..=n` is cloned so that both filters can walk it.

## Approach: sort (Sort in place and compare neighbours)

### Intuition

In sorted order, equal values are neighbours and a gap between neighbours is a run of missing values. One pass with a counter for "the smallest value not seen yet" reads both answers, already in ascending order.

### Algorithm

1. Sort `nums` in place.
2. Set `expected = 1` (the smallest value not accounted for yet) and `previous = 0`.
3. For each `value` in the sorted array:
   1. If `value == previous`, it is a repeat: append it to `duplicated` unless it is already the last entry, and move on.
   2. Otherwise every number from `expected` up to `value - 1` is missing: append them to `missing`. Then set `expected = value + 1` and `previous = value`.
4. After the loop, every number from `expected` to `n` is missing: append them.
5. Return both lists.

### Correctness

In sorted order the first copy of each distinct value is followed by its other copies. At the first copy of `value`, all smaller values that occur have been passed, so the numbers between `expected` and `value - 1` cannot occur and are missing. Later copies of the same value are the repeats, and the check against the last entry of `duplicated` lists the value once however many copies there are. After the last element, `expected` is one more than the largest value that occurs, so the numbers from there to `n` are missing too.

### Complexity

- Time: O(n log n) — the sort dominates; the scan is O(n).
- Space: O(1) — beyond the output, an in-place sort needs no memory that grows with `n` when its algorithm is heapsort or a quicksort that recurses on the smaller side; the library sorts differ, see the language notes.

### Trade-offs

Needs no hash set and no clever indexing, and its code is easy to get right. It costs a log factor over the linear approaches and reorders the input, as cyclic sort does. It is the answer when a candidate does not see the swap trick: it meets the memory limit and misses only the time limit.

### Pitfalls and edge cases

- Start `previous` at `0`, a value that cannot occur, so the first element is never taken for a repeat.
- A value with three copies must be listed once: compare with the last entry of `duplicated` before appending.
- The numbers after the largest value still count as missing; forgetting step 4 loses every missing value above the maximum.
- TypeScript's default `sort` compares values as text, which puts 10 before 9.

### Language notes

- Python: `list.sort()` is Timsort, which may use up to `n / 2` references of scratch memory; the bound above is for the algorithmic idea, not the library. `range` is extended into the list without a loop.
- TypeScript: `sort` needs the comparator `(a, b) => a - b`.
- Java: `Arrays.sort(int[])` is a dual-pivot quicksort and sorts the primitives in place; comparing `duplicated.get(...)` with an `int` unboxes it.
- Kotlin: `IntArray.sort()` calls the same `Arrays.sort`; `lastOrNull()` returns null on an empty list, so the comparison with `value` is false and the value is appended.
- Go: `slices.Sort` is an in-place pattern-defeating quicksort.
- Rust: `sort_unstable` sorts in place without allocating; the stable `sort` allocates a buffer of up to `n / 2` elements.

## Approach: cyclic-sort (Swap every value to its own index and read off the misplaced ones)

### Intuition

Use the array itself as the membership table: index `v - 1` is the home of the value `v`. Move every value to its home by swapping. When a value finds its home already holding the same value, it is a spare copy and stays where it is. Afterwards every value that occurs sits at its home, and each slot that holds something else points to a missing value (the slot's own number) and carries a repeated one (the value in it).

### Algorithm

1. For each index `i` from 0 to `n - 1`: while the slot `nums[i] - 1` does not hold `nums[i]`, swap `nums[i]` with the value at that slot.
2. For each index `i` from 0 to `n - 1`:
   1. If `|nums[i]| == i + 1`, the slot is at home: skip it.
   2. Otherwise `i + 1` is missing: append it to `missing`, and mark that the value `spare = nums[i]` is repeated by negating the slot where it is at home, `nums[spare - 1] = -spare`.
3. `duplicated` is every `v` from 1 to `n`, in order, whose home `nums[v - 1]` is negative.
4. Return `missing` and `duplicated`.

### Correctness

Step 1 ends with every occurring value at its home. Each swap writes a value into its home, and a home that already holds the right value is never written again, because the loop swaps only when the home holds a different value. The inner loop at index `i` stops only when the home of `nums[i]` holds that value too, which includes the case that the home is `i` itself, so every position is finished. After step 1, a slot `i` that does not hold `i + 1` cannot be the home of an occurring value, so `i + 1` is missing, and it holds a value whose home holds the same value, so the value occurs at least twice. Step 2 therefore finds every missing value, in ascending order since `i` ascends, and marks every repeated value at its home. A home is never a slot step 2 reports on, so marking it cannot change what is reported there, and a value with three copies marks the same home twice with the same sign. Step 3 reads the marks in ascending order of value.

### Complexity

- Time: O(n) — every swap places one value at its home for good, so there are at most `n` swaps over all positions, despite the nested loops; the two scans are O(n).
- Space: O(1) — the work happens in place, with one temporary for a swap; the signs are stored in the array.

### Trade-offs

Meets both requirements of the statement, at the cost of reordering the caller's array. The usual write-up stops after step 1 and collects `nums[i]` beside `i + 1` in one loop. That is simpler, but it lists the repeated values in the order of the missing slots, not in ascending order, and a value with three copies shows up twice; sorting that list repairs the order but costs a log factor on up to `n / 2` values. The sign marks of steps 2 and 3 give the sorted order in linear time. If the input must not change, copy it first (O(n) memory) or use the hash sets.

### Pitfalls and edge cases

- The loop condition must compare the value at the home, `nums[nums[i] - 1] != nums[i]`, not the index (`nums[i] != i + 1`). With a repeated value, the second test swaps two equal values forever.
- The home of `v` is `v - 1`. Using `v` as the index goes out of bounds for the value `n` and misplaces every other value.
- Compute the home index before swapping. In Python, `nums[i], nums[nums[i] - 1] = nums[nums[i] - 1], nums[i]` assigns `nums[i]` first and then reads the changed `nums[i]` to locate the second target, which corrupts the array.
- Appending `nums[i]` to the repeated list in step 2 gives an unsorted list, and a value with three copies is listed twice. The hidden cases include both.
- When reading a slot in step 2, compare absolute values: a home already marked negative must not be taken for a missing slot.

### Language notes

- Python: the tuple swap is safe once `home` is a separate variable; `abs` reads a slot with or without its mark.
- TypeScript: destructuring `[nums[i], nums[home]] = [nums[home], nums[i]]` swaps; `home` is computed first.
- Java: a classic three-step swap through a temporary; `Math.abs` reads the marked slots.
- Kotlin: the swap uses a temporary for clarity, and `(1..n).filter { nums[it - 1] < 0 }` reads the marks.
- Go: the standard library has no integer `abs`, so a two-line helper stands in; the tuple assignment `nums[i], nums[home] = nums[home], nums[i]` swaps. The function reorders the caller's slice, as the other languages do.
- Rust: `Vec::swap` exchanges two slots; the values are `i32` but the indices `usize`, so the home is converted after the subtraction (values are at least 1), and `unsigned_abs` reads a marked slot without an overflow case.
