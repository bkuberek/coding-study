# Replace Words with Roots

## Statement

A dictionary lists roots. Every word of `sentence` that starts with at least one root is replaced by the shortest root it starts with. Words that start with no root stay unchanged. The words of the sentence are separated by single spaces.

Return the resulting sentence. A root only counts at the beginning of a word, and a word that is equal to a root starts with it.

Reference: this is our own wording of LeetCode problem 648, [Replace Words](https://leetcode.com/problems/replace-words/).

## Input

- `dictionary`: distinct roots made of lowercase letters
- `sentence`: lowercase words separated by single spaces

## Output

The sentence after the replacement, with its words still separated by single spaces.

## Examples

### Example 1

<!-- case: ex1 -->

"sunflowers" starts with "sun", "moonlight" starts with "moon" and "starfish" starts with "star", so each becomes its root. The other words start with no root and stay.

### Example 2

<!-- case: ex2 -->

"prefix" starts with "p", "pre" and "prefix", and "prepare" starts with "p" and "pre"; the shortest, "p", wins both times. "apple" contains "p" but does not start with it, so it stays.

## Constraints

- `1 <= dictionary.length <= 2000`
- `1 <= dictionary[i].length <= 100`; the roots are distinct and use lowercase English letters
- `sentence` holds 1 to `10^4` words of 1 to 100 lowercase letters, separated by single spaces, with no leading or trailing space

## Follow-ups

- A set of roots plus a check of each prefix of a word is another answer. How does its cost compare with the trie's?
- What if roots could also match in the middle of a word?

## Hints

### Hint 1

For one word, only the roots that are prefixes of it matter.

### Hint 2

Put the roots in a trie, walk each word letter by letter and stop at the first node where a root ends.

### Hint 3

If the walk falls off the trie before a root ends, the word stays as it is.
