# Decode Ways: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(n) | O(n) | you reason from the front: "what can the first piece be?" |
| tabulation | intermediate | O(n) | O(n) | you want the prefix counts explicit before optimizing |
| two-variables | optimal | O(n) | O(1) | default answer |

A reading splits `s` into pieces of one digit (`1` to `9`) or two digits (`10` to `26`). Count readings by their last piece: the readings of the first `i` digits are the readings of the first `i - 1` digits followed by digit `i - 1` alone, when that digit is not `0`, plus the readings of the first `i - 2` digits followed by the last two digits, when they form a number from 10 to 26. The two groups cannot overlap because their last pieces have different lengths.

This is climbing stairs with gates: a one-step move is allowed only onto a non-zero digit, a two-step move only across a valid pair. The naive recursion over the first piece, without memory, branches twice per position and is exponential on strings like `"1111..."`, where it makes about 1.618 to the power `n` calls; it is the first step of the progression and is not a separate reference here.

## Approach: memoization (Top-down count of suffix decodings)

### Intuition

Let `waysFrom(i)` be the number of readings of the suffix starting at `i`. The first piece is `s[i]` alone (if it is not `0`) or `s[i..i+1]` (if it is 10 to 26), and the rest of the reading is a reading of the remaining suffix. Each suffix is asked about many times by the naive recursion; caching by `i` evaluates each once.

### Algorithm

1. `waysFrom(n) = 1`: the empty suffix has one (empty) reading.
2. If `s[i] == '0'`, return 0: no piece starts with a zero.
3. Otherwise `count = waysFrom(i + 1)`, plus `waysFrom(i + 2)` when `i + 1 < n` and `s[i..i+1] <= 26`; cache and return it.
4. Return `waysFrom(0)`.

### Correctness

By induction from the end. A reading of `s[i..]` is determined by its first piece and a reading of what follows; the conditions in steps 2 and 3 admit exactly the first pieces that are letters, and distinct first pieces give distinct readings. A suffix starting with `0` has no valid first piece. The cache stores only values the recursion would compute.

### Complexity

- Time: O(n) — each of the `n` suffixes is evaluated once with O(1) work.
- Space: O(n) — the cache and a recursion up to `n` frames deep.

### Trade-offs

Derives naturally from "what is the first letter?", which many people find easiest. The recursion depth equals the length of `s`; with up to 2000 digits that is fine, but it is the reason to prefer the iterative versions for longer inputs.

### Pitfalls and edge cases

- Return 0 for a suffix that starts with `0` before looking at pairs: `"06"` is not a letter even though 6 is.
- With `s[i]` known to be non-zero, the pair is at least 10, so checking `<= 26` suffices; without that guard, `"05"` would wrongly count as a letter.
- The constraints bound the counts of prefixes, not suffixes. A suffix such as the run of 1s in `"30" + "1" * 60` has far more than 2^31 readings, but the top-down recursion never evaluates it here (the `0` returns before recursing), and in general a count that does not contribute to the answer can be wrong without harm, because every count that does contribute is at most the answer.

### Language notes

- Python: `functools.cache` on the nested function; slicing two characters and `int` reads the pair.
- TypeScript: `Number(s.slice(i, i + 2))` parses the pair; a memo of -1 marks unknown entries, since 0 is a real count.
- Java: arithmetic on `charAt(i) - '0'` avoids building substrings.
- Kotlin: `substring(...).toInt()` reads the pair; a local `fun` captures the memo.
- Go: indexing a string yields a `byte`, so `int(s[start]-'0')*10 + int(s[start+1]-'0')` reads a pair without a substring, and the memo is filled with -1 because 0 is a real count. The recursive closure is declared with `var waysFrom func(start int) int` first.
- Rust: the digits are borrowed as `s.as_bytes()`, and the pair is computed in `u8` arithmetic (at most 99), tested with `(10..=26).contains(&pair)`. The recursion is a free function because a closure cannot call itself, with the memo passed as `&mut [i32]` and filled with -1.

## Approach: tabulation (Bottom-up table of prefix decodings)

### Intuition

Turn the recurrence around and grow the string from the left: the number of readings of each prefix depends only on the two prefixes just shorter than it, so computing prefixes in order of length always has both values ready.

### Algorithm

1. Create `ways` of length `n + 1` with `ways[0] = 1`.
2. For `i` from 1 to `n`: if `s[i - 1] != '0'`, add `ways[i - 1]`; if `i >= 2` and the pair `s[i - 2..i - 1]` is between 10 and 26, add `ways[i - 2]`.
3. Return `ways[n]`.

### Correctness

Invariant: before step `i`, `ways[k]` is the number of readings of the first `k` digits for every `k < i`. A reading of the first `i` digits ends with a one-digit piece (allowed iff `s[i - 1] != '0'`) preceded by a reading of the first `i - 1` digits, or with a two-digit piece (allowed iff it is 10 to 26) preceded by a reading of the first `i - 2`. These cases are disjoint and exhaustive, so the sum in step 2 is correct. `ways[0] = 1` makes a string that is a single valid piece count once.

### Complexity

- Time: O(n) — two constant-time checks per position.
- Space: O(n) — the table of `n + 1` counts.

### Trade-offs

Iterative, with no stack depth issue, and the table shows how zeros wipe out counts, which makes it the oracle. It keeps all `n + 1` counts although each is read only twice.

### Pitfalls and edge cases

- The pair must be at least 10, which rules out a leading zero (`"01"` to `"09"`), and at most 26 (`"27"` is not a letter).
- `ways[0] = 1` is not "the empty string has a meaning"; it is the neutral starting value that lets the first piece count as one reading.
- A string that starts with `0` gets `ways[1] = 0`, and the answer is 0 no matter what follows.

### Language notes

- Python and Kotlin: slicing two characters and parsing them as an integer keeps the check readable.
- TypeScript: `Number("05")` is 5, so the `>= 10` test is what rejects a leading zero.
- Java: the pair is built from two `charAt` values; `int[]` starts at 0, so only `ways[0]` needs setting.
- Go: the table is a zero-filled `[]int`, only `ways[0]` is set, and each pair is read with byte arithmetic. The `if pair := ...; pair >= 10 && pair <= 26` form scopes the pair to the check.
- Rust: `vec![0; n + 1]` is zero-filled and the digits are read from `as_bytes()`, so there are no substrings or parsing. `(10..=26).contains(&pair)` is the range test, and the counts fit in `i32` by the constraints, with overflow checks on as a backstop.

## Approach: two-variables (Rolling counts of the last two prefixes)

### Intuition

Each prefix count reads only the two counts before it. Keeping those two, `oneBack` for the prefix ending just before the current digit and `twoBack` for the one before that, replaces the table.

### Algorithm

1. Set `twoBack = 0` and `oneBack = 1` (the empty prefix).
2. For each index `i`: `current = oneBack` if `s[i] != '0'`, else 0; if `i > 0` and the pair `s[i - 1..i]` is between 10 and 26, add `twoBack`. Then `twoBack = oneBack` and `oneBack = current`.
3. Return `oneBack`.

### Correctness

Invariant: before digit `i`, `oneBack = ways[i]` and `twoBack = ways[i - 1]` (with `ways[-1]` taken as 0, which never matters because no pair ends at index 0). The loop body computes `ways[i + 1]` with the tabulation recurrence and shifts the pair, restoring the invariant.

### Complexity

- Time: O(n) — one pass with constant work per digit.
- Space: O(1) — two counts and a little scratch.

### Trade-offs

The expected final answer. It is easy to get the shifting wrong, so derive the table version first and then roll it.

### Pitfalls and edge cases

- Compute `current` before shifting; assigning `twoBack = oneBack` first loses the value the pair needs.
- Once both counts are 0 (for example after `"00"` or `"30"`), every later count stays 0. An early return is a valid micro-optimization but not needed.
- Counts here stay below 2^31 for every prefix by the constraints, so 32-bit integers are enough in Java and Kotlin.

### Language notes

- Python: the previous digit is remembered as a string, and `int(previous + digit)` forms the pair.
- TypeScript: `charCodeAt(i) - 48` turns a digit character into its value without allocating substrings.
- Java: the same arithmetic with `charAt(i) - '0'`.
- Kotlin: `Char.digitToInt()` converts a digit, and `in 10..26` checks the pair's range.
- Go: a plain index replaces Python's `previous_digit` string, and `twoBack, oneBack = oneBack, current` updates the pair in one statement.
- Rust: `digits[i - 1]` replaces the remembered previous digit, guarded by `i > 0`, and `(two_back, one_back) = (one_back, current)` is a destructuring assignment (Rust 1.59 and newer).
