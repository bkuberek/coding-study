# First Missing Positive: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | n is tiny, the input must stay untouched, or as a correctness oracle |
| hash-set | intermediate | O(n) | O(n) | the input must stay untouched and memory is available |
| cyclic-sort | optimal | O(n) | O(1) | default answer; the statement asks for linear time and constant memory |

One fact drives every approach: the answer is between 1 and n + 1. An array of length n can hold at most n distinct values from 1 to n; if it holds all of them the answer is n + 1, and otherwise the smallest missing one is at most n. So only the values 1..n matter, and the search for the answer never needs to go beyond n + 1.

## Approach: brute-force (Try 1, 2, 3 and so on with linear searches)

### Intuition

Check the candidates in increasing order: is 1 present? Is 2? The first candidate that is absent is the answer, and the bound above guarantees that this happens by n + 1.

### Algorithm

1. Set `candidate = 1`.
2. While `candidate` occurs in `nums` (a linear scan), increment it.
3. Return `candidate`.

### Correctness

Every candidate below the returned value was found in `nums`, and the returned value was not, so it is the smallest positive integer missing. The loop terminates because at most n candidates can be present.

### Complexity

- Time: O(n^2) — up to n + 1 candidates, each a scan of up to n elements. The test generator makes the answer at least about n/4, so the scans add up to about n^2/8 comparisons or more at every seed.
- Space: O(1) — one counter; the input is not modified.

### Trade-offs

Correct, read-only and memory-free, which makes it the oracle. At n = 30,000 it can scan around 4 * 10^8 elements. It does show the n + 1 bound in action, which is the first insight to state in an interview.

### Pitfalls and edge cases

- Start at 1, not 0: zero is not positive.
- No special case is needed for negative values, zeros or huge values: they simply never match a candidate.

### Language notes

- Python: `candidate in nums` scans in C, about ten times faster than a Python loop, with the same growth.
- TypeScript: `includes` is a linear scan.
- Java: a small `contains` helper loops over the `int[]` without boxing.
- Kotlin: `candidate in nums` calls `IntArray.contains`, also a primitive linear scan.

## Approach: hash-set (Hash set of the values)

### Intuition

Make the membership test O(1) by putting all values into a hash set first; then the candidate loop of the brute force costs O(n) in total.

### Algorithm

1. Build `present`, the set of values in `nums`.
2. Set `candidate = 1` and increment it while it is in `present`.
3. Return `candidate`.

### Correctness

Identical to the brute force: membership in `present` is exactly membership in `nums`.

### Complexity

- Time: O(n) — building the set is O(n) on average, and the loop runs at most n + 1 times with O(1) lookups.
- Space: O(n) — the set.

### Trade-offs

Linear time and read-only, but O(n) memory, which the statement rules out. It is the right intermediate step in an interview: it shows that only membership matters, and the remaining question is how to store membership without extra memory.

### Pitfalls and edge cases

- Inserting only values in `1..n` would save memory, but the set is still O(n) in the worst case.

### Language notes

- Python: `set(nums)` is built in C.
- Java: `HashSet<Integer>` boxes every value; `contains(candidate)` boxes the argument.
- Kotlin: `nums.toHashSet()` converts the `IntArray` into a `HashSet<Int>`.

## Approach: cyclic-sort (Swap every value to its own index)

### Intuition

Use the array itself as the membership table: index `v - 1` is the "home" of value `v`, for `1 <= v <= n`. Move every in-range value to its home by swapping. Afterwards, the first index `i` whose slot does not hold `i + 1` reveals the missing value; if every slot is right, the answer is n + 1.

### Algorithm

1. For each index `i` from 0 to n - 1:
   1. While `nums[i]` is in `1..n` and its home `nums[i] - 1` does not already hold it, swap `nums[i]` with the value at its home.
2. For each index `i` from 0 to n - 1, if `nums[i] != i + 1`, return `i + 1`.
3. Return `n + 1`.

### Correctness

After step 1, for every value `v` in `1..n` that occurs in `nums`, `nums[v - 1] == v`. Each swap writes some value `v` into its home `v - 1`; a home that holds its own value is never written again, because the loop only swaps when the home does not hold it yet. The inner loop at position `i` stops only when `nums[i]` is out of range or already sits at its home (possibly a repeat of a value that is home elsewhere), so no in-range value is left behind without its home being filled. Step 2 then finds the smallest `i + 1` whose home is not filled, which is the smallest value in `1..n` that does not occur. If all homes are filled, every value from 1 to n occurs and the answer is n + 1.

### Complexity

- Time: O(n) — each swap puts one value into its home for good, so there are at most n swaps in total across all iterations, despite the nested loops; the scans are O(n).
- Space: O(1) — the work happens in place, with one temporary for the swap.

### Trade-offs

Meets both requirements of the statement, at the cost of reordering the caller's array; if that is not allowed, copy it first (O(n) memory again) or use the hash set. A popular alternative marks presence with signs: first replace out-of-range values with n + 1, then for each value `v` in range make `nums[v - 1]` negative, and finally return the first index with a positive value. It has the same bounds; the swap version keeps all values intact and is easier to argue correct.

### Pitfalls and edge cases

- The loop condition must compare against the value at the home, `nums[nums[i] - 1] != nums[i]`, not against the index (`nums[i] != i + 1`). With repeated values, the index test swaps two equal values forever.
- Compute the home index before swapping. In Python, `nums[i], nums[nums[i] - 1] = nums[nums[i] - 1], nums[i]` assigns `nums[i]` first and then reads the changed `nums[i]` to locate the second target, which corrupts the array.
- Extreme values such as `-2^31` and `2^31 - 1` fail the range test immediately, so `nums[i] - 1` is never computed for them.

### Language notes

- Python: the tuple swap is safe once `home` is a separate variable.
- TypeScript: destructuring `[nums[i], nums[home]] = [nums[home], nums[i]]` swaps; `home` is again computed first.
- Java: a classic three-step swap through a temporary.
- Kotlin: `nums[i] in 1..n` expresses the range test; the swap uses a temporary for clarity (the `a = b.also { b = a }` idiom works too, but is harder to read).
