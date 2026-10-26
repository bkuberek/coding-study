# Two Sum on Sorted Input: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | n is tiny, or as a correctness oracle |
| binary-search | intermediate | O(n log n) | O(1) | you need the partner of only a few elements |
| two-pointers | optimal | O(n) | O(1) | default answer |

## Approach: brute-force (Check every pair)

### Intuition

Ignore the order and try every pair of positions `i < j`. The first pair that reaches the target is the only one.

### Algorithm

1. For each `i` from 0 to n - 1, compute `complement = target - numbers[i]`.
2. For each `j` from `i + 1` to n - 1, if `numbers[j] == complement`, return `[i, j]`.
3. Return an empty array (unreachable on valid input).

### Correctness

Every pair `i < j` is examined once, with `i` as the smaller position, so the returned pair is already in the required order. Since exactly one pair reaches the target, the first one found is the answer.

### Complexity

- Time: O(n^2) — up to n(n - 1)/2 pair checks. The generator places the earlier element of the pair between positions n/20 and n/10, so this scan does between about n^2/20 and n^2/10 checks.
- Space: O(1) — two indices.

### Trade-offs

It ignores the most useful fact in the statement, that the array is sorted. At n = 10^5 it does about 5 * 10^8 checks: seconds in Python, about a second on the JVM, while the other two approaches take a millisecond or two. It serves as the oracle; in an interview, mention it only as the baseline.

### Pitfalls and edge cases

- Start the inner loop at `i + 1`, so a value is never paired with itself.
- Equal values at different positions are a valid pair: `[2, 2, 7]` with target 4 returns `[0, 1]`.
- The pair sum is at most 2 * 10^9 in absolute value, which still fits a 32-bit signed integer.

### Language notes

- Python: `numbers.index(complement, i + 1)` scans the rest of the list in C. It is still one comparison per later element, so still quadratic, just with a small constant.
- TypeScript, Java, Kotlin: plain nested index loops; no boxing on `number[]`, `int[]` or `IntArray`.

## Approach: binary-search (Binary search for each complement)

### Intuition

For a fixed `i`, the partner must have the value `target - numbers[i]` and sit to the right of `i`. Because the array is sorted, a binary search over `numbers[i+1 ..]` finds such a value, or proves it absent, in O(log n) steps.

### Algorithm

1. For each `i` from 0 to n - 2:
   1. Let `complement = target - numbers[i]`.
   2. Binary search `numbers[i+1 .. n-1]` for `complement`.
   3. If found at `j`, return `[i, j]`.
2. Return an empty array (unreachable on valid input).

### Correctness

The sub-array `numbers[i+1 .. n-1]` is sorted, so binary search correctly decides whether `complement` occurs in it and returns a position of it. Searching only to the right of `i` guarantees `i < j`. The first `i` that has a partner is the smaller position of the unique pair, and its partner position is unique too (two different partners would form two valid pairs).

### Complexity

- Time: O(n log n) — up to n binary searches of O(log n) each.
- Space: O(1) — the search uses a few indices.

### Trade-offs

A big step up from quadratic and a natural first idea when you notice "sorted". It still repeats work: each search starts from scratch, although the partner of `numbers[i+1]` can only lie at or left of the partner of `numbers[i]`. The two-pointer scan uses that and is linear. Binary search wins only when you need partners for a few chosen elements, not for a full scan.

### Pitfalls and edge cases

- Search strictly to the right of `i`; searching the whole array can return `i` itself when `numbers[i] * 2 == target`.
- With duplicates, any position of the complement is acceptable here, because the answer is unique: two positions holding the complement would form two pairs.
- Compute the midpoint without overflow: `(low + high) >>> 1` in TypeScript and Java, or `low + (high - low) / 2`.
- `target - numbers[i]` stays within 2 * 10^9 in absolute value because `target` is limited to 10^9, so it does not overflow a 32-bit integer.

### Language notes

- Python: `bisect_left(numbers, complement, i + 1)` returns the leftmost insertion point; check that the position is in range and holds the complement.
- TypeScript: no built-in binary search on arrays; the reference writes a lower bound with `>>> 1`.
- Java: `Arrays.binarySearch(numbers, from, to, key)` returns a non-negative position when found and a negative insertion point otherwise; with duplicates it may return any matching position.
- Kotlin: `IntArray.binarySearch(element, fromIndex)` has the same contract as the Java method.

## Approach: two-pointers (Close in from both ends)

### Intuition

Compare the smallest and largest remaining values. If their sum is below the target, the smallest value is too small even with the largest possible partner, so it can be discarded. If the sum is above the target, the largest value is too large even with the smallest possible partner, so it can be discarded. Each comparison discards one position, so after at most n - 1 steps the pair is found.

### Algorithm

1. Set `left = 0`, `right = n - 1`.
2. While `left < right`:
   1. Let `total = numbers[left] + numbers[right]`.
   2. If `total == target`, return `[left, right]`.
   3. If `total < target`, increase `left`; otherwise decrease `right`.
3. Return an empty array (unreachable on valid input).

### Correctness

Invariant: the answer pair `(p, q)` satisfies `left <= p < q <= right`. It holds at the start. Suppose `total < target` and `left` is about to be discarded: if `left == p`, then `numbers[p] + numbers[right] < target = numbers[p] + numbers[q]` gives `numbers[right] < numbers[q]`, contradicting `q <= right` in a sorted array. So `left != p` and discarding it keeps the invariant. The case `total > target` is symmetric. Each step shrinks the range, and the range always contains the pair, so the loop reaches `left == p` and `right == q` and returns them in order.

### Complexity

- Time: O(n) — each step moves one pointer inward; at most n - 1 steps.
- Space: O(1) — two indices.

### Trade-offs

Linear time and constant memory, the best possible for a single query. It is the canonical two-pointer pattern; Three Sum runs it once per fixed first value. Unlike the hash-map solution of the unsorted problem, it needs the order, so on unsorted input you would pay O(n log n) to sort and lose the original positions.

### Pitfalls and edge cases

- Move exactly one pointer per step. Moving both when the sum is off can skip the answer.
- Use `left < right`, not `left <= right`, so a value is never paired with itself.
- Return 0-based positions, smaller first; this problem does not use the 1-based positions of some well-known versions.

### Language notes

- Python: plain index arithmetic; the loop runs at most n - 1 times, so even at 10^5 it takes a few milliseconds.
- TypeScript: `total === target` compares exactly; all values are integers well within the 2^53 safe range.
- Java: the sum of two `int`s within 10^9 cannot overflow; no `long` is needed.
- Kotlin: `when` with conditions expresses the three-way branch in one expression.
