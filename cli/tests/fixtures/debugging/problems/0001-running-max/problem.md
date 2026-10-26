# Running Maximum

## Statement

The code you start from should return, for every position of `nums`, the largest value seen up to and including that position. It passes some tests and fails others. Find the bug and fix it.

## Input

- `nums`: the integers, in order

## Output

An array of the same length whose element `i` is the maximum of `nums[0..i]`.

## Examples

### Example 1

<!-- case: ex1 -->

The maximum grows to 3 and stays there.

### Example 2

<!-- case: ex2 -->

With only negative values the running maximum is negative too.

## Constraints

- `1 <= nums.length <= 10^4`
- `-2^31 <= nums[i] <= 2^31 - 1`

## Hints

### Hint 1

Which inputs fail? What do they have in common?

### Hint 2

What is the maximum before the first element is read?
