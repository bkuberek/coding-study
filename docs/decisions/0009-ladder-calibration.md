# ADR 0009: Calibrating the ladder check against measured references

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-10-24 |
| Amends | [ADR 0005](0005-empirical-complexity-analysis.md) |
| Spec | [performance-analysis](../specs/performance-analysis.md#empirical-classification) |

## Context

The first catalog run of `cstudy verify --oracle --ladder --require-ready` failed the ladder on 28 problems whose references are correct, with 96 contradiction lines. Raw per-size medians of the failing references, measured again and re-judged offline, showed four causes (some lines have two):

| Cause | Evidence | Lines |
|-------|----------|-------|
| Exponential false positives | On a narrow ladder `log(time)` fits about as well against n as against log n, and the local slopes of a fixed cost plus polynomial growth rise; slopes from 0.28 to 1.34 were reported as `~2^n` | 13 |
| Memory effects below linear | O(log n) references measured slopes from 0.28 to 0.58. On the JVM a binary search takes 9 to 11 ns at n=100 and 60 to 90 ns from n=200 on, then stays nearly flat: tiny inputs, laid out back to back, stream through the cache; larger ones do not | 27 |
| Narrow ladders | The cost per unit of growth wanders by 2 to 4 times across a ladder (cache levels, background load, the per-seed choice of input family). Over three decades that moves the slope by about 0.15; over one decade, by up to 0.6, more than a band is wide | most of the rest |
| Content | Generators that do not reach the declared worst case on random inputs; a fixed-size problem with a size ladder | the remainder, listed per problem in the run report |

A fixed per-call cost, the suspected cause, explains almost none of them. It bends the log-log curve upward at the small sizes; memory effects bend it upward at the large sizes, and the two look the same. A classifier that fits `a + b * g(n)` per class and picks the best fit (an overhead-aware fit) made 51 contradictions on the same 123 measured series, against 39 for the slope bands: it read the large-size steepening of linear references as `n^1.5`.

## Decision

- **Exponential needs super-polynomial evidence.** The local slope between the two largest sizes must reach 3.4, the top of the cubic band; `a + b * n^k` with a, b >= 0 never has a local slope above k, so a fixed cost plus a declared polynomial class can no longer read as `~2^n`. Beyond that the curve must accelerate (rising local slopes and a better semi-log fit, the earlier rule).
- **Steeper than cubic is exponential.** A fitted slope of 3.4 or more is band X; the former band H (`>n^3`) is gone. On ladders such as n = 6, 7, 8 for n-queens, local slopes of 10 are too even to show acceleration and the semi-log and log-log fits are both nearly perfect, so the acceleration test called them `>n^3` at random; JVM warmup on n = 6, 8, 10 can also make the top step of a subset enumeration the flattest. No declared polynomial class is steeper than n^3, so the ladder check loses nothing; a user solution of n^4 reads as `~2^n`, still worse than every polynomial band.
- **One sublinear band.** Constant, logarithmic and square-root growth share band A (slope below 0.75), as n and n log n share band C. Distinguishing sublinear classes is not reliable; telling them from linear is.
- **The ladder check tolerates drift.** A band that differs from the declared class's band is a contradiction only when the class cannot explain the times: for every fixed cost a >= 0 small enough that the class term dominates the three largest fitted sizes, `time / (a + g(n))` varies by more than a factor of 4 across those sizes. Otherwise the check is `tolerated`: reported as a warning that names the factor, never a failure. The fixed cost stands for lower-order terms as well as call overhead, which is what O(g) allows.
- **Slope bands still classify.** The bench table, the verdict and its confidence keep the log-log slope; the drift test only decides whether a mismatch with a declared class is a contradiction.

## Consequences

- The ladder gate can no longer separate neighbouring classes on a ladder spanning about one decade: n^1.5 against n^2 over 1,000 to 10,000 varies only 3.2x. Ladders that span two or more decades keep the gate sharp; the warning says when a ladder does not.
- A user's O(sqrt n) solution against an O(log n) optimal lands in the same band and is judged by the ratio to the optimal reference and its trend, like n log n against n.
- The tolerance of 4 (`DRIFT_TOLERANCE`) comes from the re-measured failing problems at a load of 3 to 5.5 on 11 cores: references whose class is not in doubt drifted at most 2.9x, the remaining contradictions, all traced to generators or ladders, 4.0x to 7.1x. Some content issues stay below it (a fixed-size board at 3.8x) and surface only as warnings.
- No measurement changes: the runners, the sampling and the stored bench rows stay as they are.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Pick the class whose `a + b * g(n)` fits best, with an Occam penalty | More contradictions on real data (51 against 39 of 123 series): memory steepening at large sizes looks like a fixed cost with a steeper class |
| Subtract a measured empty-call baseline | Call overhead is 10 to 200 ns per call; it would not move any failing slope, and it needs a protocol change in three runners |
| Drop sizes within k times of an overhead floor | No floor is measured, and for sublinear calls every size is within a few times of it |
| Wider bands | Loses n against n^2 on wide ladders, where the slope is reliable |
| Randomize the call order inside a sample to defeat streaming | Changes three runners for one artifact of sublinear calls, which the merged band already absorbs |
