# Interval List Intersections

## Statement

Two people each keep a list of the times they are free. Each list is a sequence of closed intervals `[start, end]` sorted by start and pairwise separate: every interval ends strictly before the next one in the same list begins.

Return the times when both people are free: every non-empty intersection of an interval from `firstList` with an interval from `secondList`, sorted by start. Because the intervals are closed, two intervals that only touch at one point intersect in that single point, written `[t, t]`.

Reference: this is our own wording of LeetCode problem 986, [Interval List Intersections](https://leetcode.com/problems/interval-list-intersections/).

## Input

- `firstList`: sorted, pairwise separate intervals; may be empty
- `secondList`: sorted, pairwise separate intervals; may be empty

## Output

The list of all non-empty intersections, sorted by start. These intersections never share a point with each other, so the order is unique.

## Examples

### Example 1

<!-- case: ex1 -->

`[3, 7]` meets `[1, 4]` in `[3, 4]` and `[6, 9]` in `[6, 7]`. `[9, 13]` touches `[6, 9]` only at 9, giving the single point `[9, 9]`, and overlaps `[12, 15]` in `[12, 13]`.

### Example 2

<!-- case: ex2 -->

The second person is never free, so there are no common times and the answer is empty.

## Constraints

- `0 <= firstList.length, secondList.length <= 10^5`
- every interval has length 2 and satisfies `0 <= start <= end <= 10^9`
- within each list, `list[i][1] < list[i + 1][0]` for every valid `i`

## Follow-ups

- Comparing every pair is easy. Since both lists are sorted, can you get away with a single pass over each?
- How would you intersect `k` lists at once?

## Hints

### Hint 1

The intersection of `[a, b]` and `[c, d]` is `[max(a, c), min(b, d)]` when that start is not after that end, and empty otherwise.

### Hint 2

Keep one pointer into each list. After intersecting the two current intervals, one of them can no longer intersect anything that comes later in the other list. Which one?

### Hint 3

Advance the pointer of the interval that ends first: every later interval in the other list starts after the current interval of that other list, which already reaches at least as far.
