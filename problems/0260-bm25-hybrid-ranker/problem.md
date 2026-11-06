# BM25 Hybrid Ranker

## Statement

A help center retrieves articles for an assistant to read before it answers, and it searches in two ways. A keyword search finds exact terms such as an error code. A vector search finds articles with a similar meaning and different words. Each one misses what the other catches, so you combine them. Their scores cannot be added, because they are on unrelated scales, so you combine their **ranks** instead.

The vector search has already run: you get its hits and their scores, and no model is called here. The documents are already tokenized. Write `hybridRank` in three steps.

**Step 1: the keyword ranking, by BM25.** Let `N` be the number of documents, `avgdl` the mean length of all `N` documents in tokens, and for a query term `t`, `df(t)` the number of documents that contain `t`. A repeated query term counts once. The score of a document `d` is the sum, over the distinct query terms in `d`, of

```text
idf(t) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * |d| / avgdl))

idf(t) = ln(1 + (N - df(t) + 0.5) / (df(t) + 0.5))
```

where `tf` is how many times `t` occurs in `d`, `|d|` is the length of `d`, and `ln` is the natural logarithm.

The keyword ranking holds only documents that contain at least one query term, best score first, with ties going to the lower document index. **A document with no query term has no keyword rank at all.**

**Step 2: the vector ranking.** It holds exactly the hits, best score first, with ties going to the lower document index. A hit keeps its place in the ranking even with a negative score.

**Step 3: reciprocal rank fusion.** A document's fused score is the sum, over the rankings it appears in, of `1 / (rrfK + rank)`, where the best place in a ranking has rank 1. Return the indexes of the `topN` documents with the highest fused scores, best first, with ties going to the lower document index. A document in neither ranking is never returned, and fewer than `topN` documents come back when fewer qualify.

## Input

- `documents`: each document as its list of tokens, already lowercased and split. Tokens are compared exactly.
- `query`: the query as a list of tokens.
- `vectorHits`, `vectorScores`: `vectorScores[i]` is the similarity score of the document with index `vectorHits[i]`, in no particular order.
- `k1`, `b`: the BM25 parameters. `k1` controls how fast repeated terms stop adding score, and `b` how much a long document is penalized.
- `rrfK`: the fusion constant. A larger value flattens the difference between places in a ranking.
- `topN`: how many documents to return at most.

## Output

The document indexes, best first.

## Examples

### Example 1

<!-- case: ex1 -->

The keyword ranking is `[0, 1]`: document 0 has both terms, document 1 only `password`, and documents 2 and 3 have neither. The vector ranking is `[2, 1, 0]`. The fused scores are `1/61 + 1/63` for document 0, `1/62 + 1/62` for document 1, and `1/61` for document 2. Document 3 is in neither ranking.

### Example 2

<!-- case: ex2 -->

Only document 3 has `retry`, and only document 1 is a vector hit, so each is ranked first in one list and has a fused score of `1/61`. The tie goes to the lower index.

### Example 3

<!-- case: ex3 -->

Document 0 says `cache` twice, but it is five times as long. With `b = 0.75` that length costs it more than the repeat gains: its score is `idf * 4.4 / 3.8`, and document 1's is `idf * 2.2 / 1.6`.

## Constraints

- `1 <= documents.length <= 10^4`, with at most `10^6` tokens in total. A document may be empty.
- `0 <= query.length <= 100`. Tokens are 1 to 40 characters long.
- `0 <= vectorHits.length == vectorScores.length <= documents.length`. Each hit is a valid document index, and no hit repeats.
- `-1 <= vectorScores[i] <= 1`.
- `0 < k1 <= 10`, `0 <= b <= 1`, `1 <= rrfK <= 1000` and `1 <= topN <= 1000`.
- No test depends on the order in which the parts of one score are added.

## Follow-ups

- Give each ranking a weight, so that exact matches can count for more when a query looks like an error code.
- Index once and answer many queries. What can be computed ahead of time, and what depends on the query?
- A new document changes `N`, `avgdl` and some `df` values. What would you recompute, and which approximations are safe?
- Why is `rank` used here and not a normalized score? Think about what happens to a normalized score when one strong outlier arrives.

## Hints

### Hint 1

Only the query terms matter, so a table of counts per query term is all you need from each document.

### Hint 2

Write one helper that takes scores and returns the documents best first with the tie-break. All three orderings use it.

### Hint 3

Decide what happens to a document with a score of zero before you sort.
