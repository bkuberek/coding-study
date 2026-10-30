# Debug: Char Boundary

## Statement

A storefront shows product names in a column that is `width` characters wide. The function `truncate_label` you start from should return `label` unchanged when it has at most `width` characters. A longer label is cut to its first `width - 1` characters followed by `…` (U+2026, one character), so it fills the column exactly. A character here is a Unicode code point, a Rust `char`.

The code works for the English catalog. It fails for others. Find out why and fix it.

### Bug report

> **Title:** Product grid crashes or clips names in the European and Asian stores
>
> After the storefront launched in France and Germany, some category pages crash with ``byte index 3 is not a char boundary; it is inside 'è' (bytes 2..4) of `Crème brûlée` ``. Pages that load show short names clipped for no reason: "Café" appears as "Caf…" in a column four characters wide. The Japanese store crashes on almost every page. The English store has never had a problem.

## Input

- `label`: the product name
- `width`: the width of the column, in characters

## Output

`label` itself when it has at most `width` characters, otherwise its first `width - 1` characters and `…`.

## Examples

### Example 1

<!-- case: ex1 -->

The name has 14 characters and fits in 20. This case passes as shipped.

### Example 2

<!-- case: ex2 -->

19 characters do not fit in 10: the first 9 characters and the ellipsis make exactly 10. This case passes too.

## Constraints

- `0 <= label.chars().count() <= 200`
- `1 <= width <= 100`
- `label` holds characters of the Basic Multilingual Plane, without combining marks: every accented letter is a single precomposed character.

## Follow-ups

- Find the byte offset of the cut with `char_indices` and slice once, instead of collecting characters into a new `String`. Is it worth it?
- A user-perceived character can be several code points, such as `e` followed by a combining accent, or a flag emoji. What would a column width in those terms need?

## Hints

### Hint 1

Every failing name has a character outside ASCII. Compare `label.len()` and `label.chars().count()` for "Café".

### Hint 2

Rust strings are UTF-8. How many bytes do `é`, `П` and `東` take?

### Hint 3

`&label[..n]` slices at byte `n`. What happens when byte `n` is in the middle of a character?

### Hint 4

Count with `chars().count()`, and cut with `chars().take(width - 1)`.
