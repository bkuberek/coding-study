# Review: the facts of the greedy and interval guides

The five guides of the path "Greedy choices and intervals: from your first greedy proof to scheduling with deadlines" (`guides/paths/greedy-intervals.yaml`; [guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about algorithms, their history and languages. This page lists each one with where it was checked, so that a later review starts from the sources, and records how each guide was checked against the problems it links.

"Quote" means the exact text was read on that page or in that book. "Run" means an example of the guide, or a one-off program, printed it, on CPython 3.13.12. "Proof" means the guide proves the claim itself; the proof is written out in the guide for review, and an exhaustive run on small inputs agrees with it. A fact that could not be checked was left out of the guides; the last section lists those.

## Books and papers

| # | Claim | Source |
|---|-------|--------|
| B1 | Three strategies for greedy proofs: greedy stays ahead, a structural bound, and the exchange argument | Quote: [Kevin Wayne's slides for Kleinberg and Tardos, *Algorithm Design*, ch. 4](https://www.cs.princeton.edu/~wayne/kleinberg-tardos/pdf/04GreedyAlgorithmsI.pdf), slide "Greedy analysis strategies"; the book's title and authors from the [slides' index page](https://www.cs.princeton.edu/~wayne/kleinberg-tardos/) |
| B2 | Interval scheduling: earliest start and shortest interval have counterexamples; earliest finish is optimal | Quote: the same slides (quiz and "counterexample for earliest start time", "counterexample for shortest interval"); [Erickson, *Algorithms*, ch. 4](https://jeffe.cs.illinois.edu/teaching/algorithms/book/04-greedy.pdf), §4.2, which proves earliest finish by an exchange argument and runs it in O(n log n) |
| B3 | Files on a tape: sorting by length minimizes the expected access cost; with access frequencies, sort by length divided by frequency; both by swapping a misordered neighboring pair | Quote: Erickson ch. 4, §4.1, the first two lemmas |
| B4 | Smith's ratio rule: ordering jobs by nonincreasing weight per processing time solves the weighted sum of completion times; a sequence is optimal if and only if it is in ratio order, proved by interchanging neighbors (Theorem 4.1); shortest processing time is the special case; the origins of shortest processing time are unknown; Smith published in 1956 | Quote: [Lenstra and Shmoys (eds.), *Elements of Scheduling*](https://arxiv.org/abs/2001.06005), ch. 4 opening and §4.1, and its bibliography; Crossref metadata of [doi:10.1002/nav.3800030106](https://doi.org/10.1002/nav.3800030106): "Various optimizers for single-stage production", *Naval Research Logistics Quarterly* 3, 59–66, 1956 |
| B5 | Jackson's EDD rule: any earliest-due-date schedule minimizes the maximum lateness; all due dates can be met if and only if an EDD schedule meets them; proof by interchanging neighboring jobs; due to Jackson, Research Report 43 of the Management Science Research Project, UCLA, 1955 | Quote: *Elements of Scheduling*, ch. 3, opening, §3.1 (Theorem 3.1, Corollary 3.2), the chapter notes and the bibliography. The report itself was not found online and was not read |
| B6 | With release dates and no preemption, minimizing maximum lateness is strongly NP-hard; with preemption, the preemptive EDD rule, which at each release and completion runs the available job with the earliest due date, solves it | Quote: *Elements of Scheduling*, ch. 3 opening and §3.2 |
| B7 | Moore–Hodgson: take the jobs in EDD order, add each, and when the total passes the job's due date remove the longest; it finds a largest set of jobs that can all be on time; O(n log n) with a priority queue supporting insert and delete-max, each O(log n); Moore (1968) suggested a less elegant algorithm and credited these recurrences to his colleague Hodgson | Quote: *Elements of Scheduling*, ch. 5, §5.4 and its notes; Crossref metadata of [doi:10.1287/mnsc.15.1.102](https://doi.org/10.1287/mnsc.15.1.102): Moore, "An n Job, One Machine Sequencing Algorithm for Minimizing the Number of Late Jobs", *Management Science* 15, 102–109, 1968. The paper itself was not read |
| B8 | There is an optimal schedule in which the on-time jobs come first, in EDD order, and the late jobs after them | Quote: *Elements of Scheduling*, ch. 5, §5.1 |
| B9 | The weighted number of late jobs is NP-hard and solvable in O(nW) time, W the total weight; Moore–Hodgson stays optimal when processing times and weights are oppositely ordered (p_i < p_j implies w_i ≥ w_j), which holds when all p_j = 1 or all w_j = 1 | Quote: *Elements of Scheduling*, ch. 5 opening and §5.4. The guide's "equal weights and equal lengths" generalizes "all 1" by the definition: with all lengths equal, the condition holds vacuously |
| B10 | Dijkstra prefers `a <= i < b`: the difference of the bounds is the length, adjacent ranges share a bound, and the empty range needs no unnatural bound; Mesa programmers were advised to use only this convention | Quote: [EWD831](https://www.cs.utexas.edu/~EWD/transcriptions/EWD08xx/EWD831.html) |

## Python

| # | Claim | Source |
|---|-------|--------|
| P1 | `sorted` and `list.sort` are guaranteed stable | Quote: [functions, `sorted`](https://docs.python.org/3/library/functions.html#sorted); [stdtypes, `list.sort`](https://docs.python.org/3/library/stdtypes.html#list.sort); run: `ties.py` |
| P2 | A key function is called exactly once per record; sorts are stable | Quote: [Sorting techniques](https://docs.python.org/3/howto/sorting.html) |
| P3 | Sequences such as tuples compare lexicographically, element by element | Quote: [value comparisons](https://docs.python.org/3/reference/expressions.html#value-comparisons); run: `longest_stretch.py`, `peak_sessions.py` (closes, `-1`, sort before opens, `+1`) |
| P4 | `range` stops before `stop` (`r[i] < stop`); the slice `s[i:j]` holds the items with `i <= k < j` | Quote: [stdtypes, sequence types](https://docs.python.org/3/library/stdtypes.html#sequence-types-list-tuple-range) |
| P5 | Dicts preserve insertion order, guaranteed since 3.7 | Quote: [stdtypes, dict](https://docs.python.org/3/library/stdtypes.html#mapping-types-dict) |
| P6 | `heapq` is a min-heap with the smallest item at `heap[0]`; 3.14 added max-heap functions such as `heappush_max` and `heappop_max`; tuple comparison breaks for equal priorities when the tasks have no order; an entry count between priority and task breaks ties in the order added | Quote: [heapq](https://docs.python.org/3/library/heapq.html) and its priority queue notes; run: `ties.py` raises `TypeError: '<' not supported between instances of 'dict' and 'dict'` on popping, and pops `print, scan, bind` with a counter |
| P7 | `fractions` provides rational number arithmetic | Quote: [fractions](https://docs.python.org/3/library/fractions.html); run: `oven_order.py` |
| P8 | `functools.cmp_to_key` turns a comparison function (negative, zero, positive) into a key for `sorted`, `min`, `max`, `heapq.nlargest`, `heapq.nsmallest` and `itertools.groupby` | Quote: [functools](https://docs.python.org/3/library/functools.html#functools.cmp_to_key) |

## Java, JavaScript and Go

| # | Claim | Source |
|---|-------|--------|
| L1 | `Arrays.sort(Object[])` and `Arrays.sort(T[], Comparator)` are guaranteed stable; `List.sort` is stable | Quote: [Arrays, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Arrays.html), [List, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html) |
| L2 | `Array.prototype.sort` is stable since ECMAScript 2019 | Quote: [MDN, `Array.prototype.sort`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/sort) |
| L3 | `sort.Slice` and `slices.SortFunc` are not guaranteed stable; `sort.SliceStable` keeps equal elements in their original order; `slices.SortStableFunc` exists | Quote: [sort](https://pkg.go.dev/sort), [slices](https://pkg.go.dev/slices) |

## Proofs, runs and arithmetic

| # | Claim | Source |
|---|-------|--------|
| R1 | Oven: listed order waits 35, shortest first 23, the best of 24 orders; swapping bread and bagels gives 32; with customers per batch, shortest first waits 46 and minutes per customer 40, the best of 6; the swap changes the total by `u·b - v·a` (1·6 - 3·4 = -6) | Run: `oven_order.py`; proof: greedy-choices, exchange argument |
| R2 | Lightest first carries 4 parcels, loads 3, 7, 13, 20 against 4, 11, 20; no plan carries more | Run: `lightest_first.py`; proof: greedy-choices, stays ahead |
| R3 | Longest unbroken stretch `[0, 26)` | Run: `longest_stretch.py` |
| R4 | Telescope: on 1,940 sets of 1 to 4 requests with endpoints 0 to 5, earliest start falls short on 227, shortest first on 6, earliest end on 0, ties going to the request listed first | Run: `one_telescope.py`; proof: intervals, stays ahead (assumes `start < end`) |
| R5 | Sessions: peak 3, and 4 with opens before closes; 6 overlapping pairs; sweep and every-pair counting agree on 1,000 small inputs with repeats | Run: `peak_sessions.py`, `overlapping_pairs.py`; proof: sweep-lines, each pair counted once |
| R6 | Print shop: earliest deadline first worst lateness 0 and +3, the best of every order; shortest first +3 and +7; the heap plan keeps 4 jobs on time, never giving up keeps 3; 0 failures on 6,561 inputs of 4 jobs | Run: `deadlines.py`, `most_on_time.py`; proof: scheduling, swaps of inversions and the three promises |
| R7 | The three promises of the Moore–Hodgson proof (feasible, largest, and its `r` shortest jobs the cheapest feasible set of `r`) hold after every job | Run: a one-off program over every instance of 1 to 5 jobs with lengths 1 to 3 and due dates 1 to 7 (5-job instances with the first length fixed at 1): 7,613,445 prefixes checked against brute force, 0 failures |
| R8 | Smallest failures: earliest start on `[(0, 2), (0, 1), (1, 2)]` with ties to the first listed, and on `[(0, 3), (1, 2), (2, 3)]` with any tie order; the closed test and opens-first on `[(0, 1), (1, 2)]` | Run: `find_counterexample.py`; the tie-independent case by hand |
| R9 | 10! = 3,628,800; 6 / 1,940 ≈ 0.3%; 6 + 36 + 216 = 258 | Arithmetic |

## Left out

| Topic | Why |
|-------|-----|
| A counterexample for "fewest conflicts first" | Not constructed and checked here |
| The history of the sweep line in computational geometry (Shamos and Hoey, Bentley and Ottmann) | The papers could not be read |
| Comparators written as a subtraction, which overflow in Java; JavaScript's default string sort of numbers; ordering by rates that may be `NaN` | Catalog problems are built on these bugs: `debug-sort-comparator`, `debug-sorted-report-rows`, `debug-float-ordering` |
| Turning closed integer intervals into half-open ones | A follow-up of `range-module` |
| Choosing intervals with weights, by dynamic programming | A follow-up of `non-overlapping-intervals`, and `job-scheduling-max-profit` |
| Interval partitioning and its depth bound, the structural proof's classic example | The solution of `min-meeting-rooms`; the structural style is only named |
| Merging sorted streams with `heapq.merge` | A hint and follow-up of `employee-free-time` |
| Answering point queries offline in sorted order | The hints of `min-interval-per-query` |
| Binary search over sorted starts | The hints and follow-up of `insert-interval` |

## Spoiler check

Each practice problem's statement, hints, approaches and follow-ups were read against the guide that links it, and against the path's other guides. The worked examples are not catalog problems: an oven, a cargo bike, a channel's segments, a telescope, server sessions and a print shop. The practice lines name each problem's question only.

| Problem | Guide | Closest hint, approach or follow-up | What the guide gives, and the decision |
|---------|-------|-------------------------------------|----------------------------------------|
| best-time-to-buy-sell-stock | greedy-choices | The cheapest price so far | Nothing about running minimums |
| jump-game | greedy-choices | Farthest reachable index; the fewest jumps | The stays-ahead example is lightest-first packing, not farthest reach or fewest stops |
| partition-labels | greedy-choices | Last positions; "why cut as soon as possible"; relation to merging intervals | Neither guide argues about cutting early or relates letters to intervals |
| gas-station | greedy-choices | Restart after an empty tank; the total of gas minus cost | Nothing circular, no running balance |
| hand-of-straights | greedy-choices | The smallest card must start a straight | No forced-smallest-element argument |
| candy-distribution | greedy-choices | Two passes and a maximum | Nothing about neighbor constraints |
| can-attend-meetings | intervals | Sort by start and compare neighbors; `<` not `<=` | The overlap test for each convention, which any interval guide needs; the guide never checks a list for a clash |
| merge-intervals | intervals | Sort by start, extend the last merged end with the maximum | Accepted overlap: the scope requires teaching merging. Taught on the longest unbroken stretch, which returns one length, never the merged list |
| insert-interval | intervals | Three runs; binary search for the window | No insertion into a sorted list, no binary search (removed from the draft) |
| interval-list-intersections | intervals | `[max, min]`; advance the pointer that ends first | No intersection formula, no two-list walk |
| coverage-gaps | intervals | A coverage cursor; total uncovered days | The runs example reports the longest run, not gaps or totals |
| non-overlapping-intervals | intervals | Earliest end; "write the exchange argument"; which to keep; prices | Accepted overlap: the scope requires earliest end. Proved by stays ahead, so the exchange argument stays an exercise; the guide checks each request against every grant and does not give the one-comparison form; the removal count and the priced version are not mentioned |
| range-module | intervals | Disjoint sorted intervals; a lazy segment tree; closed integer ranges | None of these (a sentence about structures that stay sorted was removed from the draft) |
| min-meeting-rooms | sweep-lines | Rooms equal the maximum overlap (in the statement); a heap of end times; two sorted lists; the busiest time; room assignment | Accepted overlap: the scope requires counting maximum overlap with +1/−1 events. No heap, no two lists, no room assignment, and the time of the peak was cut from the draft |
| employee-free-time | sweep-lines | Union of intervals, latest end; a heap merging sorted lists | No free-time spans, no `heapq.merge` |
| min-interval-per-query | sweep-lines | Sweep sorted queries; a heap keyed by size with lazy removal | No queries in any example; the expert note on summaries does not name a structure |
| task-scheduler | scheduling-with-deadlines | The most frequent available label; frames | Nothing about frequencies or cooldowns |
| maximize-capital | scheduling-with-deadlines | Sort by requirement, a max-heap of affordable profits | The heap holds jobs already taken, to give one up, not available choices to pick from; no "two orderings" phrasing |
| remove-covered-intervals | greedy-traps | Ties at equal starts, end descending; the furthest end | The ties section uses end-sorted requests and heap entries; no containment, no tie direction for starts |
