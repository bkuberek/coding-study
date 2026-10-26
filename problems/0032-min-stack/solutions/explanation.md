# Min Stack: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| scan-min | brute | O(1) push, pop and top, O(n) getMin | O(n) | `getMin` is rare, or as a correctness oracle |
| pair-stack | optimal | O(1) per op | O(n) | default answer; simplest O(1) design |
| two-stacks | optimal | O(1) per op | O(n) | the minimum changes rarely, so the second stack stays small |

Here n is the number of elements on the stack. The key observation behind both O(1) designs: a stack only ever changes at its top, so the minimum of the elements at or below any position never changes while that position is on the stack. That value can be computed once, at push time.

## Approach: scan-min (Plain stack with a scan for the minimum)

### Intuition

Use an ordinary stack and compute the minimum on demand by looking at every element.

### Algorithm

1. `push(value)`: append `value`.
2. `pop()`: remove the last element.
3. `top()`: return the last element.
4. `getMin()`: scan all elements and return the smallest.

### Correctness

The list holds exactly the stack's elements in push order, so the last element is the top and the smallest element of the list is the stack's minimum.

### Complexity

- Time: O(1) push, pop and top, O(n) getMin — `getMin` reads every element. In the generated sequences, a fifth of the calls are `getMin` on a stack of up to about 0.3 times the number of calls, so a sequence of length n costs on the order of n^2 reads.
- Space: O(n) — one slot per element.

### Trade-offs

Correct and minimal, which makes it the oracle; fine if `getMin` is rare. It fails the O(1) requirement, and with 100,000 calls it reads several hundred million elements. A cached minimum alone does not fix it: after popping the minimum, the new one is unknown without a scan.

### Pitfalls and edge cases

- Caching only the current minimum breaks on `pop`: the next minimum must be recomputed by a scan.

### Language notes

- Python: `min(self.values)` scans in C.
- TypeScript: the reference loops instead of calling `Math.min(...values)`, because spreading 10^5 arguments into one call can exceed the engine's argument limit.
- Java: `Collections.min(values)` scans and unboxes; `values.remove(values.size() - 1)` removes by position.
- Kotlin: `minOf { it }` scans; `removeAt(lastIndex)` pops from an `ArrayList`.

## Approach: pair-stack (Each entry stores the minimum at or below it)

### Intuition

Store, with every element, the minimum of that element and all elements below it. The entry on top then carries the minimum of the whole stack. Popping restores the previous minimum automatically, because the entry below still carries its own.

### Algorithm

1. `push(value)`: let `minimum = value` if the stack is empty, else `min(value, top entry's minimum)`; push `(value, minimum)`.
2. `pop()`: remove the top entry.
3. `top()`: return the top entry's value.
4. `getMin()`: return the top entry's minimum.

### Correctness

Invariant: the entry at position `i` stores the minimum of the values at positions `0..i`. A push extends the invariant by one position: the minimum of `0..i+1` is the smaller of the new value and the minimum of `0..i`. A pop removes the top entry without touching the others, so the invariant still holds for every remaining position. `getMin` reads the stored minimum of the whole stack.

### Complexity

- Time: O(1) per op — every operation touches only the top.
- Space: O(n) — two integers per element.

### Trade-offs

The simplest O(1) design and the easiest to argue correct, so it is the usual interview answer. It always stores two values per element, even when the minimum never changes; the two-stack variant saves that space in such cases.

### Pitfalls and edge cases

- The first push has no entry below it; its minimum is its own value.
- Equal values need no special care: each entry carries its own copy of the minimum.

### Language notes

- Python: a list of `(value, minimum)` tuples.
- TypeScript: two parallel arrays avoid allocating a small object per push; they always have the same length.
- Java: an `ArrayDeque<int[]>` of two-element arrays; `push`, `pop` and `peek` work at the head of the deque.
- Kotlin: a private `data class Entry` in a `kotlin.collections.ArrayDeque`; `lastOrNull()?.let { ... } ?: value` handles the empty stack in one expression.

## Approach: two-stacks (A second stack of minimums)

### Intuition

Most pushes do not change the minimum. Keep a second stack that receives a value only when it becomes the new minimum, or ties the current one. Its top is always the current minimum, and when the value popped from the main stack equals that top, the minimum stack pops too.

### Algorithm

1. `push(value)`: push onto `values`; if `minimums` is empty or `value <= minimums.top`, push onto `minimums` as well.
2. `pop()`: pop from `values`; if the popped value equals `minimums.top`, pop `minimums`.
3. `top()`: return `values.top`.
4. `getMin()`: return `minimums.top`.

### Correctness

Invariant: `minimums` holds, from bottom to top, the elements of `values` that were less than or equal to every element below them when pushed, and its top is the minimum of `values`. A push of `value <= minimum` makes `value` the new minimum and records it; a larger value changes nothing. On a pop, if the popped value equals the recorded minimum, it is the most recent recorded copy (every later push was larger, or would have been recorded too), so removing it reveals the minimum of the remaining elements. Using `<=` records every copy of an equal minimum, so popping one copy leaves the others recorded.

### Complexity

- Time: O(1) per op — constant work at the tops of the two stacks.
- Space: O(n) — up to two values per element in the worst case (a strictly decreasing sequence); much less when the minimum rarely changes.

### Trade-offs

Same time as the pair stack, and less memory on typical inputs. The equal-values rule is a classic source of bugs, so it needs a sentence in an interview. An O(1)-extra-space variant stores differences from the minimum instead of values, but it needs 64-bit arithmetic to avoid overflow with 32-bit inputs and is rarely worth the complexity.

### Pitfalls and edge cases

- Using `<` instead of `<=` loses duplicates: push 2, push 2, pop leaves the minimum stack empty although a 2 remains.
- In Java, comparing two `Integer` objects with `==` compares references, which works only inside the small-integer cache (-128 to 127). Unbox to `int` first, as the reference does.

### Language notes

- Python: two lists; `self.values.pop() == self.minimums[-1]` compares values.
- TypeScript: `pop()` returns the removed value, compared with `===` against the last minimum.
- Java: two `ArrayDeque<Integer>`; `int value = values.pop()` unboxes before the comparison with `minimums.peek()`.
- Kotlin: `==` on `Int` compares values even when they are stored boxed in a generic `ArrayDeque<Int>`, so the Java pitfall does not apply.
