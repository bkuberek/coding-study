# Review: the facts of the recursion and dynamic programming guides

The six guides of the path "Recursion and dynamic programming: from your first recursive call to choosing states" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) are `recursion`, `backtracking`, `memoization`, `one-dimensional-tables`, `two-dimensional-tables` and `choosing-states`. They state facts about languages, libraries and the history of the method. This page lists each one with where it was checked, records which facts were left out, and checks every teaching example, trap and note against the problems the guides link, so that an independent review starts from the sources.

"Quote" means the exact text was read on that page. "Run" means an example of the guide, or a one-off program, printed it: on CPython 3.13.12, OpenJDK 21.0.2, Go 1.27.3, Node 24.18.0 and rustc 1.92.0, on macOS on AArch64. "Crossref" means the bibliographic record of the DOI was read from the Crossref API, and nothing more. A fact that could not be checked was left out of the guides.

## Python

| # | Claim | Source |
|---|-------|--------|
| P1 | `sys.getrecursionlimit()` is the maximum depth of the interpreter stack, which stops infinite recursion from overflowing the C stack and crashing Python; `sys.setrecursionlimit()` changes it, and a limit set too high can lead to a crash | Quote: [sys](https://docs.python.org/3/library/sys.html#sys.getrecursionlimit) |
| P2 | The limit is 1000 when CPython 3.13 starts. The documentation states no default, so the guide gives the number for 3.13 only | Run: `call_stack.py`, and `python3 -I -c` on 3.13.12 |
| P3 | `RecursionError` derives from `RuntimeError`, was added in 3.5, and replaced a plain `RuntimeError` | Quote: [exceptions](https://docs.python.org/3/library/exceptions.html#RecursionError); run: `call_stack.py` on a 5000-digit number |
| P4 | Since 3.12 the recursion limit applies only to Python code; built-in functions are protected by a different mechanism | Quote: [What's New in Python 3.12, `sys`](https://docs.python.org/3/whatsnew/3.12.html) |
| P5 | `functools.cache` (3.9) is `lru_cache(maxsize=None)`, smaller and faster than a bounded cache because it never evicts; `lru_cache` (3.2) defaults to `maxsize=128`; arguments must be hashable, since a dictionary holds the cache; `typed`; `f(a=1, b=2)` and `f(b=2, a=1)` may get separate entries; `cache_info()` reports hits, misses, maxsize and currsize; `cache_clear()` | Quote: [functools](https://docs.python.org/3/library/functools.html#functools.lru_cache); run: `fewest_steps.py` (`CacheInfo(hits=8, misses=10, maxsize=None, currsize=10)`), a list argument raises `TypeError: unhashable type: 'list'`, `lru_cache()` reports `maxsize` 128 |
| P6 | The cache stays coherent under concurrent updates, but the function may run more than once for the same arguments; it keeps references to arguments and results until they age out or are cleared; functions with side effects or impure functions should not be cached | Quote: functools |
| P7 | A negative index `i` is relative to the end: `len(s) + i` is substituted | Quote: [common sequence operations](https://docs.python.org/3/library/stdtypes.html#common-sequence-operations), note 3; run: `take_away.py` (the unguarded table) |
| P8 | `itertools.product` is the Cartesian product, `repeat=n` the product of `n` copies; `pairwise` returns successive overlapping pairs, added in 3.10; `combinations` returns subsequences of a given length | Quote: [itertools](https://docs.python.org/3/library/itertools.html) |
| P9 | A generator iterator suspends at each `yield`, remembering its local variables, and resumes where it left off | Quote: [glossary, generator iterator](https://docs.python.org/3/glossary.html#term-generator-iterator) |

## Java

| # | Claim | Source |
|---|-------|--------|
| J1 | `-Xss` sets the thread stack size; defaults include 1024 KB on Linux/x64 and macOS/x64, 2048 KB on Linux/AArch64 and macOS/AArch64 | Quote: [the `java` command, JDK 21](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html) |
| J2 | The `stackSize` of `Thread(ThreadGroup, Runnable, String, long)` is highly platform dependent; the virtual machine may treat it as a suggestion, round it, or ignore it completely | Quote: [Thread, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Thread.html) |
| J3 | `StackOverflowError` is thrown when an application recurses too deeply; it extends `VirtualMachineError`, an `Error` | Quote: [StackOverflowError, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/StackOverflowError.html); run: a recursion 10⁸ deep was caught as `java.lang.StackOverflowError` |
| J4 | `HashMap.computeIfAbsent` names a memoized result as a common use; the mapping function should not modify the map; the method throws `ConcurrentModificationException` on a best-effort basis when it does | Quote: [HashMap, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html); run: a recursive count memoized through `computeIfAbsent` threw `java.util.ConcurrentModificationException` |

## Go, JavaScript and Rust

| # | Claim | Source |
|---|-------|--------|
| G1 | A new goroutine gets a few kilobytes of stack, which the runtime grows and shrinks; the cost is about three cheap instructions per function call on average; hundreds of thousands of goroutines are practical | Quote: [Go FAQ, goroutines](https://go.dev/doc/faq#goroutines) |
| G2 | `debug.SetMaxStack` limits one goroutine's stack; the initial setting is 1 GB on 64-bit systems and 250 MB on 32-bit ones; a goroutine that exceeds it crashes the program | Quote: [runtime/debug](https://pkg.go.dev/runtime/debug#SetMaxStack); run: `SetMaxStack` returned 1000000000 as the previous setting, and a recursion past a 1 MiB limit printed `runtime: goroutine stack exceeds 1048576-byte limit` and `fatal error: stack overflow` |
| G3 | A recursion a million calls deep runs to the end in Go | Run: `deep_recursion.go` |
| JS1 | The messages are `RangeError: Maximum call stack size exceeded` (Chrome, and Safari with a final period) and `InternalError: too much recursion` (Firefox); a missing base case is a common cause | Quote: [MDN, too much recursion](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Errors/Too_much_recursion); run: Node 24.18.0 printed `RangeError: Maximum call stack size exceeded` |
| R1 | Spawned threads currently get 2 MiB on all Tier-1 platforms, subject to change; `Builder::stack_size` or `RUST_MIN_STACK` change it; the main thread's stack size is not determined by Rust | Quote: [std::thread, stack size](https://doc.rust-lang.org/std/thread/index.html#stack-size) |
| R2 | `1 + down(n - 1)` overflowed in a build without optimizations (`thread 'main' (…) has overflowed its stack`, `fatal runtime error: stack overflow, aborting`) and returned 2⁴⁰ for `n = 2⁴⁰` with `rustc -O` | Run: rustc 1.92.0 |

## History and names

| # | Claim | Source |
|---|-------|--------|
| H1 | Bellman's principle of optimality, quoted word for word in `choosing-states` | Quote: [RAND paper P-550](https://www.rand.org/content/dam/rand/pubs/papers/2008/P550.pdf), section 2, "The Fundamental Approach". The PDF is a scan with no text layer; its page 4 was read through OCR (tesseract) and the quoted sentence compared word for word with the page image |
| H2 | P-550 is dated 30 July 1954 and is the text of an invited address before the annual summer meeting of the American Mathematical Society at Laramie, Wyoming, 2 September 1954 | Quote: P-550, title page and summary |
| H3 | "The theory of dynamic programming", Richard Bellman, Bulletin of the AMS 60(6), 1954, pages 503 to 515 | Crossref, [10.1090/S0002-9904-1954-09848-8](https://doi.org/10.1090/S0002-9904-1954-09848-8). The AMS pages refused the request (403 and a bot check), so the guide says only that a paper of the same title appeared there, not that it is the same text |
| H4 | Bellman coined the term "dynamic programming"; his book *Dynamic Programming* was reissued by Princeton University Press in the Princeton Landmarks in Mathematics and Physics in 2010 | Quote: [Princeton University Press](https://press.princeton.edu/books/paperback/9780691146683/dynamic-programming) ("presented by the scientist who coined the term"), and its 2011 mathematics catalog; Crossref, [10.1515/9781400835386](https://doi.org/10.1515/9781400835386) |
| H5 | Donald Michie, "'Memo' Functions and Machine Learning", Nature 218 (issue 5136), April 1968, pages 19 to 22 | Crossref, [10.1038/218019a0](https://doi.org/10.1038/218019a0). The article itself redirected to a login, so the guide states only its title, journal and year |
| H6 | Solomon W. Golomb and Leonard D. Baumert, "Backtrack Programming", Journal of the ACM 12(4), October 1965, pages 516 to 524 | Crossref, [10.1145/321296.321300](https://doi.org/10.1145/321296.321300). The ACM page refused the request, so the guide states only the title, authors, journal and year |

## Algorithms and arithmetic

| # | Claim | Source |
|---|-------|--------|
| A1 | `digit_sum(4096)` is four frames deep and returns 4, 4, 13, 19 | Run: `call_stack.py` |
| A2 | Hanoi takes `2ⁿ - 1` moves (induction from `M(n) = 2·M(n - 1) + 1`), `2ⁿ⁺¹ - 1` calls counting empty towers, and `n + 1` frames | Arithmetic; run: `call_stack.py` for 1 to 10 discs |
| A3 | `T(n) = 2·T(n / 2) + O(n)` is O(n log n), since each of `log₂ n` levels does O(n) work | Arithmetic |
| A4 | The map has six valid colourings, all renamings of one; checking each choice tries 183 choices, checking complete maps checks 729; Centre first tries 84; without the undo the search finds 1 | Run: `map_colouring.py`; the six follow from a hub, a 4-cycle and a region forced to the hub's colour |
| A5 | A search tree with `n` choices of `k` options has fewer than `2kⁿ` nodes for `k ≥ 2` | Arithmetic: `(kⁿ⁺¹ - 1)/(k - 1) < kⁿ · k/(k - 1) ≤ 2kⁿ` |
| A6 | From 10, the plain recursion makes 47 calls and asks `f(3)` 5, `f(2)` 9 and `f(1)` 23 times; doubling `n` up to 160 gives 247, 1942, 23371 and 462956 calls, and 18 to 293 with a memo | Run: `fewest_steps.py` |
| A7 | The best path from 10 is `10 -> 9 -> 3 -> 1`; dividing whenever possible takes 4 steps; with one division by 3 allowed, 9 needs 3 steps and the key `n` alone answers 2; `fewest(5000)` from an empty cache raises `RecursionError`, and the loop gives 13 | Run: `fewest_steps.py`; the order in which `wrong_key` stores 3 was traced by hand from the code |
| A8 | The take-away table for 0 to 14, the game from 12, the unguarded table wrong at 2, 5, 9 and 12, and the losing positions `n % 7` in {0, 2} up to 10,000, with the ring of four slots agreeing up to 1,000 | Run: `take_away.py`; the proof for every `n` is in the guide and was checked residue by residue |
| A9 | The cheapest week costs 21 (Greek, Thai, Mexican, Greek, Thai), cheapest-each-day costs 26, all 243 sequences agree on 21, and two rows give 21 | Run: `lunch_menu.py`; Tuesday's row and the read-back worked by hand |
| A10 | The bag's best is 40 (tent and stove), greedy by value per kilogram gets 36, the divisible version 46; on 82,944 small cases the table matched brute force and greedy was wrong on 6,202 | Run: `packing.py` |
| A11 | The fractional knapsack is solved by taking the densest items first; the whole-item version is not | The exchange argument in `choosing-states`, written for this guide, and the counterexample A10 |
| A12 | On `8, 15, 3, 7`, the first player gets 22 and the second 11; taking the larger end every time gives 15 against 18; `lead[0][2] = -4` and `lead[1][3] = 11` | Run: `two_ends.py`; the first move worked by hand |

## Left out

| What | Why |
|------|-----|
| The year 1957 for Bellman's book | No page read states it: the publisher's page and catalog give only the 2010 reissue |
| The story of how Bellman chose the name | Its source is his autobiography, which was not read |
| Which languages eliminate tail calls | No official documentation read states it for Python, Java, Go or the JavaScript engines; the guide shows a Rust optimization as a run instead, and says it is not a promise |
| That 3-colouring is NP-complete, and the term "pseudo-polynomial" | No primary source was read; the guides explain the growth instead |
| That subtraction games are eventually periodic in general | Not read anywhere; the guide proves the one pattern it shows |
| Hirschberg's linear-space reconstruction | Not read; it is also close to a follow-up of `longest-common-subsequence` |
| Forward checking in backtracking | Close to the bitmask follow-up and the third hint of `n-queens` |
| The aliasing trap of `[[0] * m] * n` | It is the bug of the catalog problem `debug-grid-aliasing` |

## Teaching examples are not catalog problems

Classic teaching examples of dynamic programming are themselves catalog problems, so each example was chosen after searching the catalog's titles and the hints of the linked problems.

| Example | Guide | Avoided, and why |
|---------|-------|------------------|
| The digit sum of a number, the towers of Hanoi | recursion | Powers (`fast-power`) and binary search (`binary-search`) are catalog problems; tree recursions are close to `max-depth-binary-tree` and `employee-importance` |
| Three-colouring a map of six regions | backtracking | Subsets, orderings, sums, bracket strings, grid words and queens are the linked problems; two-colouring is `bipartite-graph`, which is not linked and is solved without search |
| Fewest operations (subtract 1, halve, divide by 3) down to 1 | memoization | Fibonacci is `climbing-stairs`; binomial coefficients and lattice paths are `unique-paths`; counting paths through a graph is close to `unique-paths` and `longest-increasing-path-matrix` |
| A take-away game with moves 1, 3 and 4 | one-dimensional-tables | Step counts are `climbing-stairs`, digit readings `decode-ways`, non-adjacent picks `house-robber`, sums of coins `coin-change` |
| A week of lunch specials, no cuisine twice in a row | two-dimensional-tables | Every two-sequence recurrence in common use (common subsequences, edit distances, interleaving, counting occurrences, pattern matching) is a linked or catalog problem, and right-and-down path costs are `unique-paths` and the unmerged `minimum-path-sum`; the guide teaches what a two-sequence cell means without any of their recurrences |
| Packing a bag, whole items, by weight and value | choosing-states | Reachable sums are `partition-equal-subset-sum`, sign assignments `target-sum`, unlimited coins `coin-change-ways` |
| Taking coins from either end of a row | choosing-states | Matrix-chain order has the recurrence of `burst-balloons`; weighted and unweighted interval scheduling are `job-scheduling-max-profit` and `non-overlapping-intervals` |

## Spoiler check

Every worked example, trap and note was read against each linked problem's statement, hints, approaches (`meta.yaml`), follow-ups, and the terms of its `solutions/explanation.md`. A guide may teach the technique a problem practises, as the hashing guides do; it may not hand over the problem's own state, recurrence or trick. The practice lines name only the question.

| Problem | Guide | What could give it away | What the guides do |
|---------|-------|-------------------------|--------------------|
| subsets | backtracking | Hint 2: branch on each value, in or out; hint 3 and follow-up 1: bits of a counter | The example branches over three colours per region; take-or-skip appears only in `choosing-states`, after subsets in the path, for items with a budget; no bits |
| permutations | backtracking | A used flag per value; swapping into place; the next ordering | Not mentioned; colours may repeat on non-neighbours, so the example needs no used flags |
| combination-sum | backtracking | Hint 1: a fixed order prevents duplicate combinations; hint 2: stay on a candidate to reuse it; hint 3: sorted candidates let the loop stop | The guide's traps leave out duplicate arrangements and sorted early exits; pruning is shown as a clash check |
| word-search | backtracking | Mark and unmark cells; count letters first; search from the rarer end | The undo is the general technique; letter counts, reversal and in-place marking are not mentioned |
| n-queens | backtracking | Row by row; sets of columns and diagonals; bits of free columns; counting only | Forward checking was cut (left out above); symmetry breaking is about renaming colours, and the statement counts mirror images as different placements |
| climbing-stairs | memoization | The recurrence `ways(n - 1) + ways(n - 2)`; two variables | No Fibonacci-shaped example; the guide answers its first follow-up only as the general idea of the guide, overlapping subproblems and a memo |
| word-break | memoization | Hint 2: the rest depends only on where it starts; hint 3: `ok[i]` over prefixes | The trap "the key describes what is left to solve" is general; no string splitting appears |
| house-robber | one-dimensional-tables | The take-or-skip recurrence over the last house; two running totals | The prefix and suffix shapes of a state are general; the example is a game with three moves |
| decode-ways | one-dimensional-tables | The relation to stairs; `ways[i]` from `i - 1` and `i - 2`; `ways[0] = 1` | Nothing about digits, pieces or an empty-prefix seed |
| coin-change | one-dimensional-tables | Hint 2: `1 + min` over coins, unreachable amounts marked; hint 3: fill amounts upwards; follow-up 1: why the largest coin first fails; follow-up 2: a shortest path over remainders | The memoization example also minimizes "1 + the best next number", and its greedy line shows dividing first is worse on 10; neither touches coins, unreachable totals or coin systems. The note that a table over a DAG is a shortest path was left out. A trap about initializing a minimum with infinity was left out |
| min-cost-tickets | one-dimensional-tables | Hint 3: the three passes; the optimal approach: a 30-day ring buffer | The ring of slots is taught on the game's window of 4, as the general space saving; passes, calendar days and the window of 30 are not mentioned |
| longest-increasing-subsequence | one-dimensional-tables | Hint 2: the best subsequence ending at `i`; hint 3: smallest tails with binary search | The table of state shapes was cut to prefix and suffix; "ending exactly at `i`" is not mentioned |
| unique-paths | two-dimensional-tables | Hint 1: right plus below; hint 2: fill from a corner; hint 3: a binomial coefficient | The guide says a right-and-down path arrives from above or the left, which is in the statement, and that row-by-row order serves it; no counts, no corners filled, no binomials anywhere in the path |
| longest-common-subsequence | two-dimensional-tables | Hint 2: `1 + L(i + 1, j + 1)` on a match, else the larger neighbour; two rows; reading one subsequence back | The guide says which three cells a two-sequence cell usually reads, never how they combine; reading back is taught on the lunch table |
| maximal-square | two-dimensional-tables | Hint 2: `1 + min` of three neighbours; hint 3: one row plus the diagonal | The three-neighbour diagram has no combining rule; the space note says two rows, not one row and a diagonal |
| edit-distance | two-dimensional-tables | Hint 2: `1 + min` of three suffix cells; the borders are the other length; returning the operations | Not mentioned; the borders trap says only that row 0 and column 0 are rarely all zeros |
| interleaving-string | two-dimensional-tables | Hint 2: `R(i, j)` from `R(i - 1, j)` and `R(i, j - 1)` with a character check | Not mentioned |
| regex-matching | two-dimensional-tables | Hint 2: skip a starred item or consume and stay; hint 3: `M(i, j)` over prefixes | Not mentioned |
| partition-equal-subset-sum | choosing-states | Hint 1: half the total; hint 2: reachable sums, item in or out; hint 3: one row updated from the largest sum down; follow-up 2: memory proportional to the target | The bag example teaches take-or-skip with values; halving, reachable sums and the one-row update direction are left out, and the complexity table gives no reduced-space row for the bag |
| coin-change-ways | choosing-states | Hint 2: `W(i + 1, a) + W(i, a - c)`, staying on a coin; hint 3: coins in the outer loop | A sentence saying that a taken item is never taken again was cut, since it points straight at staying on a coin; loop orders are not discussed |
| target-sum | choosing-states | Hint 1: the next index and the running total; hint 3: `P = (sum + target) / 2` and a one-dimensional knapsack | No signs, no running totals, no reduction |
| jump-game | choosing-states | Hint 1: reachable indexes form a prefix; hint 2: the farthest reach; hint 3: a moving goal | The greedy section proves the divisible bag and refutes the whole-item one; nothing about reach or jumps |
| job-scheduling-max-profit | choosing-states | Follow-up 1: most profitable first and ending first both fail; hints: sort by end, the last compatible job, binary search | No interval-scheduling example or counterexample appears; greedy is refuted on the bag |
| burst-balloons | choosing-states | Follow-ups: the first balloon gives dependent parts, the last does not; filling intervals by length; hint 3: the split recurrence | The interval example takes coins from the ends, with no split point; filling by length is taught as the general order of interval tables, which answers the third follow-up only in general; "cutting a piece out" was removed from the list of interval shapes |

## Not linked, checked anyway

| Problem | Note |
|---------|------|
| `debug-recursion-base-case` | The recursion guide's base-case traps are about counting down and digits; nothing about trees or leaves |
| `debug-grid-aliasing` | The list-of-lists aliasing trap was left out of the two-dimensional guide |
| `context-packer` | It packs by a fixed greedy order that its statement gives; the guide's density counterexample neither describes nor contradicts that rule |
| `stock-with-cooldown` | Left out of the path: the lunch table, a position with a choice, is close to its follow-up on a small state machine |
