# Entity Resolution: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| block-score-union | optimal | O(R + P w^2 + M k^2) | O(R + P) | default answer; each level is one more stage of the same pipeline |

Here `R` is the number of records, `P` the number of candidate pairs that blocking leaves, `w` the length of a name, `M` the number of matched pairs and `k` the size of the largest group.

## How the design grows level by level

| Level | Change | What the pipeline adds |
|-------|--------|------------------------|
| 1 | Clean the records | One pure function per field, applied once when a record is stored, and a dictionary from `(name, email)` to ids |
| 2 | Block, then score | A dictionary from key to ids, whose pairs are the candidates; `jaroWinkler`, `tokenJaccard` and a cached pair score |
| 3 | Group the matches | Union-find with the members of each root, and a guard that reads the cached scores |
| 4 | Grade a grouping | Pure functions over two partitions: pair sets for the pairwise measures, per-record sets for B-cubed |

The early choice that keeps the rest simple is to normalize once, when the record is stored, and to compare only normalized text afterwards. A first version that normalizes inside the score recomputes the same strings for every pair and, worse, is tempted to let the score and the blocking keys disagree about what a name is.

## Approach: block-score-union (Blocking keys then pair scores then guarded union-find)

### Intuition

Resolution is a pipeline of cheap filters in front of an expensive judge. Normalization removes differences that carry no information (case, spacing, punctuation, the order of a comma form). Blocking removes most pairs without looking at them. The score looks at what is left and says how alike two records are. Grouping turns pair decisions into entities. The one subtle step is the last one: a match is a statement about two records, an entity is a statement about all of its members, and the transitive closure of the first is not the second. The guard asks that a merge be acceptable to every pair across the two groups, which is complete linkage with a floor lower than the match threshold.

### Algorithm

1. Level 1: `normalizeName` lower-cases, swaps a single comma form, deletes apostrophes, turns other marks into spaces, splits, drops one leading title and joins. `normalizeEmail` trims and lower-cases. `addRecord` stores both normalized fields. `exactGroups` buckets the ids by `(name, email)`, skips the empty pair and returns the buckets of two or more.
2. Level 2: the keys of a record are `n:` plus the first three characters of its last name token, and `e:` plus the email. Put every id in the bucket of each of its keys, and the candidates are the pairs inside each bucket, collected in a set. `jaroWinkler` follows the six steps of the statement, with a window, a used-flag array for the second text, a comparison of the two matched sequences and the prefix bonus. `tokenJaccard` intersects two sets of tokens. `similarity` is `1` for a shared email, `0` for an empty name, and the weighted sum otherwise, and it is cached per ordered pair of ids.
3. Level 3: `components` runs union-find over `matches()`. `clusters` sorts the matches by decreasing score and then by id, and for each one with two different roots, checks every cross pair against the floor; only when all pass does it union, appending the smaller member list to the larger one. `canonical` and `aliases` read the group of the record and apply the three-key order.
4. Level 4: pairwise scores turn each partition into a set of pairs and compare the sets. B-cubed gives each id the set of its predicted group and the set of its gold group, and averages the two overlaps over the ids. `pairErrors` is the two set differences.

### Correctness

Normalization is a composition of total functions on strings, applied in the order of the statement, so each field has one clean form. The swap is decided on the lower-cased text before punctuation is touched, which is why `Doe, Mrs. Jane` ends with the title in front.

Blocking is exact for what it claims: a pair is a candidate if and only if its records share a key, because the buckets contain exactly the records that have the key. The pairs that are lost are exactly those with no common key, which the statement says are never compared.

Jaro-Winkler is the definition. The scan takes the first free equal character in the window, and `t` is used at most once, so `m` is well defined; the two matched sequences are permutations of each other, so `d` counts exactly the characters out of order; and `h = d / 2` is not rounded, which matters when `d` is 3. The boost is applied for every value of the Jaro score, as the statement says.

Union-find keeps one root per group, and appending the smaller member list to the larger gives each record at most `log R` moves. The guard loop is correct because the pairs are visited in a fixed order and a merge is made if and only if every cross pair passes: at the time of the merge, the two member lists are the groups. A refused pair is not retried, so a later merge of one of its groups can make it a pair inside a group without having been merged by it.

The pair and B-cubed measures follow their formulas, with the conventions for empty pair sets written in the statement (a grouping with no pairs makes no false claim, and a gold with no pairs has nothing to miss).

### Complexity

- Time: O(R + P w^2 + M k^2) — normalizing and keying the records is linear in their length; each candidate pair is scored once with a Jaro-Winkler that is quadratic in the name length in the worst case (a window scan per character); each of the `M` matches compares at most `k^2` cross pairs, all of them cached scores after the first time.
- Space: O(R + P) — the records, the buckets of keys and the cache of pair scores; `P` can be as large as `R^2` if one key is shared by all the records, which is the case blocking is supposed to avoid.

### Trade-offs

- Blocking is a bet on recall. A pair that shares no key is never found, and a key shared by too many records (a very common surname, a mailbox used by a department) brings back the quadratic cost. In practice one runs several blocking passes with different keys and takes the union, and caps or skips oversized blocks.
- A weighted sum of two measures is easy to explain and to tune, but it hides which measure drove a decision. Production systems often learn the weights, or the whole decision, from labelled pairs; the Fellegi-Sunter model does it with a likelihood ratio per field.
- Complete linkage is the strictest of the usual linkage rules: one dissimilar pair can keep two large groups apart. Average linkage is more forgiving, and single linkage is the plain closure that `components` computes. The guard is also order dependent (it visits the best pairs first), where other clustering methods are not.
- B-cubed and pairwise measures answer different questions. Reporting both, and the list of errors, is how one finds out whether the mistakes are a few large wrong merges or many small missed ones.

### Pitfalls and edge cases

- Level 1: a comma swaps the two parts only when it is the only comma; with two or more, every comma is punctuation. The title is dropped after the swap, only if another token remains, and only the first one. Apostrophes disappear but hyphens and dots become spaces. Two records with nothing left after normalization must not be grouped. A duplicate id is refused without changing the stored record.
- Level 2: the window is `max(0, floor(max(|s|, |t|) / 2) - 1)`, so texts of 1 to 3 characters only match at the same position. The transpositions are half the number of differing positions and are not rounded down; a case with three out-of-order characters tells the two apart. The prefix is capped at 4 and at the shorter length, and the boost has no threshold. Empty text scores 0, even against itself. Two empty emails are not "equal emails". A pair that would match but lies in two blocks is not in `matches()`.
- Level 3: the floor of the guard (0.65) is not the match threshold (0.75), and the guard checks every cross pair, candidates or not. Pairs are taken from the highest score, so the order of the ids is not the order of the merges. A shared email gives a score of 1 and joins records with different names: the guard sees the same score in the cross pairs it checks. The canonical record counts filled fields first, so a shorter name with an email beats a longer one without. Aliases exclude the canonical name and the empty name, and list each distinct name once.
- Level 4: a partition with no pairs has precision 1; a gold with no pairs has recall 1; both zero give an `f1` of 0, not a division by zero. B-cubed averages over the records and combines afterwards, so its `f1` is not the average of per-record scores. The order of groups and of ids inside them must not matter, and an id like `a10` sorts before `a9`.

### Language notes

- Python: `str.split()` with no argument drops empty tokens, and a `set` of tuples makes the pair sets one-liners. `itertools.combinations` on a sorted list gives each pair once with the smaller id first.
- TypeScript: a `Set` of arrays compares by reference, so pairs are stored as joined strings with a NUL separator (ids are printable). `split(" ")` keeps empty strings, so tokens are filtered. The default `sort()` of strings compares UTF-16 code units, which matches the statement for ASCII, and rows need an explicit comparator. The floating point operations are written in the same order as the statement's formula, so the two languages return the same doubles.

## Further reading

- W. E. Winkler, "String comparator metrics and enhanced decision rules in the Fellegi-Sunter model of record linkage", Proceedings of the Section on Survey Research Methods, American Statistical Association, 1990: the prefix adjustment of the Jaro comparator.
- M. A. Jaro, "Advances in record-linkage methodology as applied to matching the 1985 census of Tampa, Florida", Journal of the American Statistical Association, 1989: the original matching comparator.
- I. P. Fellegi and A. B. Sunter, "A theory of record linkage", Journal of the American Statistical Association, 1969: the probabilistic model that scores each field by a likelihood ratio.
- A. Bagga and B. Baldwin, "Algorithms for scoring coreference chains", 1998: the B-cubed measures; and E. Amigo, J. Gonzalo, J. Artiles and F. Verdejo, "A comparison of extrinsic clustering evaluation metrics based on formal constraints", Information Retrieval, 2009: why B-cubed satisfies properties that the pairwise measures do not.
- P. Christen, "Data Matching", Springer, 2012: a survey of blocking, comparison and classification, including the transitivity problem of clustering matches.
- [Union-find](https://en.wikipedia.org/wiki/Disjoint-set_data_structure): the disjoint-set structure with path compression and union by size.
