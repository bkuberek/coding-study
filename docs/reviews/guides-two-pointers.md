# Review: the facts of the two-pointer guides

The five guides of the path "Arrays: two pointers and sliding windows" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about Python and Go, and correctness arguments of their own. This page lists each fact with where it was checked, and each argument with where it is proved and tested, so that a later review starts from the sources, and records what the first independent accuracy review changed.

"Quote" means the exact text was read on that page. "Run" means an example of the guide printed it, on CPython 3.13.12. A fact that could not be checked was left out of the guides.

## Python

| # | Claim | Source |
|---|-------|--------|
| P1 | `list.reverse()` reverses in place for economy of space, and returns `None` to remind you that it works by side effect | Quote: [stdtypes, mutable sequence types](https://docs.python.org/3/library/stdtypes.html#mutable-sequence-types); run: `two_pointers.py` |
| P2 | Strings are immutable sequences of Unicode code points | Quote: [stdtypes, `str`](https://docs.python.org/3/library/stdtypes.html#text-sequence-type-str) |
| P3 | Every slice operation returns a new list | Quote: [tutorial, lists](https://docs.python.org/3/tutorial/introduction.html#lists) |
| P4 | `del s[i:j]` is the same as `s[i:j] = []`; `s[i:j] = t` replaces the slice with the contents of the iterable `t` | Quote: stdtypes, mutable sequence types |
| P5 | Code that changes a collection while looping over it can be tricky to get right; loop over a copy or build a new collection | Quote: [tutorial, `for` statements](https://docs.python.org/3/tutorial/controlflow.html#for-statements) |
| P6 | Removing from a list while looping over it skips a value: `[7, -2, -1, 5]` keeps `-1` | Run: `compaction.py`. The language reference no longer describes this, so the guide says "on CPython 3.13" |
| P7 | A `deque` with `maxlen`, once full, discards items from the opposite end as new ones are added | Quote: [collections, `deque`](https://docs.python.org/3/library/collections.html#collections.deque); run: `fixed_windows.py` |
| P8 | `Counter` returns a zero count for missing items; setting a count to zero does not remove the element, `del` does | Quote: [collections, `Counter`](https://docs.python.org/3/library/collections.html#collections.Counter) |
| P9 | `itertools.pairwise` yields overlapping pairs, added in 3.10; `itertools.batched` yields tuples of `n`, the last possibly shorter, added in 3.12; the `sliding_window` recipe is built on `deque(..., maxlen=n)` | Quote: [itertools](https://docs.python.org/3/library/itertools.html); run: `fixed_windows.py` |
| P10 | `math.fsum` returns an accurate floating-point sum by tracking partial sums | Quote: [math, `fsum`](https://docs.python.org/3/library/math.html#math.fsum); run: a rolling sum gives 1.0 where `fsum` gives 2.0 |
| P11 | The search step of `bisect` is O(log n) | Quote: [bisect](https://docs.python.org/3/library/bisect.html) |
| P12 | Tuples and lists compare lexicographically, ordered by their first unequal elements | Quote: [value comparisons](https://docs.python.org/3/reference/expressions.html#value-comparisons); run: `sorted_pairs.py` |
| P13 | Left out: a worst-case bound for `sorted` and `list.sort`. The sorting HOWTO and CPython's `Objects/listsort.txt` state none, so the guides cite Go's `sort.Sort` for O(n log n) | |

## Go

| # | Claim | Source |
|---|-------|--------|
| G1 | The `slices` package is new in Go 1.21 | Quote: [Go 1.21 release notes](https://go.dev/doc/go1.21#slices) |
| G2 | `slices.DeleteFunc` removes in place the elements for which the function returns true and returns the modified slice; `slices.Compact` replaces consecutive runs of equal elements with a single copy | Quote: [slices](https://pkg.go.dev/slices) |
| G3 | Since Go 1.22, the functions that shrink a slice (`Delete`, `DeleteFunc`, `Compact`, `CompactFunc`, `Replace`) zero the elements between the new length and the old one | Quote: [Go 1.22 release notes](https://go.dev/doc/go1.22#minor_library_changes); the `slices` entry has no anchor of its own |
| G4 | `sort.Sort` makes O(n·log(n)) calls to `Less` and `Swap`, and is not guaranteed to be stable | Quote: [sort](https://pkg.go.dev/sort#Sort) |

## Correctness arguments and arithmetic

These are the guides' own arguments, written out as proofs in the guide that states them. No outside source is cited for them; the runs check them on every small input.

| # | Claim | Where proved, and how checked |
|---|-------|-------------------------------|
| A1 | A two-pointer loop in which every step moves a pointer forward ends after at most `2n` steps; with opposite ends, the gap `j - i` shrinks by at least 1 per step | two-pointers, Complexity |
| A2 | Reversal: every position before `i` and after `j` holds its final value; merging takes the smallest value not yet taken, and taking from the first list on a tie keeps equal values in order | two-pointers, The idea and A worked example; run: `two_pointers.py` |
| A3 | Compaction: the first `write` positions hold the kept values among the first `read`, in order, and `write <= read`, so no unread value is overwritten; deleting in place costs O(n · k) | in-place-compaction, The idea and Complexity; run: `compaction.py` |
| A4 | At most `k` copies in a sorted list: compare with `values[write - k]`; comparing with `values[read - k]` fails once positions behind `read` are overwritten | in-place-compaction, Expert notes; run: `[1, 1, 1, 2, 2, 3]` gives `[1, 1, 2, 2, 3]` and `[1, 1, 2, 3]` |
| A5 | Both-ends partition makes at most `n / 2` swaps and keeps neither side's order | in-place-compaction, Expert notes |
| A6 | Counting pairs within a budget counts every fitting pair exactly once, in at most `n - 1` steps; fixing the smallest value gives triples in O(n²) | pairs-in-sorted-arrays, A worked example; run: 11,088 cases against every combination, 0 disagreements |
| A7 | The staircase walk on a grid sorted along rows and columns; pairs by difference with both pointers moving right; the `m`-th smallest pair sum by binary search over the count | pairs-in-sorted-arrays, Expert notes |
| A8 | A fixed window has `n - k + 1` positions; recomputing costs O((n - k + 1) · k), about `n² / 4` near `k = n / 2`; sliding costs at most `2n` updates | fixed-size-windows, The idea and Complexity; run: `fixed_windows.py` |
| A9 | A polynomial rolling hash slides by subtracting the leaving character's term, multiplying by the base and adding the entering character | fixed-size-windows, Expert notes; algebra |
| A10 | `1e16 + 1.0` rounds to `1e16`, so a rolling float sum of `[1.0, 1.0]` reports 1.0 | Run: `fixed_windows.py` |
| A11 | Longest form: for a rule closed under shrinking, the smallest valid left edge `L(r)` never decreases and the loop stops exactly at it; shortest form: for a rule closed under growing, the loop records the shortest window of all | variable-size-windows, A worked example; run: 70,993 cases against every stretch, 0 disagreements |
| A12 | With a negative value the window fails: `[5, -4, 1]` within 3 gives 2 instead of 3 | variable-size-windows, When the window fails; run: `variable_windows.py` |
| A13 | The valid windows ending at `r` number `r - L(r) + 1`; "exactly `k` different values" is "at most `k`" minus "at most `k - 1`" | variable-size-windows, When to use it and Expert notes |
| A14 | Left out: the history and names of the classic algorithms (the Dutch national flag, Hoare's partition, Floyd's cycle finding, saddleback search, Rabin–Karp), since no primary source was checked | |

## Changes from the first accuracy review (2026-11-12)

The review found every proof correct, every citation confirmed and every example printing what its guide shows; these are its findings and what changed.

| Finding | Change |
|---------|--------|
| Spoiler in in-place-compaction: `evens_first` was the swap solution of `move-zeroes` line for line, and its docstring repeated that problem's approach name | The function, its output and its bullet were removed; the swap variant stays as prose in the stability note |
| Spoiler in variable-size-windows: `shortest_with_at_least` solved `min-size-subarray-sum` unchanged | The shortest form now finds the fewest songs in a row by at least `k` different artists, with a count per artist, checked against every stretch for 1 to 4 artists |
| "The contract" was used without a definition | Defined on first use as the function's specification of what it promises its callers |
| The triple count sliced `prices[first + 1:]`, an O(n) copy per fixed value | `count_pairs_within` takes a `start` index |
| The difference scan said "keeping `p < q`" without saying how | `q` moves one place too when `p` catches up with it |
| `trapping-rain-water` and `sliding-window-maximum` came at the end of the path, away from their guides | Each closes its guide's section, so every guide is followed by its problems from easiest to hardest |
