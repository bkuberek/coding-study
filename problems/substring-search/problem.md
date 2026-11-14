# Substring Search

## Statement

You get a `text` and a word to look for, the `pattern`. The pattern **occurs** in the text at position `i` when the letters of the text starting at position `i`, as many as the pattern has, are exactly the pattern. Positions count from 0. This is what a text editor's "find all" does.

Return the position of every occurrence, in increasing order. Occurrences may **overlap**: two occurrences are different as soon as they start at different positions, even if they share letters. If the pattern does not occur, return an empty array.

**A worked example.** Take the text `abababa` and the pattern `aba`. Lay the pattern under the text at each start and check the three letters:

```text
position 0:  abababa      position 2:  abababa      position 4:  abababa
             aba                         aba                         aba
             match                       match                       match

position 1 (bab), position 3 (bab) and position 5 (ba, which is too short) do not match.
```

The answer is `[0, 2, 4]`. The occurrences at 0 and 2 overlap in the letter at position 2, and both count. In the text `aaaa` the pattern `aa` occurs at 0, 1 and 2.

Checking the pattern at every start is the simplest way to solve this, and it is correct. The question the problem poses is how much work it takes. With a text of `n` letters and a pattern of `m` letters, there are about `n` starts and each check may compare up to `m` letters, which is `n * m` comparisons in the worst case. For a text of 10,000 letters and a pattern of 5,000 that is about 25 million comparisons, and for 100,000 letters it is a few billion. Can the search be done with a number of steps that grows only with `n + m`? The tests include inputs large enough to tell the two apart.

## Input

- `text`: the text to search
- `pattern`: the word to look for

## Output

An array of the positions (counted from 0) at which `pattern` occurs in `text`, in increasing order, overlapping occurrences included. An empty array when there is none.

## Examples

### Example 1

<!-- case: ex1 -->

`abra` occurs at the start of `abracadabra` and again at its end, at position 7. The two occurrences do not overlap.

### Example 2

<!-- case: ex2 -->

In a text of five `a` letters, `aa` fits at positions 0, 1, 2 and 3, and all four overlapping occurrences are reported.

### Example 3

<!-- case: ex3 -->

The pattern is longer than the text, so it cannot occur: the answer is an empty array.

## Constraints

- `1 <= text.length <= 10^5`
- `1 <= pattern.length <= 10^5`
- `text` and `pattern` consist of ASCII letters (`a` to `z` and `A` to `Z`) and digits. Uppercase and lowercase letters are different letters.

## Follow-ups

- Which text makes checking every start slowest? What does the check keep repeating on that text?
- How would you find the occurrences of many patterns in one pass over the text?
- A rolling hash can report a position by mistake. When, and what does the algorithm do about it?
- The search never moves back in the text in the border (failure-function) approach. What does it keep instead, and how much space does that take?

## Hints

### Hint 1

Write the pattern on a strip of paper and slide it along the text, one position at a time. At each position, compare letter by letter and stop at the first letter that differs. Count how many letter comparisons this takes on a text of `aaaa...a` and a pattern `aaa...ab`.

### Hint 2

In that example the slide repeats work: when a check fails after matching many letters, those letters are known, and the next position starts with mostly the same letters. Ask what the matched letters tell you about where the next match could possibly begin.

### Hint 3

If the pattern `abcabd` matched `abcab` and then failed, the next place it can match must begin with a piece of `abcab` that is also the start of the pattern. The longest such piece is the key: for every prefix of the pattern, precompute the length of its longest border (a **border**: a prefix that is also a suffix, other than the whole word). Reading the text once and falling back inside the pattern with that table is one way to get linear time.

### Hint 4

Another way avoids comparing letters at all. Turn every window of the text into one number (a hash) that is easy to update when the window slides by one letter: remove the contribution of the letter that leaves, shift, and add the letter that enters. Compare the number of each window with the number of the pattern.

### Hint 5

Two different words can have the same number, so a window whose number equals the pattern's must still be checked letter by letter before it is reported. In the border (failure-function) approach, keep the table `border[i]` for the pattern prefix of length `i + 1`, extend the matched length by one on each equal letter, fall back to `border[matched - 1]` on a difference, and record an occurrence whenever the matched length reaches `m`, then fall back once more so that overlaps are found.
