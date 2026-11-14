# First Bad Commit

## Statement

A project's history is a line of commits, numbered `0` (the oldest) to `n - 1` (the newest). At some point a bug slipped in. Every commit before that point passes the project's test, and the commit where the bug appeared, and every commit after it, fails the test. A commit that passes is called **good** and one that fails is called **bad**. The task is to find the first bad commit, the one that introduced the bug.

Running the test is slow, so you only want to look at a few commits. And there is a complication: for some commits the test cannot run at all (the project does not even build there). Such a commit is **skipped**: you learn nothing about it, and it could be good or bad.

You get the result of testing every commit as an array `statuses`, where `statuses[i]` is:

- `0` if commit `i` is good,
- `1` if commit `i` is bad,
- `2` if commit `i` is skipped.

Write a function that says where the first bad commit is. When skipped commits make the answer uncertain, it says exactly which positions are possible.

**Why the answer can be uncertain.** Ignore the skipped commits for a moment and read the others from oldest to newest: they are some goods followed by some bads, never a good after a bad. The boundary lies between the last good commit and the first commit known to be bad. If the two are neighbours, the bug appeared exactly at the first known bad commit. If there are skipped commits between them, any of those could be the first bad commit as well, because nothing says they are good. Two examples with `.` marking a skipped commit:

```text
good good good BAD BAD       the first bad commit is the first BAD: no doubt
good good  .   .  BAD BAD    the bug may have appeared at either "." or at the first BAD
```

## Input

- `statuses`: the result for each commit, oldest first. Only the values `0`, `1` and `2` appear.

## Output

An array of two integers `[first, last]` (positions counted from 0):

- `first` is the position right after the last good commit, or `0` when no commit is good;
- `last` is the position of the first commit that is bad.

Every position from `first` to `last` could be the first bad commit, and no other position could. All of them except `last` are skipped commits. The answer is certain exactly when `first == last`.

## Examples

### Example 1

<!-- case: ex1 -->

Commits 0, 1 and 2 are good and commit 3 is bad, so the bug appeared at commit 3. The answer is a single position, `[3, 3]`.

### Example 2

<!-- case: ex2 -->

Commit 1 is the last good commit and commit 4 is the first bad one. Commits 2 and 3 were skipped, so the bug may have appeared at 2, at 3 or at 4: `[2, 4]`.

### Example 3

<!-- case: ex3 -->

Commit 0 was skipped and no commit is good, so the bug may have appeared at 0 or at 1, the first bad commit: `[0, 1]`.

## Constraints

- `1 <= statuses.length <= 10^5`
- every `statuses[i]` is `0`, `1` or `2`
- at least one commit is bad (`1` appears)
- no good commit comes after a bad one: if `statuses[i] == 1` and `j > i`, then `statuses[j] != 0`

## Follow-ups

- Scanning from the oldest commit reads up to `n` results. How few results can you read when no commit is skipped?
- With skipped commits, what is the worst history for your approach? How many results must any approach read to be sure about a history like `good, skipped x 98, bad`?
- If a test costs ten minutes, which of your two approaches would you rather run, and what does skipping do to its cost?

## Hints

### Hint 1

Forget the skipped commits for now. If every commit were good or bad, the results would read like `good good good bad bad bad`: the answer is the place where the line changes. What do you know about the commits on the left of a good commit?

### Hint 2

Walking from commit 0 and stopping at the first bad commit finds the boundary. Keep track of the last good commit you passed. That is correct, but it may read almost the whole array. Can a single look at one commit rule out many commits at once?

### Hint 3

Pick one commit in the middle and look only at it. If it is good, what can you say about every commit before it? If it is bad, what can you say about the commits after it? How much of the history is left to search once you know?

### Hint 4

A skipped commit tells you nothing. When the middle commit is skipped, step to the nearest commit you can learn something from, staying inside the part of the history you are still searching, and judge that one instead.

### Hint 5

Search twice. First find the position of the first bad commit, probing as above. Then, in the part before it, find the position of the last good commit, which is the same search turned around: every commit that is not skipped there is good. The answer is `[lastGood + 1, firstBad]`, with `lastGood = -1` when nothing is good.
