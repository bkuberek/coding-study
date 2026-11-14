# Basic Calculator: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reduce-and-splice | brute | O(n^2) | O(n) | short expressions, or as a correctness oracle |
| stack | optimal | O(n) | O(n) | default answer; extends naturally to parentheses |
| running-term | optimal | O(n) | O(1) | the follow-up asks for constant memory |

Here n is the length of the expression. Without parentheses, an expression is a sum of signed terms, and each term is a left-to-right chain of `*` and `/`: `20 / 6 - 3 * 2 + 1` is `3 + (-6) + 1`. All three approaches evaluate that structure; they differ in how much of it they keep around.

## Approach: reduce-and-splice (Reduce the leftmost operator of each precedence level)

### Intuition

Evaluate the way precedence is taught: first apply every `*` and `/`, always the leftmost one, then every `+` and `-`, again leftmost first. Each application replaces two numbers and an operator with one number.

### Algorithm

1. Split the expression into numbers and operators, dropping spaces.
2. For the level `*`, `/` and then the level `+`, `-`:
   1. Find the leftmost operator of that level by scanning from the front.
   2. Apply it to the numbers on its left and right, replace the two numbers with the result and delete the operator.
   3. Repeat until no operator of that level remains.
3. Return the single remaining number.

### Correctness

Applying the leftmost operator of the highest remaining precedence is exactly what precedence plus left-to-right associativity prescribe: no other operator binds its two neighbors more tightly, and every operator of the same level to its left has already been applied. Each step produces an equivalent, shorter expression, so the last remaining number is the value.

### Complexity

- Time: O(n^2) — up to n/2 reductions, each with a scan from the front and a splice that shifts the rest of the lists. About half of the generated operators are `*` or `/`, and each scan passes all the `+` and `-` operators in front of the next one, so the work grows with n^2 at every seed.
- Space: O(n) — the lists of numbers and operators.

### Trade-offs

A direct transcription of the precedence rules, which makes it a reliable oracle. It rescans and reshuffles lists that the one-pass approaches never revisit; at 10,000 operands that is tens of millions of steps against about 50,000.

### Pitfalls and edge cases

- Reducing the leftmost operator overall, ignoring precedence, gives `(4 + 6) * 2 = 20` for `4 + 6 * 2`.
- Within a level, order matters: `8 / 3 * 3` is `(8 / 3) * 3 = 6`, not `8 / (3 * 3) = 0`.

### Language notes

- Python: `re.findall(r"\d+|[-+*/]", s)` tokenizes and skips spaces; `list.index` finds each operator in C.
- TypeScript: `s.match(/\d+|[-+*/]/g)` tokenizes; `splice` replaces items in place.
- Java: a hand-written tokenizer feeds a `List<Integer>` and a `List<Character>`; `remove(int)` removes by position.
- Kotlin: `Regex.findAll` tokenizes; `removeAt` and indexed assignment update the lists.
- Go: a hand-written tokenizer walks the bytes, as in Java. `slices.IndexFunc` finds the first operator of a level, and `slices.Delete` removes an entry and shifts the tail, which keeps each reduction O(n).
- Rust: the tokenizer walks `s.bytes()` and matches `b'0'..=b'9'`. `iter().position` finds the first operator of a level and `Vec::remove` shifts the tail, so each reduction is O(n).

## Approach: stack (Stack of signed terms)

### Intuition

Read the expression once and remember the operator in front of the current number. A `+` or `-` starts a new term, so push the number (negated for `-`). A `*` or `/` belongs to the term on top of the stack, so apply it to that term right away. At the end, the stack holds the signed terms, and their sum is the answer.

### Algorithm

1. Set `operator = '+'`, `number = 0` and an empty stack.
2. For each character `c` (index `i`):
   1. If `c` is a digit, set `number = number * 10 + digit`.
   2. If `c` is an operator, or `i` is the last index:
      - For `+`, push `number`; for `-`, push `-number`.
      - For `*`, replace the top with `top * number`; for `/`, replace it with `top / number`, truncated toward zero.
      - Set `operator = c` and `number = 0`.
3. Return the sum of the stack.

### Correctness

Invariant: after the number in front of each operator is processed, the stack holds the signed terms seen so far, the top one possibly still unfinished. Each `*` or `/` binds only to the term it follows, which is the top, and applies in left-to-right order. Each `+` or `-` ends the current term and starts a new one with the right sign. After the last number, every term is complete, and the expression equals their sum. Pushing `-number` is equivalent to subtracting the term because `-(a * b) = (-a) * b` and, with truncation toward zero, `-(a / b) = (-a) / b`.

### Complexity

- Time: O(n) — one pass with O(1) work per character, plus the final sum.
- Space: O(n) — up to one term per operand.

### Trade-offs

The standard answer, and the one that extends to parentheses: on `(`, push the current state and start fresh; on `)`, collapse the inner result into the outer term. It keeps every term even though only the last can still change, which the running-term approach exploits.

### Pitfalls and edge cases

- Flush the last number: the final operand is not followed by an operator, hence the `i == last index` test. Testing the character, not just the index, also handles trailing spaces.
- Division of a negative term must truncate toward zero: `5 - 7 / 2` pushes `-7` and then divides by 2, which must give `-3`, not `-4`. Python's `//` floors, so the reference divides absolute values.
- Spaces must neither end a number nor count as an operator.

### Language notes

- Python: `character.isdigit()` and an explicit truncating division helper; `sum(terms)` adds the stack.
- TypeScript: `Math.trunc` truncates toward zero; `charCodeAt(0) - 48` converts a digit.
- Java: an `ArrayDeque<Integer>` as the stack; `int` division truncates toward zero. The sum walks `descendingIterator()`, bottom to top, which is the order of the expression.
- Kotlin: `kotlin.collections.ArrayDeque<Int>`; `character - '0'` converts a digit to an `Int`, and `terms.sum()` adds the deque from first to last.
- Go: `terms[last] *= number` changes the top term in place, and `/` on `int` truncates toward zero. The final loop adds the terms from first to last.
- Rust: `*terms.last_mut().unwrap() *= number` changes the top term in place. `terms.iter().sum()` adds from first to last, the same order as Java's `descendingIterator`; cstudy builds Rust with overflow checks, so a sum that wrapped silently in Java would panic instead.

## Approach: running-term (Running total and pending term)

### Intuition

Only the most recent term can still change; all earlier terms are final. Replace the stack with two numbers: `total`, the sum of the finished terms, and `term`, the signed term still being built.

### Algorithm

1. Set `total = 0`, `term = 0`, `number = 0`, `operator = '+'`.
2. For each character, update `number` on digits. On an operator or at the last index:
   - For `+` or `-`, add `term` to `total`, then start `term = number` or `-number`.
   - For `*`, set `term = term * number`; for `/`, set `term = term / number`, truncated toward zero.
   - Set `operator` to the character and reset `number`.
3. Return `total + term`.

### Correctness

This is the stack approach with the stack represented by the sum of all entries below the top (`total`) and the top itself (`term`). Every stack operation only pushes a new top or replaces the top, so the representation stays exact; the final sum of the stack is `total + term`.

### Complexity

- Time: O(n) — one pass with O(1) work per character.
- Space: O(1) — four scalars.

### Trade-offs

Optimal in both time and memory. It does not extend to parentheses as directly as the stack, because a parenthesized group needs its own `total` and `term`, which brings the stack back. In interviews, present the stack first and then reduce it to this version if asked for O(1) memory.

### Pitfalls and edge cases

- Starting with `operator = '+'` and `term = 0` makes the first number a positive term without a special case: the first flush adds the empty term 0 to `total`.
- The same flush-at-the-end and truncating-division rules as in the stack approach apply.

### Language notes

- Python: `operator in "+-"` checks both additive operators at once.
- TypeScript: plain `number` arithmetic is exact here, since every value stays far below 2^53.
- Java: a `switch` with `case '+', '-' ->` handles both additive operators in one branch; `term /= number` truncates toward zero.
- Kotlin: `when` with `'+', '-' ->` does the same; `s.withIndex()` provides the index for the last-character test.
- Go: `case '+', '-':` handles both additive operators, and since Go has no conditional expression the sign is two statements (`term = number`, then `term = -number` for `-`). Indexing a string yields a `byte`, so `operator` and `character` are bytes.
- Rust: `if` is an expression, so `term = if operator == b'+' { number } else { -number };` fits on one line, and `b'+'` is the byte literal that `s.bytes()` yields.
