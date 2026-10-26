# Encode and Decode Strings

## Statement

Some channels can carry only a single string, yet you need to send a whole list of strings through one. Design a way to pack a list of strings into one string and unpack it again without losing anything: not the number of strings, not their order, not empty strings, and not any character inside them.

Write two helpers and one function that connects them:

- `encode(strs)` turns a list of strings into a single string.
- `decode(encoded)` turns that single string back into the original list.
- `encodeDecode(strs)` returns `decode(encode(strs))`.

The tests call `encodeDecode` and check that it returns exactly the list it was given. That round trip must really go through your encoding: `decode` may use only the string that `encode` produced, with no shared variables, globals or other side channels, and `encodeDecode` may not simply return a copy of its input. The strings can contain every character your format might want to use as a separator, so a plain join with a delimiter is not enough.

Reference: this is our own wording of LeetCode problem 271, [Encode and Decode Strings](https://leetcode.com/problems/encode-and-decode-strings/).

## Input

- `strs`: the list of strings to send; it may be empty, and its strings may be empty or contain any printable ASCII character, tab or newline

## Output

The list produced by decoding the encoding of `strs`: the same strings, in the same order, as `strs`.

## Examples

### Example 1

<!-- case: ex1 -->

Three ordinary words survive the round trip unchanged. Any encoding that keeps the boundaries between the words works for this input.

### Example 2

<!-- case: ex2 -->

These strings are designed to break naive formats: the first looks like a length prefix (`2#x`), the second is empty, and the third contains both a comma and a backslash. All three must come back exactly as they were.

## Constraints

- `0 <= strs.length <= 10^5`
- `0 <= strs[i].length <= 200`
- The strings contain at most `10^6` characters in total.
- Every character is printable ASCII (codes 32 to 126), a tab or a newline.

## Follow-ups

- Can you make `encode` and `decode` run in time linear in the total number of characters?
- Your format must tell an empty list apart from a list holding one empty string. Does it?
- How would you decode a stream incrementally, when the encoded string arrives in chunks of arbitrary size?

## Hints

### Hint 1

Joining with a separator fails as soon as a string contains the separator. What extra information would tell `decode` where each string ends, whatever its content?

### Hint 2

If `decode` knew the length of the next string in advance, it could copy exactly that many characters without looking at them.

### Hint 3

Write each string as its length, a fixed marker such as `#`, and then the string itself. The first `#` after a position always ends the length, because a length contains only digits.

### Hint 4

Alternatively, end every string with a terminator and escape the terminator, and the escape character itself, wherever they occur inside a string.
