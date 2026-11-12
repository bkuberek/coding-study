# Line Diff and Merge

## Statement

Build `LineDiff`, the core of the tools that compare and combine versions of a text file: the diff that shows what changed, the patch that carries a change to another copy of the file, and the merge that combines two people's changes. Every file here is a list of lines. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is a diff?** Take an old version of a file and a new one. A diff lists what to do, from the top, to turn the old version into the new one: keep a line that is in both, remove a line of the old version, or add a line of the new one. For example, with the old lines `a`, `b`, `c` and the new lines `a`, `c`, `d`:

```text
 a      kept
-b      removed
 c      kept
+d      added
```

Reading the kept and removed lines gives the old version back, and reading the kept and added lines gives the new one. Many lists of steps do that, including "remove everything, then add everything". A useful diff removes and adds as few lines as possible, which is the same as keeping as many lines as possible.

**What is a merge conflict?** Two people start from the same version of a file, the base, and each changes their own copy. A merge builds one file with both sets of changes. Where only one person changed something, the merge takes that change. Where both changed the same lines in different ways, no rule can tell which version is right, so the merge writes both, between marker lines, for a person to sort out. That is a merge conflict.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 40, level 2 by 60, level 3 by 85 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `LineDiff()`: creates the tool. Only level 3 keeps anything between calls.
- A file is a list of lines. A line is any text without a line break, and may be empty. Lines are equal only when they are exactly equal: case, spaces and all.
- Each level's section describes the methods it adds and their parameters.

## Output

Every method returns a list of strings: lines of a file, lines of a diff, or the status of each hunk of a patch.

## Level 1: Common lines and a line diff

- `diff(before, after)`: the diff that turns `before` into `after`, one string per step: a kept line is written with a space in front of it (`" a"`), a removed line with `-` (`"-b"`) and an added line with `+` (`"+d"`). The steps follow the order of both files.
- `lcs(before, after)`: the kept lines of that diff, in order.

**The fewest changes.** The diff keeps as many lines as possible. The lines a diff keeps appear in both files in the same order: they are a common subsequence of the two files, where a subsequence of a list is what is left after deleting some of its items without changing the order (`a`, `c` is a subsequence of `a`, `b`, `c`; `c`, `a` is not). So the kept lines form a longest common subsequence, and `lcs` returns it.

**Which diff, when several are best.** Two files often have several diffs with the fewest changes. Compare two such diffs step by step from the top: at the first step where they differ, prefer the one whose step keeps a line over one that removes or adds, and the one that removes over one that adds. Return the diff that wins against every other diff with the fewest changes. For example, `before = [x, y]` and `after = [y, x]` can keep either line. `-x, " y", +x` and `+y, " x", -y` both change two lines; at their first step one removes and the other adds, so the first wins. One consequence: within a run of changes between two kept lines, the removed lines always come before the added ones.

### Example 1

<!-- case: ex1 -->

`flour`, `eggs` and `butter` are in both lists in that order, and no longer list is. `sugar` is removed and `milk` added.

### Example 2

<!-- case: ex2 -->

Only one of the two lines can be kept. The diff that starts by removing `x = 1` wins over the one that starts by adding `y = 2`.

## Level 2: Unified hunks

A diff of a long file is mostly kept lines. The unified format shows only the changes and a few kept lines around each, called context, in blocks called hunks, each with a header that says where it is. This is the format of the POSIX `diff -U` command.

- `unified(before, after, context)`: the hunks of the diff of level 1, as one list: each hunk's header followed by its lines, hunk after hunk. When the files are equal, the list is empty.

**Which lines a hunk holds.** A changed line is a removed or an added line of the diff. A hunk holds a run of changes and up to `context` kept lines before its first change and after its last one, fewer where the file ends sooner. Two changes separated by at most `2 * context` kept lines are in the same hunk, together with every kept line between them; two changes separated by more are in different hunks. With `context = 0`, every run of changes between two kept lines is a hunk of its own.

**The header.** A hunk starts with `@@ -<old range> +<new range> @@`. The old range describes the lines of `before` in the hunk (its kept and removed lines), and the new range the lines of `after` (its kept and added lines). Lines are numbered from 1.

- A range of several lines is `start,count`: `3,5` is the 5 lines starting at line 3.
- A range of exactly one line is written `start` alone, without `,1`.
- An empty range, in a hunk that only adds or only removes lines, is `start,0`, where `start` is the number of the line just before the place where the lines would be, or `0` at the top of the file. Adding a line between lines 1 and 2 of `before` gives the old range `1,0`.

### Example 1

<!-- case: ex3 -->

One line changed in a file of 10 lines. With 2 lines of context, the hunk holds lines 3 to 7 of each file.

### Example 2

<!-- case: ex4 -->

The two changes are 6 kept lines apart, more than `2 * 1`, so they are two hunks. The second hunk has 2 lines of `before` and 3 lines of `after`.

## Level 3: Applying a patch

A patch is a list of hunks in the format of level 2, usually made against an older copy of the file. Lines may have been added or removed above a hunk since, so its lines are no longer where its header says. Patch tools search for the hunk near the expected place.

- `applyPatch(lines, patch, maxOffset)`: applies the hunks of `patch`, in order, to a copy of `lines`, and returns one status per hunk: `"applied <offset>"` or `"rejected"`.
- `patched()`: the lines after the most recent `applyPatch`, or an empty list before the first one.

**A hunk.** Its old lines are its kept and removed lines, in order, and its new lines its kept and added lines. Applying it replaces its old lines in the file with its new lines.

**Where to look.** Let `added` be the number of lines that the hunks applied so far added, minus the number they removed. The hunk's base position is a 0-based index in the copy being patched: `start - 1 + added`, where `start` is the start of its old range, or `start + added` when the old range is empty (the lines go after line `start`). The search begins at the base position plus the offset at which the previous applied hunk was found (0 for the first hunk). It tries positions at distance 0, 1, 2 and so on up to `maxOffset` from there, and at each distance the earlier position first.

**Where a hunk fits.** A position fits when the hunk's old lines appear there exactly, inside the file, and the position is not before the end of the previous applied hunk's new lines: hunks never move backwards past each other. A hunk with no old lines fits at any such position.

**The result.** At the first position that fits, the hunk is applied and its status is `"applied <offset>"`, where the offset is the position minus the base position, written as a plain integer such as `0`, `3` or `-2`. When no position fits, the status is `"rejected"`, the copy does not change, and the next hunk is still tried. A rejected hunk counts neither for `added` nor for the offset carried to the next hunk.

You can rely on every patch being well formed: each header is followed by exactly the lines its ranges count, each starting with a space, `-` or `+`.

### Example 1

<!-- case: ex5 -->

Before any patch, `patched()` is empty. The hunk's old lines are at the place its header says, so it applies at offset 0.

### Example 2

<!-- case: ex6 -->

The file gained two lines at the top, so the first hunk is found 2 lines lower than its header says. The second hunk is searched from its base position plus 2 and fits there. The third hunk's old line, `line ten`, is nowhere near, so it is rejected and the file keeps `line 10`.

## Level 4: Three-way merge

- `merge(base, ours, theirs)`: the merge of the changes from `base` to `ours` and from `base` to `theirs`, as a list of lines with any conflicts marked.

**Stable lines and chunks.** Take the diff from `base` to `ours` and the diff from `base` to `theirs`, both by the rule of level 1. A line of `base` is stable when both diffs keep it. Stable lines are where the three files agree, and they cut them into pieces: between two consecutive stable lines, and before the first and after the last, each file has a chunk, the lines that lie between those stable lines in that file. A chunk may be empty in some of the files, and chunks that are empty in all three are skipped.

**Resolving a chunk.** Compare the three chunks, `O` from `base`, `A` from `ours` and `B` from `theirs`:

1. `A` equals `B`: both sides made the same change, or none. Take `A`, once.
2. Otherwise, `A` equals `O`: only theirs changed. Take `B`.
3. Otherwise, `B` equals `O`: only ours changed. Take `A`.
4. Otherwise both changed it differently: a conflict.

The result is every stable line and every resolved chunk, in order. A conflict is written as these lines, the marker lines being exactly as shown, each marker 7 characters long:

```text
<<<<<<< ours
(the lines of A)
||||||| base
(the lines of O)
=======
(the lines of B)
>>>>>>> theirs
```

Changes on neighbouring lines conflict, even when they touch different lines, because no stable line separates them.

### Example 1

<!-- case: ex7 -->

Ours changed the second line and theirs the last one. The two unchanged lines between them are stable and separate the two changes, so both are taken.

### Example 2

<!-- case: ex8 -->

Both sides changed `step 2: build`, differently, so the merge writes both versions with the base between them.

## Constraints

- At most 20 calls per test.
- Every list holds at most 300 lines, and a line at most 80 characters.
- `0 <= context <= 20` and `0 <= maxOffset <= 50`.
- A patch is well formed, as level 3 describes, and its hunks are in increasing order of their old ranges.

## Follow-ups

- The table of level 1 takes `n * m` cells for two files of `n` and `m` lines. Two files of 100,000 lines that differ in 10 lines need 10 billion cells. Which algorithms find the fewest changes in time that grows with the number of changes instead?
- In code, several closing braces often look the same, so a diff with the fewest changes can remove a function starting one `}` early. What preference among such diffs would line them up the way a reader expects?
- Patch tools can also drop context lines when a hunk does not fit anywhere, accepting a hunk whose changed lines match even if its first and last kept lines do not. What could go wrong?
- Would the merge change if the diffs to `ours` and `theirs` broke ties differently? Find three files where the tie-break decides between a clean merge and a conflict.

## Hints

### Hint 1

Start with the first line of each file. If they are equal, keeping both is never a mistake. If they differ, at least one of them cannot be kept here: either the line of `before` is removed or the line of `after` is added, and the rest is the same problem on shorter lists.

### Hint 2

That recursion asks the same question about the same pair of positions many times. Store the answer for every pair: the length of the longest common subsequence of `before` from line `i` on and `after` from line `j` on. Fill the table from the end of both files towards the start, so that every cell can read the cells below and to the right of it.

### Hint 3

To build the diff, walk from the top. Keep the line when the two lines are equal. Otherwise remove the line of `before` when doing so still leaves a longest common subsequence of the same length, which the table tells you, and add the line of `after` only when removing would lose a kept line.

### Hint 4

For hunks, walk the diff once and note the index of every changed step. Group consecutive changes whose gap is at most `2 * context` kept steps. For each group, take `context` steps before and after, and count how many lines of `before` and of `after` come before the hunk and inside it.

### Hint 5

For a patch, keep three numbers as you go: the lines added so far, the offset of the last applied hunk, and the index where the last applied hunk's new lines end. Each hunk gets a base position and a starting point from them; try the candidate positions in order of distance, earlier first.

### Hint 6

For the merge, turn each diff into a map from an index of `base` to the index where that line is kept in the other file. Walk `base`; at every index in both maps, resolve the chunks between the previous stable line and this one, output the stable line, and move on. Resolve what is left after the last one the same way.
