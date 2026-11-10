# Find All Missing and Duplicate Numbers

## Statement

You get an integer array `nums` of length `n`. Every value in it is between `1` and `n`, but the array is not a tidy list of those values: some values occur more than once, and, because the array has only `n` slots, others do not occur at all.

Return two lists. The first holds every value from `1` to `n` that does not occur in `nums`. The second holds every value that occurs at least twice, each listed once, however many copies there are. Both lists are in ascending order. If nothing is missing and nothing is repeated, both lists are empty.

Do it in `O(n)` time using only `O(1)` extra memory, not counting the two lists you return. You may rearrange or overwrite `nums` in place; the caller does not read it afterwards.

## Input

- `nums`: the values to inspect, in any order; each between `1` and `nums.length`, with repeats allowed

## Output

A list of two lists of integers: first the missing values in ascending order, then the repeated values in ascending order.

## Examples

### Example 1

<!-- case: ex1 -->

The values 1, 3 and 5 occur; 2 and 4 do not, so they are missing. The values 3 and 5 each occur twice, so they are the repeated ones. Both lists are sorted.

### Example 2

<!-- case: ex2 -->

An array of length 2 can hold 1 and 2. Here both slots hold 2, so 1 is missing and 2 is repeated.

## Constraints

- `1 <= nums.length <= 10^5`
- `1 <= nums[i] <= nums.length`

## Follow-ups

- A set remembers which values you have seen, but it takes `O(n)` memory. Which array already has exactly one slot per possible value?
- Sorting the array first gives the answer in `O(n log n)` time without extra memory. What does it cost you, and what do you give up compared with a linear pass?
- Your repeated values may come out in the wrong order if you find them in the order of the missing slots. How can you list them sorted without sorting a list of up to `n / 2` values?

## Hints

### Hint 1

The values are exactly the numbers that name the positions of the array: the value `v` belongs at index `v - 1`.

### Hint 2

Walk through the array and move each value to its own index by swapping, until the value at the current position is already at home. Every swap puts one value in its final place, so there are at most `n` swaps in total.

### Hint 3

Stop swapping when the slot where the value belongs already holds the same value, not when the value is at index `i`. With a repeated value, comparing against the index never stops.

### Hint 4

After the swaps, a slot `i` that does not hold `i + 1` shows that `i + 1` is missing and that the value it holds has a copy somewhere else.
