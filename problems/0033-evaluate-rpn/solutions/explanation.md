# Evaluate Reverse Polish Notation: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| rescan | brute | O(n^2) | O(n) | short expressions, or as a correctness oracle |
| stack | optimal | O(n) | O(n) | default answer |

Here n is the number of tokens. In postfix notation, the leftmost operator always has both of its operands immediately in front of it. The brute force uses that fact by searching for the operator; the stack never needs to search, because the operands it needs are always the two most recent values.

## Approach: rescan (Reduce the leftmost operator and rescan)

### Intuition

Evaluate the expression the way you would by hand on paper: find the first operator, replace it and its two operands with the result, and start over from the beginning until a single value remains.

### Algorithm

1. Turn the tokens into a list of items: numbers become integers, operators stay as they are.
2. While more than one item remains:
   1. Scan from the front for the first operator, at position `p`.
   2. Apply it to the items at `p - 2` (left operand) and `p - 1` (right operand).
   3. Replace the three items with the result.
3. Return the remaining item.

### Correctness

In a valid postfix expression, every item before the leftmost operator is a number, and the operator's operands are the last two of them: the two most recent values. Replacing the three items by the operator's value turns the list into a valid postfix expression with the same value and one operator fewer. By induction, the loop ends with a single number, the value of the original expression.

### Complexity

- Time: O(n^2) — each of the n/2 reductions rescans from the front, up to n items, and splicing the list shifts up to n items. The generator lets the numbers pending in front of the leftmost operator grow to about half of all numbers, so the scans add up to roughly n^2/15 steps at every seed.
- Space: O(n) — the list of items.

### Trade-offs

It follows the definition and is easy to check, which suits an oracle. Most of its time is spent rescanning numbers it has already passed: exactly the numbers a stack would hold. That observation leads straight to the stack solution.

### Pitfalls and edge cases

- Recognizing operators: the token `-3` is a number, while `-` is an operator; test the whole token, not its first character.
- Truncating division: `7 / -2` must give `-3`. Python's `//` floors to `-4`, so the reference divides absolute values and restores the sign.
- A single-number expression has no operator and returns that number.

### Language notes

- Python: `isinstance(item, str)` tells operators from numbers in the mixed list; slice assignment `items[p - 2 : p + 1] = [result]` replaces three items in one step.
- TypeScript: `findIndex` locates the first operator and `splice(p - 2, 3, result)` replaces the items. `Math.trunc(left / right)` truncates toward zero.
- Java: a `List<Object>` holds both `String` operators and boxed `Integer` numbers; `subList(...).clear()` followed by `add` performs the replacement.
- Kotlin: a `List<Any>` with smart casts (`as Int`, `is String`); `indexOfFirst` finds the operator.

## Approach: stack (Stack of operands)

### Intuition

Read the tokens once, left to right. Numbers wait on a stack until an operator needs them. An operator always takes the two most recent waiting values, which are the top two entries of the stack, and its result waits for the next operator.

### Algorithm

1. Start with an empty stack.
2. For each token:
   1. If it is a number, push it.
   2. Otherwise pop `right`, then pop `left`, and push `left <op> right`.
3. Return the only value left on the stack.

### Correctness

Invariant: after processing a prefix of the tokens, the stack holds, from bottom to top, the values of the complete sub-expressions in that prefix that no operator has consumed yet. A number is such a sub-expression. An operator in a valid postfix expression combines the two most recent unconsumed sub-expressions, which are the top two entries, with the earlier one (lower on the stack) as the left operand. After the last token, the whole expression is the single unconsumed sub-expression.

### Complexity

- Time: O(n) — each token is pushed or popped a constant number of times.
- Space: O(n) — up to about n/2 operands can wait at once, for example when all numbers come first.

### Trade-offs

Linear and single-pass, and the reason postfix notation exists: it needs no precedence rules and no lookahead. It assumes a valid expression; a validating version checks for at least two operands before each operator and exactly one value at the end. A recursive evaluator that reads tokens from the end also works, but its recursion depth equals the expression's nesting, which can reach thousands for the generated inputs.

### Pitfalls and edge cases

- Pop the right operand first. Popping in the wrong order flips `-` and `/`: `8 2 /` would give 0 instead of 4.
- Use integer division that truncates toward zero; see the language notes.
- Products stay within 32 bits by the constraints, so plain `int` arithmetic is safe in Java and Kotlin.

### Language notes

- Python: a dictionary from operator to function avoids an `if` chain. `int(left / right)` would also truncate, but it goes through floating point, which is inexact for large operands; dividing absolute values with `//` is exact.
- TypeScript: `Math.trunc(left / right)` truncates toward zero; every operand is far below 2^53, so the floating-point division is exact enough for the truncation.
- Java: `ArrayDeque<Integer>` as the stack; `int` division already truncates toward zero. The `switch` over strings sends the four operators to one branch and everything else to `Integer.parseInt`.
- Kotlin: `kotlin.collections.ArrayDeque<Int>` with `addLast` and `removeLast`; `Int` division truncates toward zero, and `toInt()` parses negative numbers such as `"-3"`.
