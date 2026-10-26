# Two Sum: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | n is tiny, memory is extremely tight, or as a correctness oracle |
| hash-map | optimal | O(n) | O(n) | default answer |

## Approach: brute-force (Check every pair)

### Intuition

The answer is one of the n(n - 1)/2 unordered pairs of positions. Trying them all is guaranteed to find it. Fixing the left element first turns each pair test into a question about one value: does `target - nums[i]` appear to the right of `i`?

### Algorithm

1. For each index `i` from 0 to n - 1, compute `complement = target - nums[i]`.
2. For each index `j` from `i + 1` to n - 1, if `nums[j] == complement`, return `[i, j]`.
3. If the loops finish, return an empty array. The constraints guarantee a pair, so this line is never reached on valid input.

### Correctness

Every unordered pair `{i, j}` with `i < j` is examined exactly once: when the outer loop is at `i` and the inner loop at `j`. Starting the inner loop at `i + 1` excludes `j == i`, so an element is never paired with itself. Since exactly one pair reaches `target`, the first pair found is that pair.

### Complexity

- Time: O(n^2) — the inner loop runs n - 1, n - 2, ..., 1 times, n(n - 1)/2 checks in the worst case. The test generator places the pair so that this scan does between about n^2/20 and n^2/10 checks.
- Space: O(1) — two indices and the complement; the returned array has a fixed size of two.

### Trade-offs

It needs no extra memory and is the easiest version to get right, which makes it the oracle that every other approach is checked against. At n = 10^5 it performs on the order of 10^9 comparisons: seconds in Python and hundreds of milliseconds on the JVM, where the hash map takes a few milliseconds. With time limits enabled (`cstudy test --time-limit`), the large generated case `g1` fails with `TLE` while the hash map passes. In an interview, state it first as the baseline, then improve it.

### Pitfalls and edge cases

- Starting the inner loop at `0` or at `i` pairs an element with itself: `[4, 3, 5]` with target 8 would wrongly return `[0, 0]`.
- Duplicates are fine: `[5, 5]` with target 10 is found because the two 5s sit at different positions.
- The constraints keep `nums[i] + nums[j]` within [-2 * 10^9, 2 * 10^9], inside the 32-bit range, so `int` addition does not overflow in Java or Kotlin.

### Language notes

- Python: the reference uses `nums.index(complement, i + 1)`, which scans the rest of the list in C. It is still one comparison per later element, so still O(n^2), but each check costs about 5 ns instead of about 24 ns for a hand-written `for j in range(i + 1, n)` loop. Constant factors change; the growth does not.
- TypeScript: use `===`. Plain index loops are the fastest form in V8; `nums.indexOf(complement, i + 1)` is an equivalent one-liner.
- Java: plain nested `for` loops over `int[]` involve no boxing. Return `new int[] {i, j}`.
- Kotlin: `IntArray` is a primitive `int[]`, so `nums[i]` does not box. `for (j in i + 1 until nums.size)` mirrors the Java loop.

## Approach: hash-map (One-pass hash map)

### Intuition

For each element, the brute force searches the rest of the array for one specific value. A hash map from value to index answers that search in O(1) on average. Looking up the partner among the elements already seen, before storing the current one, needs only one pass and can never return the current element as its own partner.

### Algorithm

1. Create an empty map `indexByValue` from value to index.
2. For each index `i` in order:
   1. Look up `target - nums[i]` in the map. If it is present at index `p`, return `[p, i]`.
   2. Otherwise store `indexByValue[nums[i]] = i`.
3. Return an empty array (unreachable on valid input).

### Correctness

Invariant: at the start of iteration `i`, the map holds the values of `nums[0..i-1]` (for a repeated value, its latest index). Let the unique answer be positions `p < q`. No pair is found before iteration `q`, because any earlier hit would be a second valid pair. At iteration `q`, `nums[p] == target - nums[q]` is in the map, because `p < q`. If the map holds another index `p'` for that value, then `{p', q}` is also a pair reaching `target`. Uniqueness then forces `p' == p`, so the method returns exactly `[p, q]`. The lookup happens before the insertion, so the current index is never in the map.

### Complexity

- Time: O(n) — one pass; each lookup and insertion is O(1) on average for a hash map.
- Space: O(n) — the map stores up to n - 1 entries before the pair is found. The generator puts the second element of the pair in the back half, so at least n/2 entries are stored.

### Trade-offs

It trades O(n) memory for linear time, which is almost always the right trade. It returns original indices directly, unlike the sort-plus-two-pointers technique (O(n log n), and it must carry the original indices along). Hash-map worst cases (adversarial collisions) are rarely a concern in interviews but worth one sentence.

### Pitfalls and edge cases

- Insert after the lookup, not before: inserting first lets `[4, 3, 5]` with target 8 match 4 with itself.
- Check for "absent", not "falsy": index 0 is a valid stored value. In Python `if index_by_value.get(...)` treats 0 as missing; compare with `None`. In TypeScript compare with `undefined`.
- Duplicates overwrite earlier indices. That is harmless here because a partner is always looked up before its duplicate overwrites it.

### Language notes

- Python: `dict.get` returns `None` for a missing key, so `is not None` distinguishes it from index 0. `enumerate` gives index and value together.
- TypeScript: use `Map<number, number>`, not a plain object. An object converts every key to a string and inherits prototype keys such as `constructor`; a `Map` keeps number keys as numbers and starts empty. `Map.get` returns `undefined` when absent.
- Java: `HashMap<Integer, Integer>` boxes every key and value. Compare the looked-up `Integer` with `null` and never with `==` against another `Integer`, which compares references and only works by accident inside the small-integer cache (-128 to 127).
- Kotlin: `HashMap<Int, Int>` boxes too (Kotlin `Int` in a generic becomes `java.lang.Integer`). `indexByValue[key]` returns `Int?`, so `?.let { return ... }` handles the hit without a `null` check. `nums.withIndex()` destructures into `(i, value)`.
