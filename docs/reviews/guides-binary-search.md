# Review: the facts of the binary search guides

The five guides of the path "Binary search: from a sorted array to searching the answer" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about languages, libraries and one piece of history. This page lists each one with where it was checked, so that the independent accuracy review starts from the sources.

"Quote" means the exact text was read on that page, fetched on 2026-11-12. "Run" means an example of the guide, or a one-off program, printed it: on CPython 3.13.12, OpenJDK 21.0.2, Go 1.27.3, Node 24.18.0 and rustc 1.92.0. "Proof" means the guide argues it in plain language and the argument is repeated here in short. A fact that could not be checked was left out of the guides; the last section lists what was left out.

| Guide | Slug | Level |
|-------|------|-------|
| Searching a sorted array | `searching-a-sorted-array` | intro |
| Lower and upper bounds | `lower-and-upper-bounds` | core |
| Common binary search mistakes | `binary-search-mistakes` | core |
| Binary search on the answer | `binary-search-on-the-answer` | core |
| Searching rotated and implicit structures | `rotated-and-implicit-search` | advanced |

## Python

| # | Claim | Source |
|---|-------|--------|
| P1 | `bisect_left` returns `ip` with every element of `a[lo:ip]` `< x` and every element of `a[ip:hi]` `>= x`; `bisect_right`, also named `bisect`, the same with `<=` and `>`; `lo` and `hi` select part of the list, the whole list by default | Quote: [bisect](https://docs.python.org/3/library/bisect.html); run: `bounds.py` (agrees with a hand-written bound for 0..34) |
| P2 | `key=` was added in 3.10; it is applied to the elements and, to support searching records, not to `x` | Quote: bisect ("Changed in version 3.10: Added the key parameter"; "the key function is not applied to the x value"); run: `bounds.py`, `answer_search.py` |
| P3 | `insort` is O(n): the O(log n) search is dominated by the O(n) insertion | Quote: bisect |
| P4 | `int` has unlimited precision, so `(lo + hi) // 2` never overflows | Quote: [stdtypes, numeric types](https://docs.python.org/3/library/stdtypes.html#numeric-types-int-float-complex); run: `mistakes.py` (a 41-digit square root) |
| P5 | CPython lists are contiguous arrays, so indexing costs the same whatever the size or the index | Quote: [design FAQ, how are lists implemented](https://docs.python.org/3/faq/design.html#how-are-lists-implemented-in-cpython) |
| P6 | `math.isqrt` is the integer square root of a non-negative integer, added in 3.8 | Quote: [math](https://docs.python.org/3/library/math.html); run: `mistakes.py` (both fixed searches equal it for 0..1999 and for 10⁴⁰ + 12345) |
| P7 | `math.ulp(x)` is the value of the least significant bit of `x`, added in 3.9; the first float above `x` is `x + ulp(x)`; `math.ulp(1e16)` is 2.0 | Quote: math; run: `mistakes.py` |
| P8 | Almost all platforms map Python floats to IEEE 754 binary64, with 53 bits of precision | Quote: [tutorial, floating-point arithmetic](https://docs.python.org/3/tutorial/floatingpoint.html) |
| P9 | A `range` stores only start, stop and step, computes its items as needed, and implements the `Sequence` ABC | Quote: [stdtypes, ranges](https://docs.python.org/3/library/stdtypes.html#ranges) |
| P10 | `bisect_left(range(...), True, key=...)` searches a range of candidate answers | Run: `answer_search.py` on 3.13. The bisect page does not say which sequence types it accepts; the guide states only what ran |
| P11 | CPython's list sort gallops while merging: after `MIN_GALLOP` wins in a row it compares with positions 0, 1, 3, 7, ..., `2**j - 1`, then binary-searches; no more than about 2 lg(B) comparisons; a straight binary search loses to it unless the run is quite long | Quote: [`Objects/listsort.txt`](https://github.com/python/cpython/blob/main/Objects/listsort.txt), sections "Galloping" and the merge description |
| P12 | `itertools.accumulate` gives running sums | Quote: [itertools](https://docs.python.org/3/library/itertools.html#itertools.accumulate) (as in the hashing review, P12); run: `implicit_search.py` |

## Java

| # | Claim | Source |
|---|-------|--------|
| J1 | `Arrays.binarySearch`: the array must be sorted, otherwise the results are undefined; with several equal elements "there is no guarantee which one will be found"; it returns the index, or `-(insertion point) - 1`, where the insertion point is the index of the first element greater than the key, or the length; the result is `>= 0` exactly when found | Quote: [Arrays, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Arrays.html), `binarySearch(int[], int)` and the range overload; run: `ArraysSearch.java` (-7 for 10, -1 for 1, -13 for 99) |
| J2 | `Collections.binarySearch`: the same contract; log(n) for a random-access list; on a large list without `RandomAccess`, O(n) link traversals and O(log n) comparisons | Quote: [Collections, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Collections.html) |
| J3 | Neither `Arrays` nor `Collections` has a lower-bound method: their only search methods are the `binarySearch` overloads | Checked: every method name in both Java 21 pages containing "search" or "bound" is `binarySearch` |
| J4 | An `int` addition that overflows keeps the low-order bits, and its sign differs from the true sum's | Quote: [JLS §15.18.2](https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html#jls-15.18.2); run: `Midpoint.java` (1,500,000,000 + 2,000,000,000 prints -794967296) |
| J5 | `>>>` shifts with zero-extension, so `(lo + hi) >>> 1` is right for two non-negative `int`s | Quote: [JLS §15.19](https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html#jls-15.19); run: `Midpoint.java` (1750000000); arithmetic: the true sum is below 2³² |
| J6 | Arrays are indexed by `int`; an index out of range throws `ArrayIndexOutOfBoundsException` | Quote: [JLS §10.4](https://docs.oracle.com/javase/specs/jls/se21/html/jls-10.html#jls-10.4) |
| J7 | The current `Arrays.binarySearch` computes `int mid = (low + high) >>> 1` | Quote: [OpenJDK `Arrays.java`](https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/util/Arrays.java), every `binarySearch0` |
| J8 | Bug JDK-5045582, "(coll) binarySearch() fails for size larger than 1<<30", dated 05/11/2004 against `1.5.0-beta`: `int mid = (low + high) >> 1` overflowed, and a 1,100,000,000-byte array threw `ArrayIndexOutOfBoundsException: -1064671149`; it reports similar problems in `Collections` and the same calculation in `TreeMap`; fix version 6 | Quote: [JDK-5045582](https://bugs.openjdk.org/browse/JDK-5045582) |
| J9 | `TreeMap` guarantees log(n) time for `containsKey`, `get`, `put` and `remove`; `ceilingKey` is the least key greater than or equal to the given key, `floorKey` the greatest key less than or equal | Quote: [TreeMap, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/TreeMap.html) |
| J10 | `ArrayList.get` runs in constant time | Quote: [ArrayList, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/ArrayList.html) |

## Go

| # | Claim | Source |
|---|-------|--------|
| G1 | `sort.Search(n, f)` returns the smallest `i` in `[0, n)` where `f(i)` is true, assuming `f` is false then true, and `n` if there is none; it calls `f` only inside `[0, n)`; descending data uses `<=` instead of `>=` | Quote: [sort](https://pkg.go.dev/sort#Search); run: `answer_search.go` (the first gap too wide, 8) |
| G2 | `slices.BinarySearch` returns the earliest position where the target is found, or where it would appear, and whether it was found; the slice must be sorted in increasing order; `BinarySearchFunc` takes a comparison | Quote: [slices](https://pkg.go.dev/slices#BinarySearch) |
| G3 | The `slices` package is new in Go 1.21 | Quote: [Go 1.21 release notes](https://go.dev/doc/go1.21) ("New slices package") |
| G4 | `sort.Search`, `sort.Find` and `slices.BinarySearch` compute `h := int(uint(i+j) >> 1) // avoid overflow when computing h` | Quote: [`sort/search.go`](https://go.dev/src/sort/search.go), [`slices/sort.go`](https://go.dev/src/slices/sort.go) |
| G5 | Unsigned `+`, `-`, `*` and `<<` are computed modulo 2ⁿ; signed overflow is deterministic and does not panic | Quote: [the Go specification, integer overflow](https://go.dev/ref/spec#Integer_overflow); run: `underflow.go` (`0 - 1` as `uint64` is 18446744073709551615), `answer_search.go` (`(lo + hi) / 2` is -2223372036854775808) |
| G6 | `uint` has 32 or 64 bits and `int` has the same size | Quote: the Go specification, [numeric types](https://go.dev/ref/spec#Numeric_types) |

## Rust

| # | Claim | Source |
|---|-------|--------|
| R1 | `binary_search` on an unsorted slice returns a result that is "unspecified and meaningless"; `Ok` holds the index of a match, any one of several, "chosen deterministically, but ... subject to change in future versions of Rust"; `Err` holds where a matching element could be inserted; see also `binary_search_by`, `binary_search_by_key` and `partition_point` | Quote: [slice `binary_search`](https://doc.rust-lang.org/std/primitive.slice.html#method.binary_search); run: a one-off program (`Err(7)` for 4 in the documentation's example slice) |
| R2 | `partition_point` (stable since 1.52.0) returns the first index of the second partition, where the predicate is true for the elements at the start; the lower bound is `partition_point(\|x\| x < v)` and the upper `partition_point(\|x\| x <= v)` | Quote: [slice `partition_point`](https://doc.rust-lang.org/std/primitive.slice.html#method.partition_point) and the `binary_search` example; run: a one-off program (1 and 5 for the value 1) |
| R3 | Integer operators panic on overflow in debug mode; `-C debug-assertions` and `-C overflow-checks` control it | Quote: [the Rust Reference, overflow](https://doc.rust-lang.org/reference/expressions/operator-expr.html#overflow) |
| R4 | In release mode (`--release`) there are no overflow checks, and overflow wraps in two's complement; the `checked_*`, `wrapping_*`, `overflowing_*` and `saturating_*` methods handle it explicitly | Quote: [the Rust book, integer overflow](https://doc.rust-lang.org/book/ch03-02-data-types.html#integer-overflow); run: a one-off program, `0usize - 1` through `black_box`: a debug build panics with "attempt to subtract with overflow", a `-O` build prints 18446744073709551615 |
| R5 | `usize::midpoint`, stable since 1.85.0, computes `(a + b) / 2` as if in a larger type, so it never overflows | Quote: [`usize::midpoint`](https://doc.rust-lang.org/std/primitive.usize.html#method.midpoint); run: `usize::MAX.midpoint(usize::MAX - 2)` prints 18446744073709551614 |
| R6 | `usize::checked_sub` returns `None` if the subtraction overflows | Quote: [`usize::checked_sub`](https://doc.rust-lang.org/std/primitive.usize.html#method.checked_sub); run: `0usize.checked_sub(1)` prints `None` |

## JavaScript and TypeScript

| # | Claim | Source |
|---|-------|--------|
| JS1 | `Array` has no binary search method | Checked: the `Array.prototype` methods listed on [MDN, Array](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array); none is a binary search |
| JS2 | `findIndex` calls its function once for each element in ascending-index order until it returns a truthy value | Quote: [MDN, findIndex](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/findIndex) |
| JS3 | Numbers represent integers exactly up to `Number.MAX_SAFE_INTEGER`, 2⁵³ − 1 | Quote: [MDN, MAX_SAFE_INTEGER](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/MAX_SAFE_INTEGER) |
| JS4 | `>>>` works on the operand's 32-bit representation: bits above 32 are discarded | Quote: [MDN, unsigned right shift](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Unsigned_right_shift) |
| JS5 | An array's `length` is an unsigned 32-bit integer | Quote: [MDN, Array length](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/length) |
| TS1 | TypeScript never changes the runtime behaviour of JavaScript and provides no additional runtime libraries | Quote: [TypeScript for the new programmer](https://www.typescriptlang.org/docs/handbook/typescript-from-scratch.html) |
| JS6 | `Math.floor((lo + hi) / 2)` is exact for every array index, and `(lo + hi) >>> 1` only while `lo + hi < 2³²` | Arithmetic from JS3 to JS5: two indexes sum to less than 2³³, far below 2⁵³ |

## Algorithms and arithmetic

| # | Claim | Source |
|---|-------|--------|
| A1 | A binary search on `n` elements takes at most ⌊log₂ n⌋ + 1 steps: from `s` positions, either side of the midpoint keeps at most `s // 2` | Proof; run: `sorted_search.py` (the worst case over every target equals ⌊log₂ n⌋ + 1 for n = 1, 2, 3, 15, 16, 100, 1024) |
| A2 | A search by yes/no comparisons needs at least log₂(n + 1) comparisons in the worst case; a bound search with one equality check uses at most ⌊log₂ n⌋ + 2 | Proof: `k` comparisons give at most 2ᵏ paths, and `n + 1` answers must be told apart; ⌊log₂ n⌋ + 1 ≤ ⌈log₂(n + 1)⌉ |
| A3 | `first_true` is correct: false before `lo`, true from `hi` on, and `[lo, hi)` shrinks on every step | Proof; run: `bounds.py` against `bisect` |
| A4 | The loop with `lo = mid` and a midpoint rounded down stops moving once `hi = lo + 1`; rounding up, or searching for the first false and subtracting one, fixes it | Run: `mistakes.py` (the trace repeats `lo 3 hi 4 mid 3`) |
| A5 | `first_true` on a predicate that is not monotone returns a false-to-true switch, not the first true | Run: `mistakes.py` (4 instead of 2; 6 instead of 1 for an equality predicate) |
| A6 | A bisection with `hi - lo > 1e-9` near 1e16 never ends; stopping when no double lies strictly between the ends takes 52 steps from `[0, 1e16 + 2]` | Run: `mistakes.py`; P7 |
| A7 | Sorted arrays of length `L` over `v` values number C(L + v − 1, L): 35 for lengths 0 to 4 over 3 values, 175 cases with five targets | Arithmetic; run: `mistakes.py` (60 of 175 fail for `>=` in place of `>`, first `[0]`, 0) |
| A8 | The greedy check of the sensors places at least as many sensors as any valid placement, and the largest gap is 7 for 4 sensors on the posts 0 3 4 7 11 12 18 20 25 | Proof (sensor by sensor, by induction); run: `answer_search.py` and `answer_search.go`, and every choice of 4 posts out of 9 |
| A9 | Galloping to an answer at position `p ≥ 1` makes exactly ⌈log₂ p⌉ + 1 probes, then searches at most `p` positions | Proof; run: `implicit_search.py` (position 41: 7 probes and 5 reads; past the end: 10 probes and 8 reads) |
| A10 | In a rotated array with equal values, a search can be forced to read every position: O(n) | Proof (an adversary placing one 0 among 2s); run: `implicit_search.py` (two arrays alike at first, middle and last) |
| A11 | ⌊log₂ n⌋ + 1 is 20 for a million and 30 for a billion; at most 60 checks for 10¹⁸ candidates; four quintillion lies between 2⁶¹ and 2⁶², so 62 steps | Arithmetic; run: `answer_search.go` (62 steps) |
| A12 | `lo + hi` overflows a signed 64-bit index only past 2⁶² elements, and Java's `int` only past 2³⁰ | Arithmetic: with `lo < hi ≤ n`, `lo + hi < 2n` |
| A13 | 100,000 values of up to 10⁹ sum to up to 10¹⁴, beyond 32 bits | Arithmetic |

## Left out

| Topic | Why |
|-------|-----|
| Who first published binary search, and when the first correct version appeared | No primary source was fetched; only secondary retellings exist |
| Blog posts about the midpoint overflow | Excluded by the owner's rule on sources; the JDK bug report, a primary record, is cited instead |
| Interpolation search and its average cost | The usual result could not be checked against a primary source |
| Cache behaviour of binary search and cache-friendly layouts | No primary source |
| C and C++ (`std::lower_bound`, `std::midpoint`, signed overflow) | The ISO standards are not freely available, and no other official source was used |
| The research papers named in `listsort.txt` | Not needed for the claim, and the guides name no authors |
| "Python has no sorted container in its standard library" | An absence that no single page states; the guides say only what Java's `TreeMap` offers |
| The Rust source of `binary_search` | Which match it returns is documented as unspecified, so the guides do not describe it |

## Spoilers checked

The guides teach on examples of their own and name each practice problem's question only, after reading every linked `problem.md`.

| Problem | What the guides avoid |
|---------|-----------------------|
| `binary-search`, `search-insert-position`, `first-last-position` | The worked examples use parcel weights and a list of 15 values; bounds are taught generally, with no "first and last occurrence" example |
| `time-based-kv-store`, `snapshot-array` | No example keyed by time or version; no history-per-key design |
| `debug-binary-search-bounds` | The mistakes guide's examples are a square-root loop and a half-open start with a closed loop condition; the other mixes of interval styles are not spelled out |
| `debug-unsigned-underflow` | The underflow example is a Go membership search, not "the last release at or before a time" |
| `koko-eating-bananas`, `split-array-largest-sum`, `swim-rising-water` | The worked example maximizes the smallest gap between sensors; no rate, piece-sum or grid example |
| `search-2d-matrix` | The index map is taught on chunks of different sizes and on fixed-size records, not on a grid |
| `min-in-rotated-array`, `search-rotated-array` | The guide shows that "in the second run?" switches once, without the comparison or a search for the break |
| `find-peak-element` | Not discussed beyond its practice line |
| `median-of-two-sorted-arrays` | Not discussed beyond its practice line |
