# Intervals: sorting, merging and choosing

## The idea

An **interval** is a stretch of a line between two endpoints: a booking from 9:00 to 10:30, the bytes 100 to 199 of a file, the minutes a show is on air. Interval problems ask how a collection of them relate: which overlap, what they cover together, how many can coexist.

First decide what the endpoints mean, because two conventions are common and they disagree exactly where intervals touch.

| Convention | Written | Holds | `[1, 3]` or `[1, 3)` with `[3, 5]` or `[3, 5)` |
|------------|---------|-------|----------------------------------|
| Closed | `[a, b]` | every `x` with `a <= x <= b` | share the point 3: they overlap |
| Half-open | `[a, b)` | every `x` with `a <= x < b` | touch but share nothing |

Half-open intervals are common in programs, and the rest of this guide uses them. Their length is `b - a`, and `[a, b)` followed by `[b, c)` covers `[a, c)` with no point counted twice and no point missing. Python's `range(a, b)` and its slices `s[a:b]` are half-open in the same way. A careful problem statement says which convention it uses, sometimes only through an example; find it before writing a comparison.

**Overlap.** Two half-open intervals `[a, b)` and `[c, d)` fail to overlap exactly when one ends before the other starts: `b <= c` or `d <= a`. So they overlap exactly when

```python
a < d and c < b
```

For closed intervals, both `<` become `<=`. This one test, with the right convention, is the base of everything else.

Two moves then solve most interval questions:

- **Sort by start to see what runs together.** In start order, an interval can only overlap the ones that came before it if it starts before they end, so one pass that remembers how far they reach is enough.
- **Sort by end to choose.** To keep the most intervals that do not overlap, the one that ends first leaves the most room for the others, and that choice can be proved safe.

## A worked example

A channel airs segments, some of them at the same time on different streams, as half-open intervals in minutes: `[30, 45)`, `[0, 10)`, `[8, 20)`, `[12, 15)`, `[20, 26)`, `[40, 52)` and `[60, 70)`, in the order they were logged. How long is the longest stretch during which something was on air without a break?

Sort the segments by start, then walk them remembering two numbers about the current **stretch**: when it began, and how far it **reaches**, the furthest end seen in it. A segment that starts at or before the reach continues the stretch and may push the reach further; one that starts after it begins a new stretch. The length of the current stretch is its reach minus when it began.

```python examples/longest_stretch.py
"""A channel airs segments [start, end) in minutes, some of them at the same time. How long is the
longest stretch during which something was on air without a break?"""

Interval = tuple[int, int]


def longest_unbroken(segments: list[Interval]) -> int:
    """Minutes of the longest stretch with no break, printing how long the current one lasts."""
    ordered = sorted(segments)
    since, reach = ordered[0]  # when the current stretch began, and how far it reaches so far
    longest = 0
    for start, end in ordered:
        if start > reach:
            since, reach = start, end
        else:
            reach = max(reach, end)  # a segment may end before the stretch does
        longest = max(longest, reach - since)
        print(f"[{start:>2}, {end:>2}): on air for {reach - since:>2} minutes without a break")
    return longest


segments = [(30, 45), (0, 10), (8, 20), (12, 15), (20, 26), (40, 52), (60, 70)]
print("longest unbroken stretch:", longest_unbroken(segments), "minutes")
```

It prints:

```output examples/longest_stretch.py
[ 0, 10): on air for 10 minutes without a break
[ 8, 20): on air for 20 minutes without a break
[12, 15): on air for 20 minutes without a break
[20, 26): on air for 26 minutes without a break
[30, 45): on air for 15 minutes without a break
[40, 52): on air for 22 minutes without a break
[60, 70): on air for 10 minutes without a break
longest unbroken stretch: 26 minutes
```

`sorted` orders the tuples by their first element, the start, and breaks ties by the second, because Python compares tuples element by element. Follow the first stretch in the drawing.

```mermaid
flowchart TD
  accTitle: Timing the first stretch
  accDescr: The segment from 0 to 10 begins a stretch of 10 minutes. The segment from 8 to 20 overlaps it, so the stretch lasts 20 minutes. The segment from 12 to 15 lies inside, so it still lasts 20. The segment from 20 to 26 starts exactly where the stretch reaches, so it lasts 26. The segment from 30 to 45 begins a new stretch of 15 minutes.
  a["[0, 10) begins a stretch: 10 minutes"] --> b["[8, 20) overlaps: 20 minutes"]
  b --> c["[12, 15) inside: still 20 minutes"]
  c --> d["[20, 26) touches: 26 minutes"]
  d --> e["[30, 45) begins a new stretch: 15 minutes"]
```

<!-- text-of-mermaid sha256:044229ae4e6c94a0e7a7715b092a5fd5c3926dade1051e07473cb29897fe7b08 -->
```text
┌─────────────────────────────────────────┐
│   [0, 10) begins a stretch: 10 minutes  │
└────────────────────┬────────────────────┘
                     ▼
┌─────────────────────────────────────────┐
│       [8, 20) overlaps: 20 minutes      │
└────────────────────┬────────────────────┘
                     ▼
┌─────────────────────────────────────────┐
│    [12, 15) inside: still 20 minutes    │
└────────────────────┬────────────────────┘
                     ▼
┌─────────────────────────────────────────┐
│       [20, 26) touches: 26 minutes      │
└────────────────────┬────────────────────┘
                     ▼
┌─────────────────────────────────────────┐
│[30, 45) begins a new stretch: 15 minutes│
└─────────────────────────────────────────┘
```

Two details of the walk matter:

- **The reach is a maximum.** `[12, 15)` ends before the stretch reaches, so the reach stays at 20 instead of shrinking to 15.
- **Touching continues the stretch.** `[20, 26)` starts at 20, exactly the reach. With half-open segments there is no instant of silence between minute 20 of one and minute 20 of the other, so only a segment that starts after the reach, `start > reach`, begins a new stretch.

## Choosing the most intervals

One telescope receives observation requests, each a half-open interval of hours. It can serve one request at a time and wants to grant as many as possible. A greedy algorithm takes the requests in some order and grants each one that overlaps nothing granted so far. Which order? Three rules sound reasonable:

- **Earliest start**: begin as soon as possible.
- **Shortest first**: a short request blocks the least time.
- **Earliest end**: free the telescope as soon as possible.

```python examples/one_telescope.py
"""One telescope, many observation requests [start, end) in hours. Grant as many as possible with no
two overlapping. Three greedy rules take requests in a different order; only one is always best."""

from collections.abc import Callable
from itertools import combinations

Interval = tuple[int, int]
Rule = Callable[[Interval], int]

RULES: dict[str, Rule] = {
    "earliest start": lambda request: request[0],
    "shortest first": lambda request: request[1] - request[0],
    "earliest end": lambda request: request[1],
}


def overlap(first: Interval, second: Interval) -> bool:
    return first[0] < second[1] and second[0] < first[1]


def greedy(requests: list[Interval], rule: Rule) -> list[Interval]:
    granted: list[Interval] = []
    for request in sorted(requests, key=rule):
        if not any(overlap(request, kept) for kept in granted):
            granted.append(request)
    return granted


def most_by_brute_force(requests: list[Interval]) -> int:
    return max(
        size
        for size in range(len(requests) + 1)
        for chosen in combinations(requests, size)
        if not any(overlap(a, b) for a, b in combinations(chosen, 2))
    )


for requests in ([(0, 10), (1, 3), (4, 6), (7, 9)], [(0, 5), (4, 7), (6, 11)]):
    print(f"requests {requests}: best is {most_by_brute_force(requests)}")
    for name, rule in RULES.items():
        print(f"  {name:<14} grants {greedy(requests, rule)}")

every_request = [(start, end) for start in range(6) for end in range(start + 1, 6)]
inputs = [list(chosen) for size in (1, 2, 3, 4) for chosen in combinations(every_request, size)]
print(f"every set of 1 to 4 requests within hours 0 to 5: {len(inputs)} inputs")
for name, rule in RULES.items():
    wrong = sum(len(greedy(requests, rule)) < most_by_brute_force(requests) for requests in inputs)
    print(f"  {name:<14} falls short on {wrong}")
```

It prints:

```output examples/one_telescope.py
requests [(0, 10), (1, 3), (4, 6), (7, 9)]: best is 3
  earliest start grants [(0, 10)]
  shortest first grants [(1, 3), (4, 6), (7, 9)]
  earliest end   grants [(1, 3), (4, 6), (7, 9)]
requests [(0, 5), (4, 7), (6, 11)]: best is 2
  earliest start grants [(0, 5), (6, 11)]
  shortest first grants [(4, 7)]
  earliest end   grants [(0, 5), (6, 11)]
every set of 1 to 4 requests within hours 0 to 5: 1940 inputs
  earliest start falls short on 227
  shortest first falls short on 6
  earliest end   falls short on 0
```

Each wrong rule has its counterexample:

- **Earliest start** grants `[0, 10)` first, the earliest to begin, and it blocks the three short requests inside it.
- **Shortest first** grants `[4, 7)`, the shortest, which overlaps both of the requests that fit together.

Earliest end is right on both, and on all 1,940 sets of up to four requests with endpoints between 0 and 5; the other two fall short on some, with ties going to the request listed first. Shortest first fails on only 6 of them, which is why testing a few examples by hand rarely catches it. The drawing traces earliest end on the first input:

```mermaid
flowchart TD
  accTitle: Earliest end on the first input
  accDescr: Sorted by end, the requests are 1 to 3, 4 to 6, 7 to 9 and 0 to 10. The first three overlap nothing granted before them and are granted. The request from 0 to 10 overlaps the request from 1 to 3 and is refused.
  a["Sorted by end: [1, 3), [4, 6), [7, 9), [0, 10)"] --> b["grant [1, 3)"]
  b --> c["grant [4, 6): overlaps nothing granted"]
  c --> d["grant [7, 9): overlaps nothing granted"]
  d --> e["refuse [0, 10): overlaps [1, 3)"]
```

<!-- text-of-mermaid sha256:bf925e4d71db6d82de3fd81b0c7ffed15add404bfa753089b999b208b3b39af4 -->
```text
┌──────────────────────────────────────────────┐
│Sorted by end: [1, 3), [4, 6), [7, 9), [0, 10)│
└───────────────────────┬──────────────────────┘
                        ▼
┌──────────────────────────────────────────────┐
│                 grant [1, 3)                 │
└───────────────────────┬──────────────────────┘
                        ▼
┌──────────────────────────────────────────────┐
│    grant [4, 6): overlaps nothing granted    │
└───────────────────────┬──────────────────────┘
                        ▼
┌──────────────────────────────────────────────┐
│    grant [7, 9): overlaps nothing granted    │
└───────────────────────┬──────────────────────┘
                        ▼
┌──────────────────────────────────────────────┐
│       refuse [0, 10): overlaps [1, 3)        │
└──────────────────────────────────────────────┘
```

### Why the earliest end is safe

The proof is a **stays-ahead** argument, as in the [greedy choices guide](../greedy-choices/guide.md). The measure is the time at which the telescope is free again: the end of the last request granted. Every request is assumed to have `start < end`.

Let greedy grant `g1, g2, ..., gk`, in the order it granted them, which is the order of their ends. Take any set of requests that do not overlap, `o1, o2, ..., om`, listed by end; since they do not overlap, each one starts at or after the end of the one before it.

1. **Greedy stays ahead: `gi` ends no later than `oi`, for every `i` up to both lengths.** For `i = 1`, `g1` is the request that ends first of all, since nothing is granted yet to block it. Now suppose `gi` ends no later than `oi`. The request `o(i+1)` starts at or after the end of `oi`, so at or after the end of `gi`, and so after every request greedy has granted so far, since they all end by then. It ends after `gi` does, so the greedy scan reaches it after granting `gi`. Two cases. If greedy granted another request after `gi` and before reaching `o(i+1)`, that request is `g(i+1)`, and it comes earlier in end order, so it ends no later than `o(i+1)`. If not, the granted requests are still `g1` to `gi` when the scan reaches `o(i+1)`, it overlaps none of them, and greedy grants it as `g(i+1)`. Either way, greedy's next grant ends no later than `o(i+1)`.
2. **Ahead means best.** Suppose the other set is larger, `m > k`. Then `o(k+1)` starts at or after the end of `ok`, which is at or after the end of `gk`, so it overlaps none of greedy's grants and comes after `gk` in the scan. Greedy would have granted it, a `(k+1)`-th request. So `m <= k`: no set of requests that fit together is larger than greedy's.

The proof never used how ties are broken, so earliest end is safe with any tie order.

## When to use it

- **Anything with a start and an end**: bookings, time windows, byte ranges, segments of a road, versions valid from one date to another.
- **"Which overlap", "how long without a break"**: sort by start and walk once, remembering how far the intervals so far reach.
- **"The most that fit together"**: sort by end, grant what fits.
- **"How many at once"**: turn the endpoints into events and sweep them, as the [sweep line guide](../sweep-lines/guide.md) shows.

## Common traps

- **Using the other convention's test.** A half-open test on closed intervals misses intervals that share one point; a closed test on half-open ones reports touching intervals as overlapping. Find the convention in the statement and its examples before writing `<` or `<=`.
- **Sorting by the wrong end.** Start order finds what runs together; it does not choose the most. End order chooses; it does not bring overlapping intervals together.
- **Assuming an order the input does not promise.** Interval lists often arrive in no particular order. Rely on an order only when the statement guarantees it or your code has made it.
- **Empty intervals.** `[t, t)` holds no point, so it overlaps nothing, but code that only compares starts and ends may still count it. Decide whether the input can contain one, and what it means.
- **Trusting a rule that passes the examples.** Shortest first was wrong on 6 inputs out of 1,940. Compare a new rule with brute force on every small input, as the example does.

## Complexity

| Step | Time | Space |
|------|------|-------|
| Sort n intervals | O(n log n) | O(n) for `sorted`, which copies the list |
| Walk the sorted intervals once | O(n) | O(1) besides the output |
| Earliest end, written as in the example | O(n · k) for k grants, since each request is checked against every grant | O(k) |
| Check every pair for overlap | O(n²) | O(1) |
| Brute force over every subset | O(2^n · n²) | O(n) |

A more careful earliest end runs in O(n) after the sort. Either way the sort dominates, so the whole algorithm is O(n log n).

## Expert notes

- **Why half-open.** Edsger Dijkstra's note EWD831, "Why numbering should start at zero", compares the four ways to write a range of integers and prefers `a <= i < b`: the difference of the bounds is the length, two adjacent ranges share a bound, and an empty range is written without an unnatural bound. He reports that programmers of the Mesa language, which offered all four, were advised to use only this one.
- **The mirror image is safe too.** Reflect the time line, `t` to `-t`: ends become starts, and two requests overlap after the reflection exactly when they did before. So granting by **latest start**, working from the right end of the line towards the left, grants as many requests as earliest end does. For any problem that looks the same in a mirror, a rule and its mirror image are equally good, which is a quick sanity check on a new rule.
- **The same rule, other sources.** Jeff Erickson's *Algorithms*, §4.2, proves the earliest-end rule a different way, and Kevin Wayne's slides for Kleinberg and Tardos give counterexamples for earliest start and for shortest interval.

## Practice

- `cstudy start can-attend-meetings`: decide whether one person can attend every meeting of a day.
- `cstudy start merge-intervals`: replace overlapping intervals by intervals that cover the same points.
- `cstudy start insert-interval`: add one interval to a list that is already sorted and separate, and keep it that way.
- `cstudy start interval-list-intersections`: the times when two people are both free, from their two lists.
- `cstudy start coverage-gaps`: the stretches of a window that no period covers.
- `cstudy start non-overlapping-intervals`: the fewest bookings to cancel so that the rest never conflict.
- `cstudy start range-module`: track which parts of a line are covered while ranges are added, removed and queried.

## Further reading

- [Jeff Erickson, *Algorithms*, chapter 4: Greedy Algorithms](https://jeffe.cs.illinois.edu/teaching/algorithms/book/04-greedy.pdf): §4.2, scheduling classes, the earliest-end rule and its proof, and exercises with other rules.
- [Kevin Wayne, lecture slides for Kleinberg and Tardos, *Algorithm Design*, chapter 4](https://www.cs.princeton.edu/~wayne/kleinberg-tardos/pdf/04GreedyAlgorithmsI.pdf): interval scheduling and counterexamples for earliest start and shortest interval.
- [Edsger W. Dijkstra, EWD831, "Why numbering should start at zero"](https://www.cs.utexas.edu/~EWD/transcriptions/EWD08xx/EWD831.html): the case for half-open ranges.
- [Python sequence types](https://docs.python.org/3/library/stdtypes.html#sequence-types-list-tuple-range): slices `s[i:j]` hold the items with `i <= k < j`, and `range` stops before `stop`.
- [Python value comparisons](https://docs.python.org/3/reference/expressions.html#value-comparisons): sequences such as tuples compare lexicographically, element by element.
