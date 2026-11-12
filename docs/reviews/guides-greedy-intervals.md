# Review: the facts of the greedy and interval guides

The five guides of the path "Greedy choices and intervals: from your first greedy proof to scheduling with deadlines" (`guides/paths/greedy-intervals.yaml`; [guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about algorithms, their history and languages. This page lists each one with where it was checked, so that a later review starts from the sources, and records how each guide was checked against the problems it links.

"Quote" means the exact text was read on that page or in that book. "Run" means an example of the guide, or a one-off program, printed it, on CPython 3.13.12. "Proof" means the guide proves the claim itself; the proof is written out in the guide for review, and an exhaustive run on small inputs agrees with it. A fact that could not be checked was left out of the guides; the section "Left out" lists those.

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
| B9 | The weighted number of late jobs is NP-hard and solvable in O(nW) time, W the total weight; the guide's heap rule ignores weights, so it is only for counting late jobs | Quote: *Elements of Scheduling*, ch. 5 opening. The draft also claimed the rule stays optimal for oppositely ordered weights; §5.4 states that case with the job given up chosen as `argmax p = argmin w`, so among jobs of equal length the lightest must go, and the guide's rule breaks such ties by arrival (two jobs of length 1, both due at 1, weights 10 and 1: it gives up the weight-10 job). The claim was removed |
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
| R3 | Longest unbroken stretch 26 minutes; the current stretch lasts 10, 20, 20, 26, 15, 22 and 10 minutes after each segment in start order | Run: `longest_stretch.py` |
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
| can-attend-meetings | intervals | Hint 1: which pairs can clash once sorted by start; Hint 2: sort by start and compare each meeting with the one before; Hint 3: `<` not `<=` | The overlap test for each convention, which any interval guide needs, and the advice to find the convention before choosing `<` or `<=`, without saying which this problem needs. The idea's "sort by start to see what runs together" is the general move behind Hints 1 and 2. The draft's trap "neighbors after sorting by start" reveal overlap, which was Hint 2, was replaced by advice not to assume an input order. The guide never checks a list for a clash |
| merge-intervals | intervals | Hint 1: what sorting by start does; Hint 2: one pass keeping the last merged interval; Hint 3: extend with the maximum of the ends; follow-up 1: why one preparation makes one pass enough | The longest-stretch example sorts by start and walks once with the same test, `start > reach`, and takes the maximum of the ends ("the reach is a maximum"), so Hints 2 and 3 are there in another form. It computes and prints lengths only: no merged interval is ever built, yielded or printed. The draft's `unbroken_runs`, which yielded the merged intervals with the exact merge test, and its "why one pass is enough" argument, which answered follow-up 1, were removed |
| insert-interval | intervals | Three runs; binary search for the window | No insertion into a sorted list, no binary search (removed from the draft) |
| interval-list-intersections | intervals | `[max, min]`; advance the pointer that ends first | No intersection formula, no two-list walk |
| coverage-gaps | intervals | A coverage cursor; total uncovered days | The longest-stretch example prints how long the current stretch lasts, never a gap, a total or where a stretch ends; the draft's sentence on gaps between runs was removed |
| non-overlapping-intervals | intervals | Hints 1 to 3: keep as many as possible, the earliest end first, sort by end; follow-ups: which to keep, the exchange argument, prices | Deliberate exception, see below |
| range-module | intervals | Disjoint sorted intervals; a lazy segment tree; closed integer ranges | None of these (a sentence about structures that stay sorted was removed from the draft) |
| min-meeting-rooms | sweep-lines | Hint 1: rooms equal the most meetings running at once (the Output section says so too); Hint 3: a heap of end times, or two sorted lists; follow-ups: room assignment, one room, the busiest time | Deliberate exception, see below |
| employee-free-time | sweep-lines | Hint 2: sort by start, remember the latest end, a later start opens a free span; Hint 3: a heap merging the sorted lists | No free spans and no `heapq.merge` in any guide. The intervals guide's longest-stretch walk uses the same reach test as Hint 2 but prints only lengths; its draft sentence on gaps was removed |
| min-interval-per-query | sweep-lines | Sweep sorted queries; a heap keyed by size with lazy removal | No queries in any example; the expert note on summaries does not name a structure |
| task-scheduler | scheduling-with-deadlines | The most frequent available label; frames | Nothing about frequencies or cooldowns |
| maximize-capital | scheduling-with-deadlines | Sort by requirement, a max-heap of affordable profits | The heap holds jobs already taken, to give one up, not available choices to pick from; no "two orderings" phrasing |
| remove-covered-intervals | greedy-traps | Ties at equal starts, end descending; the furthest end | The ties section uses end-sorted requests and heap entries; no containment, no tie direction for starts |

## Deliberate exceptions to the spoiler rule

The guides spec says that a guide never gives away a linked problem's solution ([Writing a guide](../specs/guides.md#writing-a-guide), step 1). The scope of this path required teaching two techniques that are, on their own, the solutions of two linked problems. Both are taught on examples that are not catalog problems, and both are kept on purpose; this is exactly what each guide gives.

| Problem | Guide | What the guide gives | What it does not give |
|---------|-------|----------------------|-----------------------|
| non-overlapping-intervals | intervals | The earliest-end rule as code (`one_telescope.py`: sort by end, grant each request that overlaps nothing granted), the counterexamples to earliest start and shortest first, and a stays-ahead proof that it keeps the most intervals. With the problem's own Hint 1, removing the fewest is keeping the most, this solves the problem; the example prints the granted requests, which answers follow-up 1. The traps guide's checker repeats the rule | The removal count as such; the one-comparison form that makes the pass O(n), only that one exists; the exchange argument of follow-up 2, left as the exercise it asks for; the priced version of follow-up 3 |
| min-meeting-rooms | sweep-lines | The peak number of open intervals as code (`peak_sessions.py`: +1 and −1 events sorted by `(time, change)`, so closes come before opens at equal times), with why reading the count after every event is safe and a demonstration that opens first overcounts. With Hint 1, rooms equal the most meetings at once, this solves the problem by a third method beside its heap and two-list approaches, and also answers follow-up 2, whether one room suffices. The traps guide's checker repeats the closes-first peak | The heap of end times and the two sorted lists of Hint 3; when the peak happens, follow-up 3 (cut from the draft); an assignment of meetings to rooms, follow-up 1 |

## Changes from the first independent review

The review confirmed every source and all the arithmetic, and found these errors.

| Finding | Change |
|---------|--------|
| The weighted Moore–Hodgson claim omitted the book's tie-break (give up the lightest among the longest), so the guide's arrival tie-break was wrong for weights | The claim was removed; the note says the heap rule is only for counting late jobs (B9) |
| The sweep guide said every count read between events is part of the true count, which fails for `[0, 4)` and `[1, 4)` | The guide now bounds the counts during the closes by the count just before `t` and during the opens by the count at `t`, both real moments |
| The earliest-end proof said the scan "finds it overlapping nothing granted" before splitting into cases, where it only holds in the second | The proof splits into two cases first |
| `unbroken_runs` yielded the merged intervals with the exact merge test, a full merge-intervals solution, and the gap sentence answered its follow-up 1 and the coverage-gaps and employee-free-time walks; the neighbors trap gave can-attend-meetings' Hint 2 | The example computes only the longest stretch as a length; the gap sentence, the merged-interval drawing and the neighbors trap are gone |
| The spoiler table misstated what three guides give | Rows for merge-intervals, can-attend-meetings and min-meeting-rooms rewritten; two deliberate exceptions recorded above |
| The scheduling guide pointed to trees and heaps guides that are not on main | It explains the two max-heap operations inline and names the trees and heaps path only as further reading |
| The exchange drawing showed a "first difference" step that the proof does not use | It shows the swap of neighbors out of order, as the proof does |
| The stays-ahead proof skipped the case where every parcel fits; "right only when"; "will fail" | Covered; "guaranteed right only when"; "can fail" |
