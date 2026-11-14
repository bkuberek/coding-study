# Maximum Average of a Fixed Window

## Statement

A bakery writes down its takings for each day in a row, in order. The owner wants to know which stretch of exactly `k` days in a row went best. In programming terms, a run of neighbouring numbers of a fixed length is called a window: the window of width 3 that starts at position 0 holds the numbers at positions 0, 1 and 2, the next one holds positions 1, 2 and 3, and so on. Sliding the window one step to the right drops its first number and picks up one new number at the end.

The average of a window is the sum of its numbers divided by `k`. Given the array `nums` and the width `k`, return the largest average that any window of width `k` has.

The numbers can be negative, and so can the answer.

Reference: this is our own wording of LeetCode problem 643, [Maximum Average Subarray I](https://leetcode.com/problems/maximum-average-subarray-i/).

## Input

- `nums`: the numbers, in order.
- `k`: the width of the window; every window has exactly `k` numbers, so a run that is shorter than `k` does not count.

## Output

The largest window average, as a floating-point number: the exact sum of the best window divided by `k`, with no rounding to a whole number. An answer is accepted when its difference from the exact value is at most `10^-5` times the larger of 1 and the exact value's size, so any usual `double` arithmetic is fine.

## Examples

### Example 1

<!-- case: ex1 -->

There are four windows of width 4, with sums 14, 9, 14 and 12. The largest sum is 14, which two windows reach, and 14 divided by 4 is 3.5. The other windows average 2.25 and 3.0, so they do not beat it.

### Example 2

<!-- case: ex2 -->

There are three windows of width 2, with sums -8, -11 and -13. The largest of them is -8, so the answer is -4.0. If you started your running best at 0, you would wrongly answer 0.

## Constraints

- `1 <= k <= nums.length <= 10^5`
- `-10^4 <= nums[i] <= 10^4`

## Follow-ups

- Adding up a window from scratch costs `k` steps, and there are about `n` windows. Can you reach the answer in a single pass, with a constant amount of extra memory?
- Which window would you report if you also had to return where it starts?
- What changes if the window width is not fixed, and you want the shortest stretch whose sum reaches a given total?

## Hints

### Hint 1

Do it by hand on the first example. Write down the sum of the first window, then the sum of the second. How do the two windows differ, and how much of the work for the first window can you reuse?

### Hint 2

Every window has the same number of values, `k`. When you compare two windows, dividing both sums by the same `k` does not change which is bigger. So you can compare sums, and divide only once at the end.

### Hint 3

When the window slides one step to the right, exactly one number enters it and exactly one number leaves it. The new sum is the old sum, plus the number that entered, minus the number that left.

### Hint 4

Compute the sum of the first `k` numbers directly and take it as your best so far. Then slide the window one step at a time, updating the sum with the one number that enters and the one that leaves, and keep the largest sum seen. Start the best from the first window, not from 0, or all-negative inputs go wrong. Return the best sum divided by `k`.
