# Valid Parentheses

## Statement

You get a string `s` made only of the six bracket characters `(`, `)`, `[`, `]`, `{` and `}`. Decide whether the brackets are properly balanced:

- every opening bracket is closed by a closing bracket of the same kind,
- brackets close in the reverse order of opening, so a pair that opens inside another pair also closes inside it,
- every closing bracket closes some earlier opening bracket.

Reference: this is our own wording of LeetCode problem 20, [Valid Parentheses](https://leetcode.com/problems/valid-parentheses/).

## Input

- `s`: the bracket string to check

## Output

`true` if the brackets in `s` are properly balanced, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

The braces enclose a bracket pair, which encloses a parenthesis pair, and each closes in reverse order of opening. A separate `()` follows. Every bracket is matched.

### Example 2

<!-- case: ex2 -->

The `(` opens inside `[`, so it must close before the `]`. Here the `]` comes first, while `(` is still open, so the string is not balanced, even though each kind of bracket appears equally often.

## Constraints

- `1 <= s.length <= 10^5`
- `s` contains only the characters `()[]{}`.

## Follow-ups

- Can you check the string in a single left-to-right pass?
- If `s` contained only `(` and `)`, could you avoid a stack and use O(1) extra memory?
- How would you report the position of the first bracket that breaks the rules?

## Hints

### Hint 1

In a balanced string, some opening bracket is immediately followed by its matching closer. What happens to the rest of the string if you delete that pair?

### Hint 2

When you meet a closing bracket, which opening bracket must it match: the first one still open, or the most recent one?

### Hint 3

Keep the open brackets on a stack. A closing bracket must match the top of the stack, and the stack must be empty at the end.
