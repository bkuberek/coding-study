# Count Words by Prefix

## Statement

A phone keeps a list of contact names, and its search box answers one question as you type: how many names begin with the letters typed so far? You get the list as `words`, and the letters typed in several different moments as `prefixes`. For every prefix, count how many entries of `words` begin with it.

A **prefix** is the beginning of a word: `"te"` and `"tea"` are prefixes of `"team"`. A word also counts as a prefix of itself, and a prefix longer than the word is not a prefix of it. If the same word appears several times in `words`, each appearance counts.

**The data structure: a trie.** Checking every prefix against every word works, but it repeats a lot of work, because many words begin with the same letters. A **trie** (a tree of letters whose name comes from the word "retrieval") stores each shared beginning only once. Every node stands for one letter, the **root** at the top stands for the empty beginning, and following the letters of a word from the root downward walks one **path**. Words that begin alike share the start of their paths.

For the words `tea`, `team`, `ten` and `tin`, the trie looks like this. The number in brackets is how many of the words pass through that node, which is the same as how many of them begin with the letters on the path from the root down to it:

```text
(root)
└─ t (4)
   ├─ e (3)
   │  ├─ a (2)       "tea" ends here
   │  │  └─ m (1)    "team" ends here
   │  └─ n (1)       "ten" ends here
   └─ i (1)
      └─ n (1)       "tin" ends here
```

To answer the prefix `"te"`, start at the root and follow `t`, then `e`: the node you reach says 3. To answer `"tx"`, the path breaks off after `t`, because there is no `x` below it, so the answer is 0. Each question costs only as many steps as the prefix has letters, however many words there are.

## Input

- `words`: the words to search, in any order and possibly with repeats
- `prefixes`: the beginnings to ask about, possibly with repeats

## Output

A list with one number per prefix, in the order of `prefixes`: how many entries of `words` begin with that prefix.

## Examples

### Example 1

<!-- case: ex1 -->

Four of the five words begin with `"te"` (`tea`, `team`, `ten`, `tent`), two begin with `"tea"`, and all five begin with `"t"`. No word starts with `"x"`, and `"tens"` is longer than `"ten"` and differs from `"tent"` in its last letter.

### Example 2

<!-- case: ex2 -->

The word `"go"` appears twice, and each appearance counts, so `"go"` is the beginning of all four entries. Only `"gold"` and `"golf"` begin with `"gol"`, only `"golf"` begins with `"golf"`, and nothing begins with `"golfs"`.

## Constraints

- `1 <= words.length, prefixes.length <= 10^4`
- `1 <= words[i].length, prefixes[j].length <= 20`
- Every word and prefix consists of lowercase English letters `a` to `z`.

## Follow-ups

- How would you also report how many words are exactly equal to a prefix, not only how many begin with it?
- A trie node here has 26 slots, one per letter. What would you store instead if the words could use any Unicode character?
- If the words arrive one at a time and the questions are mixed with them, which part of your solution has to change?

## Hints

### Hint 1

Take the prefix `"te"` and the word list from Example 1, and decide for each word by hand whether it begins with `"te"`. Now imagine the list holds ten thousand words and there are ten thousand prefixes. Which part of that hand work is the same for every prefix?

### Hint 2

Many words start with the same letters. A tree with one node per letter, where words with the same beginning share their first nodes, lets you read a prefix's answer from the node at the end of its path instead of scanning the words.

### Hint 3

Give every node a counter and one slot for each possible next letter. For each word, walk down from the root creating missing nodes, and add 1 to the counter of every node you step on. To answer a prefix, walk the same way without creating anything: if a slot is empty the answer is 0, otherwise it is the counter of the last node.
