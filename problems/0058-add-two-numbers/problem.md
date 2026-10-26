# Add Two Numbers

## Statement

Two non-negative integers are stored as singly linked lists of decimal digits, one digit per node, with the **least significant digit first**. The number 704, for example, is the list `4 -> 0 -> 7`. Add the two numbers and return their sum in the same form.

The numbers can be far longer than any built-in integer type can hold, so the intended solution works digit by digit, the way you add on paper, rather than converting the lists to machine integers. Neither number has leading zeros, except the number 0 itself, which is the single node `0`.

Reference: this is our own wording of LeetCode problem 2, [Add Two Numbers](https://leetcode.com/problems/add-two-numbers/).

## Input

- `l1`: the digits of the first number, least significant first.
- `l2`: the digits of the second number, least significant first.

Each list is written as the array of its node values from head to tail, so `[4, 0, 7]` is 704.

## Output

The digits of the sum, least significant first, without leading zeros.

## Examples

### Example 1

<!-- case: ex1 -->

The lists hold 704 and 58, and 704 + 58 = 762. The ones digits 4 + 8 = 12 give 2 and a carry of 1; the tens give 0 + 5 + 1 = 6; the hundreds digit 7 has no partner and is copied.

### Example 2

<!-- case: ex2 -->

999 + 1 = 1000. The carry ripples through every digit and, after both lists are used up, still produces one more node: the sum is one digit longer than either input.

## Constraints

- Each list has between `1` and `10^4` nodes.
- `0 <= node value <= 9`.
- No list has a most significant digit of 0, unless the whole number is 0.

## Follow-ups

- Why does converting to 64-bit integers fail, and what would converting to arbitrary-precision integers cost?
- What changes if the digits are stored most significant first? Can you solve that version without reversing the input lists?
- How would you subtract or multiply two numbers stored this way?

## Hints

### Hint 1

The least significant digits are at the heads, which is exactly where pen-and-paper addition starts.

### Hint 2

Walk both lists together. At each step add the two digits (a missing digit counts as 0) and the carry from the previous step; the new node holds the sum modulo 10, and the new carry is the sum divided by 10.

### Hint 3

Do not stop when both lists end: a remaining carry of 1 needs one last node.
