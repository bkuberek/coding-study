# Min Stack

## Statement

Build a stack of integers that, besides the usual operations, can report its smallest element at any moment. Implement the class `MinStack`:

- `MinStack()` creates an empty stack.
- `push(value)` puts `value` on top of the stack.
- `pop()` removes the element on top of the stack.
- `top()` returns the element on top of the stack without removing it.
- `getMin()` returns the smallest element currently in the stack, without removing anything.

Every method should run in O(1) time. The tests never call `pop`, `top` or `getMin` on an empty stack.

Reference: this is our own wording of LeetCode problem 155, [Min Stack](https://leetcode.com/problems/min-stack/).

## Input

- Constructor: no arguments.
- `push(value)`: `value` is the integer to put on top.
- `pop()`, `top()`, `getMin()`: no arguments.

Each test is a sequence of calls: the constructor first, then the other methods in order.

## Output

- `top` returns the element on top of the stack.
- `getMin` returns the smallest element in the stack.
- `push` and `pop` return nothing.

The expected output of a test lists one result per call, with `null` for the constructor, `push` and `pop`.

## Examples

### Example 1

<!-- case: ex1 -->

After pushing 6, 2 and 9, the minimum is 2 and the top is 9. Popping 9 and then 2 leaves only 6, which is now both the minimum and the top.

### Example 2

<!-- case: ex2 -->

The value -4 is pushed twice. Popping the upper copy must not lose track of the lower one: the minimum stays -4 until both copies are gone, and here one copy remains to the end.

## Constraints

- `-2^31 <= value <= 2^31 - 1`
- `pop`, `top` and `getMin` are only called when the stack is not empty.
- At most `10^5` calls in total.

## Follow-ups

- Scanning the stack for the minimum takes O(n). What could you store at push time so that `getMin` becomes O(1)?
- Can you store fewer extra values than one per element when the minimum rarely changes?
- How would you build a queue that reports its minimum in O(1) amortized time?

## Hints

### Hint 1

When you pop, the minimum can change, and you need to know what it was before the popped element arrived.

### Hint 2

The minimum of the stack depends only on the elements below the top and the top itself. Remember, next to each element, the minimum of everything at or below it.

### Hint 3

Alternatively, keep a second stack that receives a value only when it is less than or equal to the current minimum. Think carefully about equal values.
