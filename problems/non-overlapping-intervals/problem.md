# Non-Overlapping Intervals

## Statement

You are given a list of intervals `[start, end]` with `start < end`. Think of each one as a booking of a single room from time `start` to time `end`. Two bookings conflict when their times overlap by more than an instant: a booking that ends at time 5 does not conflict with one that starts at time 5.

Cancel as few bookings as possible so that no two of the remaining ones conflict. Return how many bookings you cancel.

Reference: this is our own wording of LeetCode problem 435, [Non-overlapping Intervals](https://leetcode.com/problems/non-overlapping-intervals/).

## Input

- `intervals`: the bookings `[start, end]`, in any order

## Output

The minimum number of intervals to remove so that, for every remaining pair, one ends at or before the other starts.

## Examples

### Example 1

<!-- case: ex1 -->

Keeping `[2, 3]` and `[5, 8]` works, and so does keeping `[2, 3]` and `[3, 6]`, which only touch at 3. No three bookings can stay together: `[1, 4]` overlaps both `[2, 3]` and `[3, 6]`, and `[3, 6]` overlaps `[5, 8]`. So at least two of the four must be cancelled.

### Example 2

<!-- case: ex2 -->

Each booking starts exactly when the previous one ends, so none of them conflict and nothing is cancelled.

## Constraints

- `1 <= intervals.length <= 10^5`
- `intervals[i].length == 2`
- `-10^9 <= intervals[i][0] < intervals[i][1] <= 10^9`

## Follow-ups

- Instead of the count, can you return which intervals to keep?
- Why does keeping the interval that ends earliest never hurt? Try to write the exchange argument.
- If each booking had a price, how would you maximize the total price of the kept bookings?

## Hints

### Hint 1

Removing as few as possible is the same as keeping as many as possible. Which booking would you keep first?

### Hint 2

Among all bookings, the one that ends earliest leaves the most room for the others. Keep it, and discard everything that conflicts with it.

### Hint 3

Sort by end time. Walk the list, keeping a booking whenever it starts at or after the end of the last booking you kept. The answer is the number of bookings you skipped.
