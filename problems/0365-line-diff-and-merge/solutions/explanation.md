# Line Diff and Merge: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| lcs-table | optimal | O(n * m) per diff, unified diff or merge; O(k * p + h * n) per patch | O(n * m) | default answer for files of a few thousand lines |

`n` and `m` are the numbers of lines of the two files (for a merge, of `base` and the longer of the other two), `h` the number of hunks of a patch, `p` its number of lines and `k` the largest offset searched.

## How the design grows level by level

| Level | What changes | Design move |
|-------|--------------|-------------|
| 1 | Common lines and a diff | A table of longest common subsequence lengths over suffixes, then a walk from the top that reads the table to pick the preferred step |
| 2 | Hunks | The walk's steps become a list that is cut into groups of changes; line numbers are counts of the steps before a hunk |
| 3 | Patches | No diff at all: the hunks are parsed back into old and new lines and searched for in the file, with three numbers carried from hunk to hunk |
| 4 | Merge | Two diffs from the same base; the base lines both keep are the anchors, and each piece between anchors is resolved by comparing three lists |

Everything rests on one function, the diff of level 1, which levels 2 and 4 call; level 3 reads the output of level 2.

## Approach: lcs-table (A suffix table of common subsequences and chunked three-way merge)

### Intuition

A diff that changes as few lines as possible keeps as many as possible, and the kept lines are a common subsequence of the two files, so the problem is the longest common subsequence. Let `L[i][j]` be its length for the suffixes `before[i:]` and `after[j:]`. If the first lines of the suffixes are equal, keeping them is always part of some best answer: `L[i][j] = 1 + L[i+1][j+1]`. Otherwise one of them is not kept, and `L[i][j] = max(L[i+1][j], L[i][j+1])`. Each cell needs only the cells below and to its right, so the table fills from the bottom-right corner.

The table is over suffixes, not prefixes, because of the tie-break. The statement prefers, from the top, keep over remove over add. Choosing the first step well needs to know, for each choice, whether the rest can still reach the best total, and that is exactly what a suffix table answers at the start. A table over prefixes answers it at the end, so it naturally builds the diff backwards and breaks ties from the bottom, which is a different diff.

The merge reuses the diff. A base line that both diffs keep is a place where all three files agree; the stretches between those places are where something changed, and comparing the three versions of a stretch says who changed it.

### Algorithm

1. **Table.** For `i` from `n - 1` down to 0 and `j` from `m - 1` down to 0, set `L[i][j]` as above, with zeros in row `n` and column `m`.
2. **Walk.** From `i = j = 0`: if `before[i] == after[j]`, keep and advance both. Else if `before` has a line left and either `after` is used up or `L[i+1][j] >= L[i][j+1]`, remove `before[i]`. Else add `after[j]`. `lcs` returns the kept lines and `diff` every step with its prefix.
3. **Hunks.** List the indices of the changed steps. Start a group at the first; a change joins the current group when at most `2 * context` steps lie between it and the previous change, and starts a new group otherwise. A hunk spans its group's steps widened by `context` on each side, clipped to the list. Its old range counts the steps that are not additions, before the hunk (for the start) and inside it (for the count), and its new range the steps that are not removals. A count of 1 drops `,1`; a count of 0 writes the number of lines before the hunk, then `,0`.
4. **Patch.** Parse each hunk into its old-range start, old lines (context and removed) and new lines (context and added); the start index is `start - 1`, or `start` when the old range is empty. Keep `added`, `shift` and `floor`, all 0. For each hunk, `base = start + added`; try the positions `base + shift - d` and `base + shift + d` for `d` from 0 to `maxOffset`, keeping those at or after `floor` whose slice equals the old lines. On the first fit, splice in the new lines, set `shift = position - base`, add the length change to `added`, set `floor = position + len(new)` and report `applied shift`; otherwise report `rejected`.
5. **Merge.** Diff `base` against `ours` and against `theirs`, and turn each diff into a map from a kept base index to its index in the other file. Walk `base`; at each index in both maps, resolve the three chunks since the previous such index, output the line and move the three cursors past it. Resolve the three tails at the end. A chunk resolves to `ours` if `ours == theirs`, else `theirs` if `ours == base`, else `ours` if `theirs == base`, else to a conflict block.

### Correctness

**Table.** If `before[i] == after[j]`, any common subsequence of the suffixes that does not use this pair can swap its first matched line for this pair, so some longest one uses it. If they differ, a longest common subsequence cannot use both lines as a pair, so it skips at least one of them, which is the max of the two smaller suffixes.

**Walk.** At each position the walk takes the first step, in the order keep, remove, add, after which a best total is still reachable: keep is always optimal when the lines are equal, and when they differ, `L[i+1][j] >= L[i][j+1]` means `L[i+1][j] = L[i][j]`, so removing loses nothing. Taking the preferred optimal step at every position is exactly the lexicographic rule: two diffs that agree up to some step and then differ are compared at that step, and the walk's step is the preferred one among all that can still finish with the fewest changes. Removed lines come before added ones within a run: after an addition at `(i, j)`, removing `before[i]` at `(i, j+1)` would need `L[i+1][j+1] = L[i][j+1]`, but `L[i+1][j+1] <= L[i+1][j] < L[i][j+1]`.

**Hunks.** A gap of more than `2 * context` kept lines cannot be covered by the context after one change and before the next, so those changes are in separate hunks; a gap of at most that much is covered, and splitting there would show the same kept line in two hunks or leave hunks that touch. The counts follow from the steps: kept and removed steps are lines of `before`, kept and added steps lines of `after`.

**Patch.** `base` is where the hunk's old lines would be if the file were the one the patch was made from, with the earlier hunks applied. Adding `shift` assumes the file moved the same way as at the previous hunk, which is the common case of lines added or removed above. The order of candidates is the stated one, and `floor` keeps hunks in the order of the file.

**Merge.** The stable lines are in the same order in all three files, since each diff keeps lines in order, so the chunks between them are well defined and cover every line of each file exactly once. This is the parse into stable and unstable chunks that Khanna, Kunal and Pierce describe for diff3: a chunk where only one side differs from the base was changed on that side only, and propagating that change is safe. When both sides differ from the base and from each other, no choice keeps both changes, so the block shows all three versions. When both sides are equal, the paper calls the chunk falsely conflicting; this problem takes it once.

### Complexity

- Time: O(n * m) per diff, unified diff or merge; O(k * p + h * n) per patch — the table has `(n + 1) * (m + 1)` cells and the walk and the grouping are linear; a patch tries at most `2k + 1` positions per hunk, each compared over the hunk's old lines, and splices each hunk into a file of about `n` lines.
- Space: O(n * m) — the table; the steps, hunks and maps are linear.

### Trade-offs

- **Time that follows the size of the change.** Myers' algorithm (1986) finds a shortest edit script in time O(ND), where `N` is the total length of the two files and `D` the size of the shortest edit script, which is what makes diffs of large, similar files fast. A diff built on it has its own way of choosing among equally short scripts, so check its output against this problem's rule before reusing it here. Hunt and McIlroy's earlier diff (1976) also solves the longest common subsequence problem, and gains its speed by attending only to certain candidate matches between the files.
- **Space.** The full table is needed only to walk forwards. Computing just the length needs two rows, O(m), since each row reads only the row below it.
- **Merge styles.** Showing the base between `|||||||` and `=======` tells the reader what each side changed; the shorter style without it shows only the two results.

### Pitfalls and edge cases

- Building the table over prefixes and walking back from the end breaks ties from the bottom: on Example 2 it keeps `x = 1` instead of `y = 2` and starts with an addition.
- Choosing "remove" whenever the lines differ, without checking the table, gives a valid diff that is not the shortest (`[x, y, z]` against `[z, x, y]`).
- Hunk headers: an empty range counts the line before it (`-1,0`), `0` at the top of the file, not the next line. A one-line range has no `,1`. The old and new starts differ as soon as an earlier hunk added or removed lines.
- A gap of exactly `2 * context` kept lines stays in one hunk.
- Patches: forgetting `added` makes every hunk after one that changed the length search from the wrong place; forgetting `shift` loses a file that moved by more than `maxOffset`; breaking a tie towards the later position, or letting a hunk match before the previous one, applies a change to the wrong copy of repeated lines. A rejected hunk must not stop the patch.
- Merge: an identical change on both sides is not a conflict; changes on neighbouring lines are, because no stable line separates them; a deletion against an edit is a conflict with an empty side.

### Language notes

- The table is the only large structure: Python uses lists of lists, TypeScript `Int32Array` rows, Java and Kotlin `int` arrays, Go slices and Rust `Vec<Vec<u32>>`.
- Lists are compared by value with `==` in Python and Kotlin, `equals` on Java lists, `slices.Equal` in Go and `==` on slices in Rust; TypeScript has no list equality, so the reference writes a small helper.
- Java and Kotlin splice a hunk through `subList(...).clear()` and `addAll`, Go rebuilds the slice with `slices.Concat`, Rust uses `Vec::splice` and TypeScript `Array.prototype.splice`.
- Rust parses the header without a regular expression, since the `regex` crate is not available offline; the other languages use their standard regular expressions.

## Further reading

- J. W. Hunt and M. D. McIlroy, *An Algorithm for Differential File Comparison*, Bell Laboratories Computing Science Technical Report 41, July 1976. Its abstract describes diff as solving the longest common subsequence problem to find the lines that do not change.
- E. W. Myers, *An O(ND) difference algorithm and its variations*, Algorithmica 1, 251–266 (1986), [doi:10.1007/BF01840446](https://doi.org/10.1007/BF01840446).
- S. Khanna, K. Kunal and B. C. Pierce, *A Formal Investigation of Diff3*, FSTTCS 2007, Lecture Notes in Computer Science 4855, 485–496, [doi:10.1007/978-3-540-77050-3_40](https://doi.org/10.1007/978-3-540-77050-3_40): the parse into stable and unstable chunks, the classification of a chunk as changed on one side, falsely conflicting or truly conflicting, and the chunk-by-chunk algorithm that the merge here follows.
- [POSIX `diff`, The Open Group Base Specifications Issue 8](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/diff.html): the unified format, its `@@ -range +range @@` headers, the rule for an empty range, and the limit of `2n` consecutive unaffected lines in output with `n` lines of context.
