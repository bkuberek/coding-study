# Two Sum

## Statement

You get an integer array `nums` and an integer `target`. Exactly two positions hold values that add up to `target`. Return those two positions in any order.

## Input

- `nums`: the integers to search
- `target`: the required sum

## Output

Two distinct indices `i` and `j` with `nums[i] + nums[j] == target`, in any order.

## Examples

### Example 1

<!-- case: ex1 -->

The values at positions 1 and 2 are 9 and 2, and 9 + 2 = 11.

### Example 2

<!-- case: ex2 -->

Equal values at different positions form a valid pair.

## Constraints

- `2 <= nums.length <= 10^5`
- Exactly one valid pair exists.

## Hints

### Hint 1

For each value, which partner would complete the sum?

### Hint 2

Remember the values already seen, together with their positions.
