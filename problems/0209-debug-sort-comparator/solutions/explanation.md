# Debug: Leaderboard Comparator: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| key-ordering | optimal | O(n log n) | O(n) | default answer: compare (score descending, name ascending) exactly, with no arithmetic |

## Approach: key-ordering (Lexicographic key comparison)

### Intuition

The comparator has two bugs.

1. **A tie-break that breaks transitivity.** `SCORE_EPSILON = 1` is a leftover from when scores were decimal averages and "equal" had to absorb rounding noise. On integer points it declares 41 and 42 a tie and orders them by name, so `kim` (41) lands above `lee` (42). Worse, "within 1 point" is not transitive: 3 ties with 4 and 4 ties with 5, but 3 does not tie with 5. A comparator must induce a consistent total order. This one is internally contradictory, so the result depends on the sorting algorithm and on the input order. That explains "the order changes depending on submission order". Java's TimSort sometimes detects the contradiction and throws `IllegalArgumentException: Comparison method violates its general contract!`, but only on larger inputs.
2. **A subtraction comparator that overflows.** `scores[b] - scores[a]` is a common shortcut for "compare descending". In Java and Kotlin it is 32-bit `int` arithmetic: `2000000000 - (-2000000000)` wraps to `-294967296`, so the comparator says the jackpot winner ranks *lower*. `Math.abs` on the overflowed difference is wrong too, and `abs(Integer.MIN_VALUE)` is negative. Python integers do not overflow, and TypeScript numbers are doubles that hold every difference of two 32-bit values exactly, so only the JVM services inverted the podium.

The fix compares the keys instead of doing arithmetic on them: score with an exact three-way compare (`Integer.compare`, `compareByDescending`, or a key tuple), then name.

### Debugging approach

1. **Reproduce small.** Two players settle the first complaint: `kim` 41 and `lee` 42 come out as `[kim, lee]`. One wrong pair is enough to show the comparator is wrong, before thinking about sort algorithms.
2. **Test the comparator on its own, not the sort.** Call it on pairs and check the contract by brute force over a few values: antisymmetry, `sign(cmp(a, b)) == -sign(cmp(b, a))`, and transitivity: `cmp(a, b) <= 0` and `cmp(b, c) <= 0` imply `cmp(a, c) <= 0`. Scores 3, 4 and 5 with names `a`, `b` and `c` violate transitivity immediately.
3. **Read the history.** The ticket says scores were decimals until this season. A constant named `EPSILON` in integer code is a strong lead.
4. **Second symptom, second hypothesis.** "Only the JVM services, only with huge scores" points at integer width. Evaluate the comparator's arithmetic in 32 bits for the event's extremes: the sign flips.
5. **Check the half-fixes.** Removing the epsilon alone still fails `h6` and `h7` on the JVM, because of the overflow. Replacing only the subtraction leaves the near-tie bug in every language.

### Algorithm

1. Build the list of player indices (or `(name, score)` pairs).
2. Sort them with an order that compares, in sequence:
   1. scores, descending, with an exact comparison (never subtraction);
   2. names, ascending, for exactly equal scores.
3. Return the names in sorted order.

### Correctness

The key `(-score, name)` compared lexicographically is a strict total order on the players. Each component is compared with an exact total order, integers by value and strings by code units, and lexicographic order over total orders is total and transitive. Names are distinct, so no two players compare equal and the sorted order is unique. A correct sort with a valid total order returns that unique order, which is the leaderboard order by definition. No arithmetic is performed on scores, so nothing can overflow.

### Complexity

- Time: O(n log n) — the sort does O(n log n) comparisons, each O(1) for scores plus O(name length) for the rare name comparison, and names are at most 10 characters.
- Space: O(n) — the index array or key tuples, plus the sort's buffer.

### Trade-offs

A key-based sort, `key=lambda p: (-p[1], p[0])` in Python or `compareByDescending { }.thenBy { }` in Kotlin, removes the hand-written comparator entirely and cannot violate the contract. Python's key sort also computes each key once instead of once per comparison. A hand-written comparator is still fine when it delegates each field to an exact compare (`Integer.compare`, `String.compareTo`). Sorting indices instead of building record objects keeps the input arrays untouched, at the cost of one level of indirection.

### Pitfalls and edge cases

- The general trap: a comparator must be a consistent total order. "Close enough means equal" (epsilon or tolerance rules) is never transitive, and subtraction is only safe when the difference cannot overflow.
- An intransitive comparator does not always fail. `h8` (5, 4, 3 with names `a`, `b`, `c`) passes by luck, because the name order happens to agree with the score order.
- `Math.abs(Integer.MIN_VALUE)` is `Integer.MIN_VALUE`, which is negative. Any `abs(a - b) <= tolerance` check on 32-bit values is broken at the extremes.
- The shipped tie-break returns `1` for equal names, so `cmp(x, x) != 0`. Names are distinct here, but in general a comparator must return `0` for equal keys.
- For decimal scores, compare exactly too, and round once when the score is computed, not inside the comparator.

### Prevention

- Reject subtraction comparators in review, and build comparators from keys: `Comparator.comparingInt(...)` and `thenComparing(...)`. Static analyzers catch related mistakes, for example Error Prone's `ComparisonContractViolated` and SpotBugs' `RV_NEGATING_RESULT_OF_COMPARETO`, but none of them proves a comparator transitive, so tests still matter.
- Unit test the comparator itself with a property test: random triples must satisfy antisymmetry and transitivity, including extreme values such as `Integer.MIN_VALUE`, `0` and `Integer.MAX_VALUE`.
- When a data type changes (decimals to integers), search for every tolerance or epsilon that depended on the old type.
- Test leaderboards with adjacent integer scores (gap of 1) and with names in the opposite order to the scores. Ties in name order alone do not exercise the bug.

### Language notes

- Python: `sort` with `key=` is the idiom; `functools.cmp_to_key` exists for porting old comparators and is slower. `-score` cannot overflow. The sort is stable, so sorting twice (by name, then by score descending) also works.
- TypeScript: `Array.prototype.sort` needs a consistent negative, zero or positive result. Numbers subtract exactly in this range, so `b.score - a.score` would be safe here, but the reference compares explicitly so that the code is correct for any numeric range. `localeCompare` would use locale collation, not the code-unit order the spec asks for.
- Java: `Integer.compare(scores[b], scores[a])` is the overflow-safe descending compare, and `thenComparing` chains the tie-break. `Comparator.comparingInt(...).reversed()` also works but reverses every component chained before it, a frequent source of surprise. `Arrays.sort` on objects is a stable TimSort that may throw on contract violations.
- Kotlin: `compareByDescending<Int> { scores[it] }.thenBy { names[it] }` builds the comparator from keys, with no arithmetic. `sortedWith` is stable. `kotlin.math.abs(Int.MIN_VALUE)` is negative, exactly as in Java.
