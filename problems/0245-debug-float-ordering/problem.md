# Debug: Float Ordering

## Statement

An ad platform ranks the creatives of a campaign by click rate. Creative `i` has id `ids[i]`, was shown `impressions[i]` times and clicked `clicks[i]` times. Its click rate is `clicks[i] / impressions[i]`, and a creative that was never shown has a rate of `0`. The function `rank_creatives` you start from should return the ids from the highest rate to the lowest, and among equal rates, from the smallest id to the largest.

The code ranks established campaigns correctly. It fails on others. Find out why and fix it.

### Bug report

> **Title:** Ranking job panics after new creatives are uploaded
>
> The nightly ranking job stopped with ``called `Option::unwrap()` on a `None` value`` right after the design team uploaded fresh creatives to two campaigns. Rerunning the job gives the same panic every time. Campaigns whose creatives have all been shown at least once still rank fine, and so does a campaign with a single new creative and nothing else.

## Input

- `ids`: the id of each creative
- `impressions`: how often each creative was shown
- `clicks`: how often each creative was clicked; `clicks[i]` belongs to `impressions[i]`

## Output

The ids, by click rate from highest to lowest, ties by smaller id first.

## Examples

### Example 1

<!-- case: ex1 -->

The rates are 0.05 (id 7), 0.15 (id 3) and 0.1 (id 9). This case passes as shipped.

### Example 2

<!-- case: ex2 -->

Id 8 has the best rate, 0.2. Ids 4 and 2 both have 0.01, so the smaller id, 2, comes first. This case passes too.

## Constraints

- `1 <= ids.length <= 10^4`, and `ids`, `impressions` and `clicks` have the same length
- `1 <= ids[i] <= 10^6`, and the ids are distinct
- `0 <= clicks[i] <= impressions[i] <= 10^9`

## Follow-ups

- Rank without floating point at all, by comparing fractions with integer arithmetic. Which case still needs a special rule?
- Why does `ranked.sort()` not compile for a vector of `(i32, f64)`, while it does for `(i32, i64)`?

## Hints

### Hint 1

Find the smallest input that panics. What do the failing campaigns have that the passing ones do not?

### Hint 2

What is `0.0 / 0.0` in floating point? What does `partial_cmp` return when one side is that value?

### Hint 3

The single new creative did not panic. How many comparisons does sorting one element make?

### Hint 4

Two changes: compute the rate the statement defines for a creative that was never shown, and compare with a method that always returns an `Ordering`, such as `f64::total_cmp`.
