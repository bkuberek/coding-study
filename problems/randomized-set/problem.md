# Randomized Set

## Statement

Build a set of integers that supports adding a value, removing a value and drawing a random member, each in constant average time. Implement the class `RandomizedSet`:

- `RandomizedSet()` creates an empty set.
- `insert(value)` adds `value` if it is not already present. It returns `true` when the value was added and `false` when it was already there.
- `remove(value)` deletes `value` if it is present. It returns `true` when the value was deleted and `false` when it was not in the set.
- `getRandom()` returns one member of the set, chosen uniformly at random: with `k` members, each is returned with probability `1/k`.

Aim for O(1) average time per call, for all three methods.

The output of `getRandom` is random, so the automated tests only call it while the set holds exactly one value, when the result is predictable. Your implementation must still choose uniformly whatever the size of the set.

Reference: this is our own wording of LeetCode problem 380, [Insert Delete GetRandom O(1)](https://leetcode.com/problems/insert-delete-getrandom-o1/).

## Input

- Constructor: no arguments.
- `insert(value)`: `value` is the integer to add.
- `remove(value)`: `value` is the integer to delete.
- `getRandom()`: no arguments.

Each test is a sequence of calls: the constructor first, then `insert`, `remove` and `getRandom` calls in order.

## Output

- `insert` and `remove` return whether they changed the set.
- `getRandom` returns a member of the set.

The expected output of a test lists one result per call, with `null` for the constructor.

## Examples

### Example 1

<!-- case: ex1 -->

Inserting 8 and 3 succeeds; inserting 8 again changes nothing and returns `false`. After 3 is removed, 8 is the only member, so `getRandom` must return 8. Removing 5, which was never added, returns `false`.

### Example 2

<!-- case: ex2 -->

Removing from an empty set returns `false`. Each `getRandom` call happens while exactly one value is present: first 1, then, after 1 is removed and 2 inserted, 2.

## Constraints

- `-2^31 <= value <= 2^31 - 1`
- At most `10^5` calls to `insert`, `remove` and `getRandom` in total.
- `getRandom` is only called when the set is not empty.

## Follow-ups

- A hash set gives O(1) `insert` and `remove`, but how would it pick a uniformly random member in O(1)?
- An array gives O(1) random access, but removing from its middle is O(n). How can you remove without shifting elements?
- How would you allow duplicates, so that `getRandom` returns each value with probability proportional to how many copies are stored?

## Hints

### Hint 1

Picking a uniformly random element is easy in an array: choose a random index.

### Hint 2

To find a value inside the array quickly, keep a hash map from each value to its index.

### Hint 3

The order of the array does not matter. To remove a value, move the last element into its slot, update that element's index in the map, and shrink the array by one.
