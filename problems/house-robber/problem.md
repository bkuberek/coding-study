# House Robber

## Statement

Houses stand in a single row along a street, and `nums[i]` is the amount of cash hidden in house `i`. A burglar wants to collect as much cash as possible in one night, but neighboring houses share an alarm: taking cash from two houses that are next to each other in the row sets it off.

Return the largest total the burglar can collect from a set of houses in which no two chosen houses are adjacent. Choosing no house at all is allowed and collects 0.

Reference: this is our own wording of LeetCode problem 198, [House Robber](https://leetcode.com/problems/house-robber/).

## Input

- `nums`: the cash in each house, in street order

## Output

The maximum total over all sets of pairwise non-adjacent houses.

## Examples

### Example 1

<!-- case: ex1 -->

Taking houses 1 and 4 collects 8 + 6 = 14. Taking every other house from the start (3 + 4 + 6 = 13) collects less.

### Example 2

<!-- case: ex2 -->

The two outer houses are not adjacent, so both can be taken for 5 + 5 = 10; skipping two houses in a row is sometimes necessary.

## Constraints

- `1 <= nums.length <= 2000`
- `0 <= nums[i] <= 10^4`

## Follow-ups

- Trying every subset of houses takes exponential time. What smaller question does each house leave you with once you decide to take it or skip it?
- Can you solve it with constant extra memory?
- How would you handle a street that loops around, where the first and the last house are also neighbors?

## Hints

### Hint 1

Look at the last house. Either it is skipped, or it is taken and the house before it must be skipped.

### Hint 2

Let `best(i)` be the most cash obtainable from the first `i` houses. Then `best(i) = max(best(i - 1), best(i - 2) + nums[i - 1])`.

### Hint 3

The recurrence only looks two positions back, so two running totals replace the whole table.
