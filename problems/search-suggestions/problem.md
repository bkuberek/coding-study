# Search Suggestions

## Statement

A shop's search box suggests products while the customer types. You get the list of product names and the word the customer types, `searchWord`, one letter at a time. After each typed letter, the box shows up to three products whose names start with everything typed so far. When more than three products qualify, it shows the three that come first in alphabetical order; when fewer qualify, it shows all of them, also in alphabetical order.

Return the suggestions shown after each letter of `searchWord`, in typing order.

Reference: this is our own wording of LeetCode problem 1268, [Search Suggestions System](https://leetcode.com/problems/search-suggestions-system/).

## Input

- `products`: the distinct product names, in no particular order.
- `searchWord`: the word being typed.

## Output

A list with one entry per letter of `searchWord`. Entry `i` is the alphabetically smallest (at most three) products that start with the first `i + 1` letters of `searchWord`, in alphabetical order; it is empty when no product starts with those letters.

## Examples

### Example 1

<!-- case: ex1 -->

In alphabetical order the products are `pea`, `peach`, `pear`, `pecan`, `plum`. After `p`, `pe` and `pea` the first three matches are always `pea`, `peach` and `pear`. After `pear`, only `pear` itself still matches.

### Example 2

<!-- case: ex2 -->

All three products start with `s`. None starts with `se`, so that entry is empty, and so is every later one: no product can start with `sea` if none starts with `se`.

## Constraints

- `1 <= products.length <= 10^4`.
- `1 <= products[i].length <= 20`; the products are distinct.
- `1 <= searchWord.length <= 20`.
- All strings consist of lowercase English letters.

## Follow-ups

- The suggestions for a longer prefix are always among the matches for a shorter one. How can you use that to avoid starting every search from scratch?
- If products were added while customers type, which structure would you keep?

## Hints

### Hint 1

Sort the products once. All products that start with a given prefix then form one contiguous block of the sorted list.

### Hint 2

Binary search finds where that block starts: the first product that is not smaller than the prefix. The suggestions are the next three products, as long as they still start with the prefix.

### Hint 3

A trie works too: walk one node per typed letter, and let every node remember the three smallest products below it, filled by inserting the products in sorted order.
