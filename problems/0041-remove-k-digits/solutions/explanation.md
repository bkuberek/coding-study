# Remove K Digits: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| repeated-peak-removal | brute | O(n * k) | O(n) | short numbers, or as a correctness oracle |
| monotonic-stack | optimal | O(n) | O(n) | default answer |

Both approaches apply the same greedy rule: to make a number smaller with one deletion, delete the first digit that is larger than the digit after it (a "peak"), or the last digit if the digits never decrease. The brute force applies the rule k times, rescanning from the start; the stack applies all k deletions in one pass. Trying every subset of k digits would also work, but it costs C(n, k) and is useless beyond a dozen digits.

## Approach: repeated-peak-removal (Remove the first peak digit k times)

### Intuition

Comparing two numbers of the same length, the first differing digit decides. With one deletion, everything before the deleted digit stays put and everything after it shifts left by one. Deleting at the first position where the next digit is smaller makes that position smaller and leaves the prefix untouched, which is the best possible. Repeat k times.

### Algorithm

1. Repeat k times:
   1. Find the first index `i` with `digits[i] > digits[i + 1]`; if there is none, take the last index.
   2. Delete `digits[i]`.
2. Strip leading zeros; return `"0"` if nothing is left.

### Correctness

One deletion: let `i` be the first peak. Deleting any `j < i` replaces `digits[j]` by `digits[j + 1] >= digits[j]` at position `j` and leaves the prefix before `j` unchanged, so it is never smaller than deleting `i`, which keeps positions up to `i - 1` and lowers position `i` to `digits[i + 1] < digits[i]`. Deleting `j > i` keeps `digits[i]` at position `i`, which is worse. With no peak, the digits never decrease and deleting the last one is best by the same argument.

k deletions: the optimal result after k deletions can be reached by first making an optimal single deletion (an exchange argument: the first peak is deleted in some optimal solution), so applying the rule greedily k times is optimal. Leading zeros do not change the value, so stripping them at the end is safe.

### Complexity

- Time: O(n * k) — each of the k rounds scans from the start to the first peak and shifts the tail of the array, both O(n).
- Space: O(n) — a mutable copy of the digits.

### Trade-offs

It states the greedy rule directly, which makes it a good oracle and a natural first answer in an interview. With a long non-decreasing prefix every rescan walks the whole prefix again; the stack never looks at a digit twice.

### Pitfalls and edge cases

- Use `<=` while walking to the peak: equal digits are not a peak.
- If `k` equals the length, everything is deleted and the answer is `"0"`.
- Strip leading zeros only at the end; stripping them in between would change which digits count as deleted.

### Language notes

- Python: `del digits[peak]` on a list of characters; `"".join(...).lstrip("0") or "0"` handles the empty result.
- TypeScript: `splice(peak, 1)` removes one element; a regular expression strips the zeros.
- Java: `StringBuilder.deleteCharAt` shifts the tail; the zeros are skipped by index and `substring` copies the rest.
- Kotlin: the same `StringBuilder`, with `deleteAt`, `trimStart('0')` and `ifEmpty { "0" }`.
- Go: the digits are a `[]byte`, and `slices.Delete(digits, peak, peak+1)` removes one in place by shifting the tail. `for range k` (Go 1.22 and newer) repeats the removal. `strings.TrimLeft(s, "0")` takes a set of characters and strips every leading zero; `TrimPrefix` would strip only one.
- Rust: the digits are a `Vec<char>` and `Vec::remove` shifts the tail. The leading zeros go with `skip_while(|&digit| digit == '0')` while the string is collected, and an empty result becomes `"0"`.

## Approach: monotonic-stack (Keep a non-decreasing stack of digits)

### Intuition

Read the digits left to right and keep the ones not deleted yet on a stack. A new digit that is smaller than the top makes the top a peak: deleting the top is exactly what the greedy rule would do next. So pop while deletions remain and the top is larger than the new digit, then push the new digit. The kept digits therefore never decrease. Deletions left over at the end go to the last digits, which is the rule's "no peak" case.

### Algorithm

1. For each digit `d` of `num`:
   1. While deletions remain, the stack is not empty and its top is greater than `d`, pop and use one deletion.
   2. Push `d`.
2. Remove the remaining deletions from the top of the stack.
3. Strip leading zeros; return `"0"` if nothing is left.

### Correctness

Invariant: after reading a prefix, the stack is the result of applying the first-peak rule as many times as deletions were used, restricted to that prefix, and it never decreases from bottom to top. A peak can only appear where a new digit is smaller than the one before it, and the earliest such position is at the top of the stack, so popping the top is the greedy deletion; popping repeats while the new top is still a peak. Once the new digit is pushed, the stack is non-decreasing again, and digits further left can never become peaks later, because the digit after them is already final. At the end the stack has no peak, so each leftover deletion removes the last digit, as the rule says.

### Complexity

- Time: O(n) — every digit is pushed once and popped at most once.
- Space: O(n) — the stack holds up to n digits.

### Trade-offs

The standard answer: one pass, simple code, and the same skeleton solves "smallest subsequence of length m" problems. It is slightly harder to justify than the brute force, because the deletions happen in a different order (but on the same positions).

### Pitfalls and edge cases

- Pop on a strictly larger top: popping equal digits wastes deletions.
- Do not forget the leftover deletions after the loop (ascending input such as `12345` uses none inside the loop).
- Leading zeros: the stack may start with zeros once the digits before them were deleted; strip them before returning, but do not count them as deletions.

### Language notes

- Python: a list of characters as the stack; slicing drops the leftover deletions.
- TypeScript: an array of one-character strings compared with `>`, which compares digit characters correctly; `kept.length -= remaining` truncates in place.
- Java: a `StringBuilder` is the stack (`charAt`, `setLength`, `append`), so no boxing.
- Kotlin: the same `StringBuilder` with `last()` and `setLength`.
- Go: a `[]byte` is the stack, and comparing two bytes with `>` orders the digit characters correctly. `kept[:len(kept)-remaining]` drops the leftover deletions without copying.
- Rust: a `Vec<char>` is the stack; `char` comparison orders `'0'` to `'9'` correctly, and `Vec::truncate` drops the leftover deletions. `kept.last().is_some_and(|&last| last > digit)` reads the top without popping.
