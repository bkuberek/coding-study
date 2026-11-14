# Top K Frequent Elements

## Statement

You get an integer array `nums` and an integer `k`. Count how many times each distinct value occurs, and return the `k` values with the highest counts.

The inputs are chosen so that the answer is unambiguous: every value in the answer occurs strictly more often than every value left out. Values inside the answer may share a count, and they may be returned in any order.

Reference: this is our own wording of LeetCode problem 347, [Top K Frequent Elements](https://leetcode.com/problems/top-k-frequent-elements/).

## Input

- `nums`: the values to count
- `k`: how many of the most frequent distinct values to return

## Output

An array of `k` distinct values from `nums`: the ones with the highest counts, in any order.

## Examples

### Example 1

<!-- case: ex1 -->

The value 4 occurs three times and 6 occurs twice; 2 and 9 occur once each. The two most frequent values are 4 and 6.

### Example 2

<!-- case: ex2 -->

There are only two distinct values and `k` is 2, so both are returned, even though 2 occurs more often than 9. The order of the answer does not matter.

## Constraints

- `1 <= nums.length <= 10^5`
- `-10^4 <= nums[i] <= 10^4`
- `1 <= k <=` the number of distinct values in `nums`
- The `k`-th highest count is strictly greater than the next one, so the answer is unique.

## Follow-ups

- Sorting the distinct values by count takes O(n log n) time. Can you do better when `k` is small?
- A count is never larger than `n`. How can that bound give you an O(n) solution?
- How would you maintain the top `k` values while new numbers keep arriving?

## Hints

### Hint 1

Start by counting: a hash map from value to count turns the problem into "pick the `k` largest counts".

### Hint 2

You do not need the full order of all counts. A min-heap that never holds more than `k` entries keeps exactly the `k` largest seen so far.

### Hint 3

Every count is between 1 and `n`. Put each value into a bucket indexed by its count, then read the buckets from the highest count down.
