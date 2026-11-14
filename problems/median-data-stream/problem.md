# Median of a Data Stream

## Statement

Numbers arrive one at a time, and at any moment you may be asked for the median of all numbers received so far. The median of a sorted collection is its middle value when the count is odd, and the average of its two middle values when the count is even: the median of `1, 4, 10` is `4`, and the median of `4, 10` is `7`.

Implement the class `MedianFinder`:

- `MedianFinder()` creates an empty collection.
- `addNum(num)` adds the integer `num` to the collection.
- `findMedian()` returns the median of all numbers added so far, as a floating-point number.

The tests never call `findMedian` before the first `addNum`. Answers within `10^-6` of the exact median are accepted.

Reference: this is our own wording of LeetCode problem 295, [Find Median from Data Stream](https://leetcode.com/problems/find-median-from-data-stream/).

## Input

- Constructor: no arguments.
- `addNum(num)`: the next number of the stream.
- `findMedian()`: no arguments.

Each test is a sequence of calls: the constructor first, then the methods in order.

## Output

- `findMedian` returns the current median as a floating-point number.
- The constructor and `addNum` return nothing.

The expected output of a test lists one result per call, with `null` for calls that return nothing.

## Examples

### Example 1

<!-- case: ex1 -->

After 4 and 10 the collection has an even count, so the median is their average, 7.0. Adding 1 makes the sorted collection `1, 4, 10`, whose middle value is 4.

### Example 2

<!-- case: ex2 -->

The median after each addition: -3 alone; the average of -8 and -3, which is -5.5; the middle of `-8, -3, 6`, which is -3; and the average of the two middle values of `-8, -3, 0, 6`, which is -1.5.

## Constraints

- `-10^5 <= num <= 10^5`
- `findMedian` is called only after at least one `addNum`.
- At most `10^5` calls in total.

## Follow-ups

- Keeping the numbers sorted makes `findMedian` trivial. What does each `addNum` cost then?
- Can you make both operations faster than linear?
- If every number is between 0 and 100, how would you do it? What if 99% of them are?

## Hints

### Hint 1

The median only depends on the middle of the sorted order. You never need the full order of the smaller half or of the larger half, only their extremes.

### Hint 2

Keep the smaller half in a max-heap and the larger half in a min-heap. The median comes from their tops.

### Hint 3

After each insertion, rebalance so that the halves differ in size by at most one, and so that every value in the lower half is at most every value in the upper half. Sending each new number through one heap into the other maintains the second rule for free.
