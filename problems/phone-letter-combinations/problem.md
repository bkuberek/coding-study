# Phone Letter Combinations

## Statement

On a classic phone keypad, each digit from 2 to 9 stands for a few letters:

| Digit | Letters |
|-------|---------|
| 2 | `abc` |
| 3 | `def` |
| 4 | `ghi` |
| 5 | `jkl` |
| 6 | `mno` |
| 7 | `pqrs` |
| 8 | `tuv` |
| 9 | `wxyz` |

You get a string `digits` made of such digits. Pressing them in order spells a word by choosing one letter for each digit. List every word that can be spelled this way. When `digits` is empty, nothing can be spelled, and the answer is empty.

Reference: this is our own wording of LeetCode problem 17, [Letter Combinations of a Phone Number](https://leetcode.com/problems/letter-combinations-of-a-phone-number/).

## Input

- `digits`: the keys pressed, in order

## Output

A list of every word with one letter per digit, the `i`-th letter taken from the letters of `digits[i]`. The words may come in any order.

## Examples

### Example 1

<!-- case: ex1 -->

The 4 offers `g`, `h` or `i` and the 7 offers `p`, `q`, `r` or `s`, so there are 3 * 4 = 12 words.

### Example 2

<!-- case: ex2 -->

A single 9 spells each of its four letters on its own.

## Constraints

- `0 <= digits.length <= 6`
- Every character of `digits` is between `'2'` and `'9'`.

## Follow-ups

- How many words do `k` presses of the 7 key produce? What is the size of the answer in general?
- Can you build the words without recursion, extending a list of partial words one digit at a time?

## Hints

### Hint 1

The answer is the product of the digits' letter sets: one letter for the first digit, combined with every word for the remaining digits.

### Hint 2

Depth-first: keep a buffer with one slot per digit, fill slot `i` with each letter of `digits[i]` in turn, and record the buffer when every slot is filled.

### Hint 3

Breadth-first: start with the single empty word and, for each digit, replace every partial word by its extensions with each of the digit's letters.
