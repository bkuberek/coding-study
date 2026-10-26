# Smallest String With Swaps

## Statement

You get a string `s` and a list `pairs` of index pairs `[a, b]`. As often as you like, and in any order, you may pick a pair from the list and swap the characters at its two positions.

Return the lexicographically smallest string you can reach.

Reference: this is our own wording of LeetCode problem 1202, [Smallest String With Swaps](https://leetcode.com/problems/smallest-string-with-swaps/).

## Input

- `s`: the starting string
- `pairs`: pairs of positions `[a, b]` whose characters may be swapped

## Output

The smallest string, in dictionary order, that some sequence of allowed swaps produces.

## Examples

### Example 1

<!-- case: ex1 -->

Positions 0 and 3 can trade, and so can positions 1 and 2. Putting the smaller letter first in each group gives `s` and `t` at positions 0 and 3, and `o` and `p` at positions 1 and 2.

### Example 2

<!-- case: ex2 -->

Swapping 0 with 1 and 1 with 2 lets the first three letters reach any arrangement, so they can be sorted to `bcd`. Position 3 is in no pair, so its `a` stays last.

## Constraints

- `1 <= s.length <= 10^5`
- `0 <= pairs.length <= 10^5`
- `0 <= a, b < s.length`; a pair may repeat, and `a` may equal `b`.
- `s` consists of lowercase English letters.

## Follow-ups

- Swaps along a chain of pairs can move a character far from home. Which positions can end up holding which characters?
- Within one group of connected positions, is every arrangement reachable?
- With only 26 letters, can you avoid a comparison sort for each group?

## Hints

### Hint 1

Think of positions as nodes and pairs as edges. Repeated swaps along edges can carry any character anywhere within its connected component, and in fact reach every arrangement of the component's characters.

### Hint 2

So the answer handles each component independently: sort its characters and write them back into its positions in increasing order of position.

### Hint 3

Union-find over the positions finds the components while reading the pairs once. Group the positions by root, sort each group's characters, and place them.
