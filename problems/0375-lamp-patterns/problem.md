# Lamp Patterns

## Statement

A corridor has `n` lamps in a row. Each lamp is either on or off, and the safety rule says that no two neighbouring lamps may be on at the same time. Write one arrangement as a string of `n` characters from left to right, with `1` for a lamp that is on and `0` for a lamp that is off. For example, `"1010"` is allowed and `"0110"` is not.

Return every allowed arrangement exactly once, in increasing order. Strings of the same length are ordered like words in a dictionary, so `"0"` comes before `"1"` at the first position where two strings differ.

Reference: this is our own wording of LeetCode problem 3211, [Generate Binary Strings Without Adjacent Zeros](https://leetcode.com/problems/generate-binary-strings-without-adjacent-zeros/), with the roles of `0` and `1` swapped.

**The technique: backtracking.** Backtracking builds an answer one decision at a time, and every decision follows the same three steps:

1. **Choose.** Fill the next empty slot with one of its possible values.
2. **Explore.** Handle all the slots that are still empty, by repeating the same steps.
3. **Undo.** Take the value back out, so that the slot is free for its next possible value.

When every slot is filled, the string in your hands is one complete answer: copy it into the result. When a choice already breaks a rule, do not explore it at all. Skipping a branch that cannot lead to an answer is called pruning.

Here is `n = 3`, read left to right. Each line is a string being built, and the lines below it are the choices made next:

```text
""
├─ "0"
│  ├─ "00"
│  │  ├─ "000"   complete: keep
│  │  └─ "001"   complete: keep
│  └─ "01"
│     ├─ "010"   complete: keep
│     └─ "011"   two 1s in a row: pruned
└─ "1"
   ├─ "10"
   │  ├─ "100"   complete: keep
   │  └─ "101"   complete: keep
   └─ "11"       two 1s in a row: pruned
```

Visiting the choices in the order `0`, then `1` produces the complete strings in exactly the increasing order the answer needs.

## Input

- `n`: the number of lamps in the row

## Output

A list holding every allowed string of length `n` exactly once, in increasing order.

## Examples

### Example 1

<!-- case: ex1 -->

This is the tree above: five of the eight possible strings survive, and `"011"`, `"110"` and `"111"` are the three that break the rule.

### Example 2

<!-- case: ex2 -->

With two lamps, only `"11"` is forbidden.

## Constraints

- `1 <= n <= 14`

## Follow-ups

- Count the answers for `n = 1, 2, 3, 4, 5`. Which well-known sequence do the counts follow, and why does the last lamp being off or on explain it?
- How would you change the rule so that no three neighbouring lamps may all be on?
- Can you list the same answers without recursion, by counting from `0` up to `2^n - 1` and looking at the bits of each number?

## Hints

### Hint 1

Take `n = 3` and write down all eight strings of three characters, each `0` or `1`. Cross out the ones with two `1`s side by side. What is left is the answer; the program only has to do the same for any `n`.

### Hint 2

Instead of writing all the strings and crossing some out, build each string from left to right, one character at a time. At every position you may write `0`, and you may write `1` only when the character before it is not `1`.

### Hint 3

Keep one shared list of characters for the string being built. Add a character, continue with the next position, then remove that character again so the next choice starts from the same string. When the list has `n` characters, copy it into the result. Trying `0` before `1` gives the required order.
