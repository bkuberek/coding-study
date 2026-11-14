# All Grid Paths: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| filter-sequences | brute | O(n * 4^n) | O(sqrt(n) * 4^n) | as a cross-check, or to show how much work the pruning saves |
| build-path | optimal | O(sqrt(n) * 4^n) | O(sqrt(n) * 4^n) | default answer: every move it writes belongs to a finished path |

This problem differs from counting the paths. The count is `C(2n - 2, n - 1)`, which grows like `4^n / sqrt(n)`, and a table or a binomial coefficient finds it without ever seeing a path. Here every path is part of the output and each one has `2n - 2` characters, so the output alone has size Θ(sqrt(n) * 4^n): at `n = 10` that is 48,620 strings of 18 characters. No algorithm can beat the size of what it must write, which is why the optimal approach is optimal even though its time is exponential, and why `n` is capped at 10.

The ladder of this problem cannot tell the two approaches apart by their growth. Both are exponential in `n`, and what separates them is the constant: the brute force looks at `4^(n - 1)` sequences to keep `C(2n - 2, n - 1)` of them, about `sqrt(pi * n)` times as many as it keeps, while the optimal approach never leaves the set of valid prefixes. The declared classes are therefore the same `2^n` for both, and the exact bounds are in the table.

## Approach: filter-sequences (Write every sequence of right and down moves, keep the ones with n - 1 of each)

### Intuition

A route is a sequence of `2n - 2` moves, each `D` or `R`, so it is one of the `2^(2n - 2)` such sequences. Write all of them and keep the ones that end in the bottom-right corner. A sequence ends there exactly when it holds `n - 1` rights, since then it holds `n - 1` downs too and never needs to leave the grid: no prefix can overshoot, because a sequence with exactly `n - 1` of each letter never has more than `n - 1` of either.

### Algorithm

1. Let `steps = 2n - 2`. For every number `pattern` from 0 to `2^steps - 1` in increasing order:
   1. Write its `steps` bits from the most significant bit down, with `D` for 0 and `R` for 1.
   2. Count the `R` letters in the text.
   3. If the count is `n - 1`, append the text to the result.
2. Return the result.

### Correctness

Every string of `steps` letters from `D` and `R` is written once, so every string with `n - 1` of each letter is considered, and only those are kept. Each of them is a route from the top-left to the bottom-right corner, and each route is such a string. Counting up from 0 reads the bit patterns in increasing numeric order. With the most significant bit as the first letter and `D < R`, that is lexicographic order, so the result needs no sorting.

### Complexity

- Time: O(n * 4^n) — `2^(2n - 2)` sequences, each written and counted in O(n).
- Space: O(sqrt(n) * 4^n) — the kept strings, `C(2n - 2, n - 1)` of length `2n - 2`; the sequence being tested needs only O(n).

### Trade-offs

Correct by inspection and the natural first idea, which is why it is the oracle. It does about `sqrt(pi * n)` times more work than there are paths, and at `n = 10` it writes 262,144 sequences to keep 48,620. It shows the cost of generating first and filtering later: the optimal approach below uses the same two counts, but to decide before writing a letter.

### Pitfalls and edge cases

- `n = 1` has zero moves and `2^0 = 1` sequence, the empty one, which has zero rights and is kept. The answer is a list holding the empty string, not an empty list.
- Reading the bits from the least significant end writes every string reversed, which lists the paths in the wrong order.
- The test must be on the count of `R` (or `D`), not on a text comparison: a sequence like `RRDD` has the same counts as `DDRR`.

### Language notes

- Python: `format(pattern | (1 << steps), "b")[1:]` gives exactly `steps` digits, leading zeros included, also when `steps` is 0; `str.replace` maps the digits to letters and `str.count` counts the rights, all in C.
- TypeScript: bit operators work on 32-bit integers, which is enough since `steps` is at most 18; the letters are appended one by one.
- Java: the loop builds a `StringBuilder` per pattern and counts the rights as it appends.
- Kotlin: the same loop with `shl`, `shr` and `and`; `if` is an expression, so the letter choice is a single `append`.
- Go: one `[]byte` buffer is reused for every pattern, and `string(moves)` copies it only for the kept ones.
- Rust: `u32` holds the pattern, `1u32 << steps` is at most `2^18`, and `matches('R').count()` counts the rights in the built `String`.

## Approach: build-path (Extend one path builder with a move only while the corner is still reachable)

### Intuition

Build a route move by move in one shared buffer. A `D` is allowed while fewer than `n - 1` downs have been made, and an `R` while fewer than `n - 1` rights have been made. Every prefix built this way can be finished, since the missing moves are just the remaining downs and rights in any order, so each branch of the search ends in a route and nothing is thrown away. Trying `D` before `R` at every step visits the routes in dictionary order.

### Algorithm

1. Keep a shared list `moves` and a result list `paths`. Let `last = n - 1`.
2. `extend(downs, rights)`:
   1. If `downs == last` and `rights == last`, append a copy of `moves` as a string to `paths` and return.
   2. If `downs < last`: push `D`, call `extend(downs + 1, rights)`, pop.
   3. If `rights < last`: push `R`, call `extend(downs, rights + 1)`, pop.
3. Call `extend(0, 0)` and return `paths`.

### Correctness

By induction on the number of moves left, `extend(downs, rights)` appends exactly the completions of the current prefix: strings of `last - downs` downs and `last - rights` rights, each once. With no moves left, the prefix is the route itself and is appended. Otherwise every completion starts with `D` or with `R`; the first branch is taken only while a `D` is still needed, the second only while an `R` is, and each branch lists the completions that start with its letter. The `D` branch runs first, so within one prefix all completions that start with `D` come before those that start with `R`, which is lexicographic order. The pop after each call restores `moves` for the next branch.

### Complexity

- Time: O(sqrt(n) * 4^n) — the search tree has no dead ends, so the number of calls is at most the number of paths times the path length, and copying each path into the result costs O(n). With `C(2n - 2, n - 1)` of about `4^n / sqrt(n)` paths, the total is of the order of `sqrt(n) * 4^n`, the same as the size of the output.
- Space: O(sqrt(n) * 4^n) — the result; the recursion and the builder need only O(n).

### Trade-offs

Optimal in the only sense that applies: it does work proportional to the output and never builds a string that is not a route. It is the same idea as Permutations and Generate Parentheses, with a different rule for when a move is allowed. Counting the routes instead would drop the exponential cost to a binomial coefficient, which is the point of the related problem Unique Paths: say which question the caller asks before choosing the algorithm.

### Pitfalls and edge cases

- Append a copy of the builder, not the builder itself. In Python, `paths.append(moves)` stores the same list `n` times and ends with every entry empty after the pops; joining or `toString` makes the copy.
- Pop after the recursive call. Without it the builder keeps growing and the next branch starts from the wrong prefix.
- `n = 1`: `last = 0`, so the first call is already complete and the result is the empty string, one path of zero moves.
- Trying `R` before `D` gives the right set in the reverse order within every prefix, and the checker rejects it.
- Using `n` instead of `n - 1` as the limit adds a step to every path: a grid with `n` cells per side needs only `n - 1` moves of each kind.

### Language notes

- Python: a nested function shares `moves` and `paths` through the closure; `"".join(moves)` makes the copy.
- TypeScript: an arrow function inside the exported one plays the same role, with `moves.join("")`.
- Java: a private method takes the `StringBuilder` and the list as arguments; `deleteCharAt(length - 1)` undoes the last move and `toString()` copies.
- Kotlin: a local `fun` captures `moves` and `paths`; `StringBuilder.deleteCharAt` undoes the last move.
- Go: a closure over a `[]byte` buffer; `moves[:len(moves)-1]` undoes the append and `string(moves)` copies the bytes.
- Rust: the recursion is a free function that takes `&mut String` and `&mut Vec<String>`; `pop` undoes the push and `clone` copies.
