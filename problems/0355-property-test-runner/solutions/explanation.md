# Property Test Runner: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| xorshift-greedy-shrink | optimal | O(R * S) per run of R values of size S; O(P * C * S) per shrink of P steps with C candidates each | O(S + C * S) | default answer; one parsed generator, one random stream and one candidate function per generator kind serve all four levels |

Here `S` is the size of a value (its number of integers, or of commands), `C` the number of candidates of a value and `P` the number of steps a shrink takes.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Random stream, parser, values | a `Random` object with the xorshift state; a parsed generator tree; values as integers and lists |
| 2 | Shrinking | a candidates function per generator kind and a greedy loop; nothing new is stored |
| 3 | Pairs, filters, discards | pairs join the value tree; the random object also counts discards against the limit |
| 4 | Stateful testing | a queue class with a `bug` field, used as model and as system under test; sequences reuse the list removals |

The early decision that pays off is to make candidates a function of the *generator* and the value, not of the value alone. At level 2 the two look the same, since an integer's candidates need its range and a list's need its minimum length and element rules. At level 3 the generator is what makes filtered candidates valid and pair candidates follow their parts, and at level 4 the same removal function shrinks command sequences.

## Approach: xorshift-greedy-shrink (One xorshift stream with greedy shrinking over generator-built candidates)

### Intuition

A property test is three small machines. A generator is a recipe that turns random numbers into a value; written in prefix form, it parses with one recursive function, and the value it draws has the same tree shape as the recipe. A runner is a loop over draws from one stream. A shrinker is hill-climbing in the space of values the generator could make: from a failing value, step to a simpler failing neighbour until there is none. The candidates define the neighbours, so each generator kind defines its own: an integer moves toward its target, a list loses chunks or simplifies an element, a pair simplifies one part, a filter keeps only the neighbours that pass it. Stateful testing is the same idea with a sequence of commands as the value and "model and system disagree" as the failing property.

### Algorithm

1. `Random.next` applies the three xorshift steps to a 32-bit state; `between(low, high)` is `low + next() mod (high - low + 1)`. A `discard` increments a counter and raises `GiveUp` above the limit.
2. Parse the generator string: split on spaces, and read `int LOW HIGH`, `list MIN MAX G`, `pair A B` or `filter NAME G` recursively from a position.
3. Draw: an `int` takes one number; a `list` takes its length, then its elements; a `pair` draws its parts in order; a `filter` draws from its inner generator until the value passes, discarding the others.
4. `check` draws values from one stream, tests the property on each and reports the first failure, the number of runs before a give-up, or a pass.
5. Candidates: for an integer, the target and then `x - d/2^k` with truncating division until the quotient is `0`; for a list, removals by chunk sizes `n, n/2, ...` at starts `0, c, 2c, ...` while the length stays at least `MIN`, then each element's candidates in place; for a pair, the first part's candidates and then the second's; for a filter, the inner candidates that pass. Drop any candidate whose text was seen, including the value's own.
6. `minimize` starts from the failing value and repeatedly moves to the first candidate on which the property fails, recording the path.
7. Level 4: a sequence is drawn with a model that decides whether `get` is allowed. A run applies each command to a fresh model and a fresh buggy queue and fails at the first different answer. Shrinking uses the list removals with a minimum of one command, then the `int 0 9` candidates of each `put` value, keeping only sequences whose `get` commands are all allowed on the model.

### Correctness

The draws follow the statement's order exactly (length before elements, first part before second, retries of a filter in place), so every language consumes the same numbers and makes the same values.

Every candidate is a value the generator could make: integer candidates lie between the target and `x`, so inside the range; list removals keep at least `MIN` elements; element candidates are valid for the element generator by induction; filter candidates pass the filter. This is what keeps a shrunk counterexample meaningful: a shrinker that left the range or broke the filter could report a "bug" for an input the code never receives.

The shrink loop ends. Give each value a measure, a non-negative integer: for an integer, `|x - target|`; for a list, its length plus the measures of its elements; for a pair, the sum of its parts' measures; for a filtered value, its inner measure. Every candidate has a smaller measure than its value: an integer candidate is strictly closer to the target (`|d - d/2^k| < |d|`), a removal takes away at least one element and its measure, and an element candidate lowers one element's measure and keeps the length. A non-negative integer cannot decrease forever, so the loop takes finitely many steps. When it stops, no candidate fails, which is the statement's definition of the result.

For level 4, a sequence fails when the system under test and the model disagree, and the model is correct by construction, so a failing sequence always exposes the planted bug. Removing commands or lowering a `put` value can make a later `get` find an empty model; such candidates are rejected before they are run, so a shrunk sequence is always a valid use of the queue.

### Complexity

- Time: O(R * S) per run of R values of size S; O(P * C * S) per shrink of P steps with C candidates each — drawing and checking a value is linear in its size; a shrink step builds up to `C` candidates of size `S` and checks each, and filters add their discarded draws, bounded by the limit.
- Space: O(S + C * S) — the current value, and the candidate list of one step, which this solution builds whole; generating candidates lazily would need only O(S).

### Trade-offs

- Building the whole candidate list is simple and makes `candidates` a direct answer; a lazy generator (a Python generator, an iterator in other languages) would stop at the first failing candidate and save the rest of the work on long lists.
- Greedy first-failing search can stop at a local minimum: `sum-lt 20` shrinks to `[5,6,1,8]` rather than `[9,9,2]`, and `repeat-dropped` keeps `put 4, put 4` because lowering one value at a time breaks the equality the bug needs. Shrinkers that try pairs of changes, or that shrink the random stream itself, find smaller results at a higher cost.
- Filtering is easy to write but wasteful and biased; a generator that builds valid values directly avoids both, which is why the discard limit exists.
- A filtered value's candidates are the inner candidates that pass. When few pass, shrinking stalls early, as `filter even` does at `14`; a generator built for even numbers (`2 * int`) would shrink further.

### Pitfalls and edge cases

- 32-bit arithmetic: the left shifts must drop the bits above 32, and the right shift must be unsigned. Draws reach `2^32 - 1`, so the remainder must be taken on the unsigned value (`h1`, `h2`).
- Halving rounds toward zero. Python's `//` and Kotlin's or Java's `Math.floorDiv` round down, which gives other candidates for negative distances and never reaches `0` from `-1` (`ex3`, `h6`).
- The target of a range that does not hold `0` is its end nearest zero (`h6`, `h9`).
- Removals never go below the minimum length, chunk starts are multiples of the chunk size, and repeated candidates are dropped by text (`h7`).
- `minimize` returns `[]` when the check passes, and a value with no failing candidate is its own result (`h8`, `h14`).
- A filter's candidates must pass it (`ex5`, `h10`, `h11`), and a list's elements shrink with the element generator, filters included.
- Discards count over the whole call, element filters included, and a run that gives up is not counted as passed (`h12`, `h13`). The limit is "above", so a limit of `0` gives up at the first discard.
- Generation offers `get` only when the model is non-empty, and a `get` draw consumes no value draw (`h16`).
- Shrinking a sequence must drop candidates whose `get` finds an empty model (`h18`): without that check, removing a `put` can produce a "counterexample" that no valid use of the queue reaches.

### Language notes

- Python integers are unbounded, so the reference masks with `0xFFFFFFFF` after each left shift. TypeScript keeps the state as a signed 32-bit number and reads it with `>>> 0`; Java and Kotlin keep an `int` and use `>>>` and `ushr`, converting to an unsigned `long` for the remainder; Go uses `uint32` and Rust `u32`, where `<<` drops the high bits.
- Values are a tagged union: Python uses `int`, `list` and `tuple`; TypeScript a union of `number`, arrays and `{first, second}` objects; Java a sealed interface with records; Kotlin a sealed class; Go a struct with a kind field; Rust an `enum`.
- Python's `//` rounds down, so the reference halves with a helper that rounds toward zero. Integer division in TypeScript (`Math.trunc`), Java, Kotlin, Go and Rust already truncates toward zero.
- Giving up is an exception in Python, Java, Kotlin and TypeScript; Go and Rust return a flag (`ok` or `Option`) through the drawing functions instead.

## Further reading

- K. Claessen and J. Hughes, "QuickCheck: a lightweight tool for random testing of Haskell programs", Proceedings of the Fifth ACM SIGPLAN International Conference on Functional Programming (ICFP 2000), pp. 268–279, [doi:10.1145/351240.351266](https://doi.org/10.1145/351240.351266): properties checked on random inputs from custom generators; conditional properties whose failed cases are discarded, with a fixed number of candidates before the tool gives up; and why such conditions skew the inputs toward short lists.
- K. Claessen and J. Hughes, "Testing monadic code with QuickCheck", ACM SIGPLAN Notices 37(12), 2002, pp. 47–59, [doi:10.1145/636517.636527](https://doi.org/10.1145/636517.636527): properties of stateful code, including model-based specifications.
- A. Zeller and R. Hildebrandt, "Simplifying and isolating failure-inducing input", IEEE Transactions on Software Engineering 28(2), 2002, pp. 183–200, [doi:10.1109/32.988498](https://doi.org/10.1109/32.988498): delta debugging, which simplifies a failing input to a 1-minimal one (no single part can be removed) that still fails.
- D. R. MacIver and A. F. Donaldson, "Test-Case Reduction via Test-Case Generation: Insights from the Hypothesis Reducer", 34th European Conference on Object-Oriented Programming (ECOOP 2020), LIPIcs 166, 13:1–13:27, [doi:10.4230/LIPIcs.ECOOP.2020.13](https://doi.org/10.4230/LIPIcs.ECOOP.2020.13): shrinking the sequence of random choices instead of the value, so that every reduced input is one the generator could have made.
- G. Marsaglia, "Xorshift RNGs", Journal of Statistical Software 8(14), 2003, [doi:10.18637/jss.v008.i14](https://doi.org/10.18637/jss.v008.i14): the xorshift generators; the shifts 13, 17 and 5 used here are one of the paper's full-period choices for 32 bits.
