# Entity Resolution

## Statement

Build `EntityResolver`, a small tool that finds the records that describe the same real-world thing. A customer list may hold `Maria Gonzalez`, `GONZALEZ, Maria` and `maria gonzales` as three rows, and a person reading them knows it is one customer. A program has to decide that from the text. This task is called *entity resolution* (or record linkage, or deduplication), and it is usually done in four steps, one per level: clean the records so that the same thing is written the same way, avoid comparing every record with every other, score the pairs that remain and decide which are the same, then group the matches into entities and check how good the grouping is. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**Why not compare everything?** Comparing every pair of `n` records takes about `n^2 / 2` comparisons, which is far too many for a million records. *Blocking* gives each record a few cheap *keys* and only compares records that share a key. It trades some missed matches (two records that match but share no key are never compared) for a large saving.

**Why grouping is harder than matching.** If record A matches B and B matches C, it is tempting to say that A, B and C are one entity. But matching is not transitive: A and C may be quite different, and a chain of small differences can lead from a name to another person's name. Level 3 groups matches with union-find, shows this problem, and fixes it with a guard.

A record has an `id` (unique), a `name` and an `email`. The email can be empty.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 65, level 3 by 95 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `EntityResolver()`: creates an empty resolver.
- A record `id` is 1 to 10 printable ASCII characters (codes 33 to 126, so no space), compared exactly as given. A `name` and an `email` are 0 to 60 printable ASCII characters (codes 32 to 126, spaces allowed), so case folding means turning `A` to `Z` into `a` to `z`.
- Each level's section describes the methods it adds and their parameters.

## Output

Methods that change the resolver return a `bool`. Questions return a `string`, a number, a list of texts or a list of lists. "Sorted" means that texts are compared by the numeric value of their characters, so `B` comes before `a` and `a10` before `a2`; lists of texts are sorted that way, and lists of lists by their first entry, then their second, and so on. A pair of record ids is always written with the smaller id first. Numbers are checked to within `1e-6`.

## Level 1: Normalized records

Records are cleaned before they are compared. All the rules are exact, and they apply to every method of every level.

- `normalizeName(name)`: the clean form of a name, built by these steps in order:
  1. Turn `A` to `Z` into `a` to `z`.
  2. If the text has **exactly one** comma, swap the two parts: the new text is the part after the comma, a space, then the part before it. (`smith, john` becomes ` john smith`.) With no comma, or with two or more, nothing is swapped, and every comma is punctuation for the next step.
  3. Delete every apostrophe `'`. Replace every other character that is not `a` to `z`, `0` to `9` or a space by a space. (`o'brien` becomes `obrien`, `mary-jane` becomes `mary jane`, `j.r.r.` becomes `j r r`, and a comma that was not swapped becomes a space.)
  4. Split the text into **tokens**, the maximal runs of characters other than a space. Spaces at the ends and runs of spaces vanish.
  5. If there are at least two tokens and the first one is `mr`, `mrs`, `ms`, `miss`, `dr` or `prof`, drop that first token (only that one, only once).
  6. Join the tokens with single spaces. The result is `""` when there are no tokens.
- `normalizeEmail(email)`: the email without spaces at the start and the end, turned to lower case, and nothing else. Spaces inside, dots and `+` tags stay.
- `addRecord(recordId, name, email)`: stores a record with its normalized name and email. It returns `false` and changes nothing when the id is already used.
- `normalized(recordId)`: the list `[normalized name, normalized email]` of a record, or `[]` for an id that is not stored.
- `exactGroups()`: the groups of two or more records that have the same normalized name **and** the same normalized email, each group as its sorted ids, the groups sorted. A record whose normalized name and normalized email are both empty is never in a group, since it says nothing. A record with an empty name and an email can be grouped with one that has the same email.

The order of the steps matters. The swap happens before the punctuation is removed and before the title is looked for, so `Doe, Mrs. Jane` becomes `jane doe`. A title that is not the first token after the swap stays: `Dr. Smith, John` becomes `john dr smith`.

### Example 1

<!-- case: ex1 -->

The first three names show the case folding, the comma swap and the dropped title. `O'Brien, Mary-Jane` is swapped first, then the apostrophe is removed and the hyphen turned into a space. The email loses its spaces and its capitals. The second `addRecord` with the id `r1` is refused and does not change the stored record, and an unknown id has no normalized form.

### Example 2

<!-- case: ex2 -->

`r1` and `r2` have the same name after the swap and the same email after trimming, so they form a group. `r3` and `r4` agree on the name and both have no email. `r5` and `r6` are only punctuation, so their normalized name and email are both empty, and they never group. `r9` has the name of `r7` and `r8` but another email, so it is not in their group.

## Level 2: Blocking and pair scores

Two things are needed to decide whether two records match: a way to avoid most comparisons, and a score for the pairs that are compared.

**Blocking keys.** The keys of a record are:

- `n:` followed by the first 3 characters of the **last token** of its normalized name (all of it when it is shorter), when the normalized name is not empty;
- `e:` followed by the normalized email, when the email is not empty.

Two records are **candidates** when they share at least one key. Only candidates are ever compared by `matches` and by the levels after it.

- `blockingKeys(recordId)`: the keys of a record, sorted, or `[]` for an unknown id or a record without keys.
- `candidatePairs()`: every pair of candidates once, as `[smaller id, larger id]`, sorted.

**Jaro-Winkler similarity** measures how alike two texts are, from 0 (nothing in common) to 1 (equal). It counts the characters that appear at nearly the same place in both texts, subtracts a little for characters that appear in a different order, and finally rewards a common beginning, which suits names. For texts `s` and `t`, compared as given (case counts, spaces are characters):

1. If either text is empty the similarity is 0.
2. The **window** is `w = max(0, floor(max(|s|, |t|) / 2) - 1)`.
3. Go through `s` from left to right. The character `s[i]` **matches** the first character `t[j]` that has not matched yet with `|i - j| <= w` and `t[j] = s[i]`, when there is one. A character of `t` matches at most once. Let `m` be the number of matches. If `m = 0` the similarity is 0.
4. Write the matched characters of `s` in the order of `s`, and the matched characters of `t` in the order of `t`. Both lists have `m` characters. Let `d` be the number of positions where the two lists differ, and `h = d / 2`: the number of **transpositions**, a real number that is **not rounded** (`d` can be odd).
5. The **Jaro** similarity is `(m / |s| + m / |t| + (m - h) / m) / 3`.
6. Let `l` be the length of the longest common prefix of `s` and `t`, at most 4. The **Jaro-Winkler** similarity is `jaro + l * 0.1 * (1 - jaro)`. The boost applies whatever the Jaro value is.

This is the definition given on the usual reference pages. Libraries differ in details that this problem fixes as above: some round `h` down, some apply a threshold of 0.7 to the boost, and some always scan the shorter text instead of `s`.

**Token Jaccard.** The tokens of a text are its maximal runs of non-space characters. `tokenJaccard(s, t)` is the number of distinct tokens in both texts divided by the number of distinct tokens in either, compared exactly as given, and `0` when neither text has a token.

- `jaroWinkler(first, second)` and `tokenJaccard(first, second)`: these two measures of two texts as given.
- `similarity(first, second)`: the score of two stored records, a number from 0 to 1. Let `a` and `b` be the normalized names, and let `a` be the name of the record with the smaller id. The score is:
  - `1` when the two normalized emails are equal and not empty;
  - otherwise `0` when either normalized name is empty;
  - otherwise `0.7 * jaroWinkler(a, b) + 0.3 * tokenJaccard(a, b)`.

  It is `0` when an id is not stored.
- `isMatch(first, second)`: `true` when both ids are stored and `similarity(first, second) >= 0.75`. This looks at the two records only, and ignores blocking.
- `matches()`: the candidate pairs for which `isMatch` is `true`, in the order of `candidatePairs`. A pair of records that would match but share no key is not among them.

### Example 1

<!-- case: ex3 -->

`r1`, `r2`, `r3` and `r4` all have `gon` as the start of their last name token, so they are all candidates of each other, while `r5` shares nothing. `r1` and `r2` differ by one letter and score `0.78`. `r1` and `r3` score about `0.6367`, below `0.75`, since `maria` and `mario` differ and the surnames do too. `r1` and `r4` have the same email, so their score is `1` whatever the names are. `r1` and `r5` are not candidates, and are not a match either.

### Example 2

<!-- case: ex4 -->

The first three values are the ones usually quoted for this definition (the original 1990 paper may tabulate somewhat different numbers for some pairs, likely because the comparator it describes makes further adjustments; this problem uses the plain definition): for `MARTHA` and `MARHTA` there are 6 matches, 2 characters out of order so one transposition, a Jaro value of `0.9444` and a common prefix of 3, which gives `0.9611`. Equal texts score 1 and texts with no character in common score 0. `john a smith` and `smith john` share two of three distinct tokens. Repeated tokens count once, and two empty texts give 0.

## Level 3: Clusters and canonical records

An **entity** is a group of records that stand for one thing. The simple way to build entities is to take every match as a link and join everything that is linked, which is a job for union-find (a structure that keeps a set of disjoint groups and merges two of them in nearly constant time). It has a flaw.

**The transitivity pitfall.** `A ~ B` and `B ~ C` do not mean `A ~ C`. A chain of small differences (`maria gonzalez`, `maria gonzales`, `mario gonzales`) joins names that are two edits apart and may be two different people. The simple grouping is still useful as a baseline, so it stays:

- `components()`: the connected components of the graph whose links are `matches()`, every record in one, as sorted groups of sorted ids. A record without matches is a group of its own.

**The guard.** `clusters()` builds the same groups but refuses a merge that would join dissimilar records:

1. Take the pairs of `matches()` in order of decreasing `similarity`, equal scores by the smaller id of the pair, then by the larger.
2. For each pair, find the groups of its two records. If they are the same group, do nothing. Otherwise **merge** them only if `similarity` is at least `0.65` for **every** pair made of one record of the first group and one record of the second (matches or not, candidates or not). Otherwise leave both groups alone.
3. The answer is the final groups as sorted groups of sorted ids, singletons included, in the same format as `components()`.

A merge is thus judged on the whole of both groups, and the floor `0.65` is lower than the match threshold `0.75`: records that would not match each other can still share a group when they are close enough, and records that match can be kept apart when a third record in their groups is not close.

- `canonical(recordId)`: the id of the **canonical record** of the entity (a `clusters()` group) of the record, which is the record that stands for the entity: the one with the most filled fields (a normalized name that is not empty counts one, and so does a normalized email that is not empty), then the longest normalized name, then the smaller id. It is `""` for an unknown id.
- `aliases(recordId)`: the other names of the entity: the distinct normalized names of its records, without the normalized name of the canonical record and without the empty name, sorted. `[]` for an unknown id or an entity with one name.

Every method answers for the records stored now, so the groups follow `addRecord`.

### Example 1

<!-- case: ex5 -->

The matches chain `r1`, `r2`, `r3` and `r4`, so `components()` joins all four. `clusters()` merges `r1` with `r4` (score 1), then `r2` into them, and keeps `r3` out: `r1` and `r3` score `0.6367`, below the floor of `0.65`, even though `r2` and `r3` match. `r1` is the canonical record of the entity `{r1, r2, r4}`: `r1` and `r4` have both a name and an email, `r2` only a name, and `r1` and `r4` tie on the length of the name, so the smaller id wins. The only alias of the entity is the one different name, `maria gonzales`, and `r3` is canonical for itself with no alias.

### Example 2

<!-- case: ex6 -->

The three `Murray` records are joined by two matches, and `k2` and `k3` score `0.7083`: not a match, but above the floor, so the guard lets the group form. `Tim Baker` matches `Tom Baker`, which matches `Tom Bakker`, but `t1` and `t3` score `0.6347`. The pair with the highest score, `t2` and `t3`, is merged first, and then `t1` cannot join them. `k1` and `k2` have the same length of name, so the smaller id `k1` is canonical, and `t3` has the longer name than `t2`.

## Level 4: Grading the clusters

How good is a grouping? With a list of **gold** groups (the true entities, known for a test set) there are two common ways to answer, and they disagree in useful ways. In this level the two groupings are arguments, so that any grouping can be graded, including the output of `clusters()` and of `components()`. Both are partitions of the same set of ids: every id is in exactly one group of each.

- `pairwiseScores(predicted, gold)`: `[precision, recall, f1]` over **pairs**. The predicted pairs are all the pairs of ids in a same predicted group, and the gold pairs those in a same gold group. With `hits` the number of pairs in both:
  - `precision = hits / (number of predicted pairs)`, and `1` when there are no predicted pairs;
  - `recall = hits / (number of gold pairs)`, and `1` when there are no gold pairs;
  - `f1 = 2 * precision * recall / (precision + recall)`, and `0` when both are 0.
- `bcubedScores(predicted, gold)`: `[precision, recall, f1]` by **B-cubed**, which scores each record and averages over the records. For a record `e`, let `P(e)` be its predicted group and `G(e)` its gold group. The precision of `e` is `|P(e) ∩ G(e)| / |P(e)|` and its recall is `|P(e) ∩ G(e)| / |G(e)|`. The precision and the recall of the grouping are the averages over all the records, and `f1` is computed from them as above.
- `pairErrors(predicted, gold)`: the rows `["false-merge", a, b]` for every pair `a < b` that is predicted together and not in gold, and `["missed", a, b]` for every pair in gold and not predicted, sorted.

**Why two measures?** A group of `k` records holds `k (k - 1) / 2` pairs, so in pairwise scores one large entity weighs far more than many small ones, and a single wrong merge of large groups collapses precision. B-cubed gives each record the same weight. Neither is better in general: pairwise answers "how many of my links are right", B-cubed "how good is the group around a typical record".

### Example 1

<!-- case: ex7 -->

The gold groups are `{a, b, c}`, `{d, e}` and `{f}`. Predicting `{a, b}`, `{c}`, `{d, e}` and `{f}` makes no false link, so precision is 1, but it misses `a c` and `b c`: of 4 gold pairs, 2 are found, so recall is `0.5` and `f1` is `2/3`. For B-cubed, `a` and `b` have recall `2/3` and `c` has `1/3`, the others `1`: the average is `0.7778`. Putting all six records in one group finds every gold pair but 11 of its 15 pairs are false: precision `4/15`. B-cubed precision is `0.3889`, higher, because `d`, `e` and `f` weigh as much as `a`.

### Example 2

<!-- case: ex8 -->

The first value is the output of `clusters()` for the five records of level 2 (`r1`, `r2` and `r4`, then `r3`, then `r5`), graded against the gold groups `{r1, r2, r3, r4}` and `{r5}`. The guard made no false link and kept `r3` apart, so the precision is 1 and three gold pairs are missed. The last values of the example list those errors.

## Constraints

- At most 400 calls per test and at most 200 records stored.
- A group list holds each id of its partition once, and `predicted` and `gold` hold the same ids; there is at least one id.
- No score used to take a decision is within `10^-9` of `0.75` or `0.65`. Two pairs can have the same score, and then the ids decide, but when the score is below 1 the tests give the same answer whichever of the two comes first, since the last digit of a score depends on how it is computed.
- Every text is printable ASCII, so there is nothing to normalize at the level of Unicode.

## Follow-ups

- The guard tests a merge the way complete linkage does: every cross pair must score at least 0.65. It is not complete-linkage clustering, which merges the two groups whose worst cross pair is best, whereas the guard visits the pairs by their best single score, which is why the order matters. What would a single-linkage test give (that is `components`), and what an average-linkage test? Which one splits a chain like `maria gonzalez, maria gonzales, mario gonzales` the way you want?
- Two people can share an email, such as a shared office mailbox, and then the score is 1 and the guard cannot see the difference. How would you give a key a weight, or count how many records use it?
- Blocking by the first three letters of the last token loses `Smith` against `Smyth`, and a name written first-name-last is in another block. Which cheaper or more tolerant keys (sorted tokens, phonetic codes, n-grams, several keys at once) would you add, and what does each cost in comparisons?
- Choosing the threshold 0.75 and the floor 0.65 by hand is fragile. How would you choose them from a labelled sample, with the pair precision and recall of level 4?
- The canonical record is chosen by a fixed rule. What changes when each field carries its own trust, and the entity is built from the best field of each record instead of one record?

## Hints

### Hint 1

Start with the cleaning, since everything else depends on it. Take a name and apply the steps one at a time on paper: lower case, then the comma, then punctuation, then split into words and look at the first word, then join. Write one function for each step and test it with a few names before you build a class around it.

### Hint 2

Comparing every pair is the slow way. Make a dictionary from each key to the list of record ids that have it, then for each list make all the pairs inside it. A pair can come from several lists, so collect the pairs in a set and sort them at the end.

### Hint 3

For Jaro-Winkler, do it in three small pieces. First find the matches: a list of "used" flags for the second text, and for each character of the first text the first unused equal character inside the window. Then compare the two lists of matched characters position by position to count the differences. Then put the numbers in the formula. Check yourself on `MARTHA` and `MARHTA` (0.9611) before anything else.

### Hint 4

Union-find keeps one parent per id. `find` follows the parents up to a root and can shorten the path as it goes, and `union` hangs one root under the other. For the guard you also need the members of each group: keep a list per root, and when two groups merge, append the smaller list to the larger.

### Hint 5

The guard compares every record of one group with every record of the other, so a score is looked up many times. Compute the score of a pair once and keep it in a dictionary keyed by the two ids in order. Remember that the floor for the guard (0.65) is not the threshold for a match (0.75).

### Hint 6

For the canonical record, sort the members by a tuple that already contains all three tie-breaks: minus the number of filled fields, minus the length of the normalized name, and the id, so that the most filled and the longest sort first. The first member is the canonical one; the aliases are the other distinct names.

### Hint 7

For B-cubed, build for every id the set of the ids in its predicted group and the set in its gold group. The precision of the id is the size of the intersection divided by the size of the first set, and the recall is the same intersection divided by the size of the second. Average over the ids, and only then compute `f1`; it is not the average of the `f1` of each record.
