# Palindrome With One Deletion: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| try-each-deletion | brute | O(n^2) | O(n) | n is small, or as a correctness oracle |
| two-pointers | optimal | O(n) | O(1) | default answer |

## Approach: try-each-deletion (Test every single deletion)

### Intuition

There are only n + 1 candidate strings: `s` itself and the n strings with one character removed. Build each one and test whether it is a palindrome. If any test succeeds, the answer is `true`.

### Algorithm

1. If `s` is a palindrome, return `true`.
2. For each index `i` from 0 to n - 1:
   1. Build `candidate = s[0 .. i-1] + s[i+1 .. n-1]`.
   2. If `candidate` is a palindrome, return `true`.
3. Return `false`.

### Correctness

The loop enumerates every way to delete exactly one character, and step 1 covers deleting none. The answer is `true` exactly when one of these n + 1 strings is a palindrome, and each is tested directly, so the method returns `true` exactly in those cases.

### Complexity

- Time: O(n^2) — up to n candidates, each built and tested in O(n). From 100 characters on, every generated input needs two deletions, so all n candidates are built and none of them is a palindrome.
- Space: O(n) — one candidate string of length n - 1 at a time.

### Trade-offs

It needs no insight beyond the definition, which makes it the oracle. At n = 3 * 10^4 it rebuilds the string tens of thousands of times: still under a second, because each rebuild is a fast memory copy, but the growth is quadratic and it would need minutes at the stated maximum of 10^5 in slower runtimes. It also ignores the strongest clue in the problem: the first mismatch tells you which two deletions are worth trying.

### Pitfalls and edge cases

- Test `s` itself before deleting anything: `deified` is `true` with zero deletions.
- A one-character string is a palindrome; deleting its only character leaves an empty string, which is also a palindrome.
- Do not stop after the first failing candidate. `cuppucu` fails when the first `c` is deleted and succeeds when the last `u` is.

### Language notes

- Python: slicing and concatenation build the candidate in C, and `candidate == candidate[::-1]` compares in C too. The work is still about 4n character copies per candidate.
- TypeScript: `slice` plus `+` creates a rope that V8 flattens on the first `charCodeAt`, which is the O(n) copy. The check compares char codes without building a reversed copy.
- Java: `substring` copies since Java 7, so each candidate costs O(n) memory and time; the check uses `charAt` without another copy.
- Kotlin: `removeRange(index, index + 1)` builds the candidate; `indices.any { ... }` stops at the first success.
- Go: `s[:index] + s[index+1:]` concatenates two substrings into a new string, so each candidate costs a real O(n) copy; the check indexes bytes, which are whole characters for lowercase ASCII.
- Rust: `[&bytes[..index], &bytes[index + 1..]].concat()` builds each candidate as a new `Vec<u8>`, an O(n) copy per deletion, and `iter().eq(iter().rev())` compares a byte sequence with its reverse without allocating the reversed copy.

## Approach: two-pointers (Branch once at the first mismatch)

### Intuition

Walk inward from both ends as in an ordinary palindrome check. While the outer characters agree, no deletion is needed for them, and deleting one of them would only shift the problem inward. At the first pair that disagrees, `s[left] != s[right]`, one of those two characters must be deleted, because no other single deletion can make these two positions match. So test the two remaining ranges, `s[left+1 .. right]` and `s[left .. right-1]`, as plain palindromes. Only one branch point exists, so the total work stays linear.

### Algorithm

1. Set `left = 0`, `right = n - 1`.
2. While `left < right`:
   1. If `s[left] == s[right]`, move both inward.
   2. Otherwise return `isPalindrome(left + 1, right) or isPalindrome(left, right - 1)`.
3. Return `true` (no mismatch: `s` is already a palindrome).

`isPalindrome(i, j)` compares `s[i]` with `s[j]`, then `s[i+1]` with `s[j-1]`, and so on, returning `false` at the first difference.

### Correctness

If the loop finds no mismatch, `s` is a palindrome and needs no deletion. Otherwise let `(l, r)` be the first mismatch. Every earlier pair matched, so `s[i] == s[n-1-i]` for all `i < l`, and `l + r == n - 1`. Suppose deleting some position `d` leaves a palindrome `t` of length n - 1, where index `i` mirrors index `n - 2 - i`.

- `l < d < r` is impossible: `s[l]` stays at index `l` of `t` and `s[r]` moves to index `r - 1 = n - 2 - l`, its mirror, but the two characters differ.
- If `d < l`: for each `i` from `d` to `l - 1`, `t` holds `s[i+1]` at index `i` and `s[n-1-i]` at its mirror, so `s[i+1] == s[n-1-i] == s[i]`. Hence `s[d] == s[d+1] == ... == s[l]`, and deleting `l` instead of `d` produces the very same string `t`.
- If `d > r`: the mirror image of the previous case shows that deleting `r` produces the same `t`.

So whenever any single deletion works, deleting `l` or deleting `r` works. Deleting `l` keeps the matched outer pairs mirrored and leaves a palindrome exactly when `s[l+1 .. r]` is one; deleting `r` does so exactly when `s[l .. r-1]` is one. The method tests precisely these two ranges.

### Complexity

- Time: O(n) — the outer loop and the two range checks together compare each position at most three times.
- Space: O(1) — a few indices; the range checks read `s` in place.

### Trade-offs

Linear time and constant memory, with one branch. It is the expected interview answer and a good example of greedy reasoning on top of two pointers: the first mismatch forces the choice down to two options. Generalizing to `k` deletions turns the single branch into a recursion with up to 2^k paths, or a DP over the longest palindromic subsequence (O(n^2)); mention this only if asked.

### Pitfalls and edge cases

- Try both deletions at the first mismatch. Testing only the left one fails `aab` and `ababbabab`; testing only the right one fails `baa` and `ababaabab`.
- After branching, the inner checks must not allow another deletion; a recursive version that passes a "deletions left" counter must start the branches with zero.
- Return `true` when the loop ends without a mismatch; that covers the empty-inner-range and already-palindrome cases.
- Slicing in the range check (`s[l+1:r+1] == reversed`) is correct but allocates O(n); the in-place loop keeps O(1) space.

### Language notes

- Python: the helper takes the string and two indices; plain `while` loops avoid the copies that slicing would make. In CPython the slicing version is faster in practice despite the memory.
- TypeScript: `charCodeAt` comparisons avoid creating one-character strings; `s[left] !== s[right]` also works and is slightly slower.
- Java: a `private static` helper with `charAt` keeps everything in place; `s.charAt(left++)` advances while reading.
- Kotlin: function parameters are read-only, so the helper copies `from` and `to` into `var`s before moving them.
- Go: the helper takes a start and an end index into the same string, so the two retries after the first mismatch copy nothing; substrings in Go would share the backing bytes anyway, but indexes avoid even the slice headers.
- Rust: the helper takes a `&[u8]` subslice, a borrowed view of the same bytes, so the two retries copy nothing. Both pointers use the half-open form `left + 1 < right`, which stays clear of `usize` underflow.
