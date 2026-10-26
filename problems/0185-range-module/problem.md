# Range Module

## Statement

Track which parts of the number line are covered. The line starts empty; ranges can be added to the covered set, removed from it, and queried. All ranges are half-open: `[left, right)` contains every real number `x` with `left <= x < right`, so `[3, 5)` and `[5, 8)` touch but do not overlap, and together they cover `[3, 8)`.

Implement the class `RangeModule`:

- `RangeModule()` starts with nothing covered.
- `addRange(left, right)` covers every point of `[left, right)`, whether or not parts of it were covered before.
- `queryRange(left, right)` returns `true` if every point of `[left, right)` is currently covered, and `false` if any point of it is not.
- `removeRange(left, right)` uncovers every point of `[left, right)` that is covered.

Reference: this is our own wording of LeetCode problem 715, [Range Module](https://leetcode.com/problems/range-module/).

## Input

- Constructor: no arguments.
- `addRange(left, right)`, `queryRange(left, right)`, `removeRange(left, right)`: the ends of a half-open range, with `left < right`.

Each test is a sequence of calls: the constructor first, then the other methods in order.

## Output

- `queryRange` returns whether the whole range is covered.
- `addRange` and `removeRange` return nothing.

The expected output lists one result per call, with `null` for the constructor and for every `addRange` and `removeRange`.

## Examples

### Example 1

<!-- case: ex1 -->

After adding `[2, 6)` and `[6, 9)`, the touching ranges cover `[2, 9)` without a gap, so `[4, 8)` is covered. Removing `[5, 7)` leaves `[2, 5)` and `[7, 9)`: `[2, 5)` is still covered, but `[4, 8)` now contains uncovered points, and so does `[5, 7)`.

### Example 2

<!-- case: ex2 -->

Nothing is covered at first, so the first query is `false`. Adding `[1, 100)` and then removing `[1, 50)` leaves `[50, 100)`. A query must lie completely inside the covered part: `[60, 100)` does, `[49, 51)` does not.

## Constraints

- `1 <= left < right <= 10^9`
- At most `3 * 10^4` calls in total to `addRange`, `queryRange` and `removeRange`.

## Follow-ups

- Keeping a sorted list of disjoint intervals makes every call O(k) for k intervals. Can each call cost O(log) of something?
- How would you report the total covered length after each call?
- What changes if ranges are closed, `[left, right]`, on integers?

## Hints

### Hint 1

Keep the covered set as disjoint intervals in sorted order. Adding merges every interval that overlaps or touches the new one; removing trims or splits the intervals it overlaps.

### Hint 2

A query is covered exactly when one stored interval contains it, because stored intervals never touch.

### Hint 3

For logarithmic calls, build a segment tree over `[1, 10^9)` lazily: a node is fully covered, fully uncovered or mixed. Assigning a state to a range only splits the nodes along its two boundaries, and a query only descends into mixed nodes.
