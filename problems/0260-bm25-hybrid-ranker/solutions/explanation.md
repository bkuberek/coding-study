# BM25 Hybrid Ranker: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| postings-and-fusion | optimal | O(t + q + n log n + h log h) | O(t + h + q) | default answer |

`t` is the total number of tokens, `q` the number of query tokens, `n` the number of documents and `h` the number of vector hits.

## Approach: postings-and-fusion (Build postings for the query terms and fuse the two rankings by rank)

### Intuition

BM25 is a small argument about evidence. A rare term says more than a common one, so `idf` weighs it up. The third mention of a word says less than the first, so `tf` saturates. A long document has more chances to mention anything, so length is held against it. All of it fits on one line, and the parameters say how strongly each effect applies.

Fusion is the other small argument. A BM25 score of 12 and a cosine of 0.8 have no common scale, and normalizing them is fragile, because a single strong outlier squeezes every other score. Ranks have no such problem: being first means the same thing in any list. So you throw the scores away after they have done their job, and you add `1 / (k + rank)`. A document that both searches like beats a document that only one loves, unless `k` is small enough that the very top place dominates.

The one thing fusion cannot do for you is decide who gets a rank. Only a real result gets one. If every document is sorted and ranked, a document with no query term gets a keyword rank just by existing, and it collects fused score for nothing.

### Algorithm

1. Make an empty count table per distinct query term, and fill the tables in one pass over the tokens.
2. Compute `avgdl` over all documents and, for each term, `df` as the size of its table.
3. For each term and each document in its table, add the term's contribution to that document's score. Documents in no table get no score.
4. Sort the keyword scores and the vector scores by score descending, then by document index.
5. For each ranking, add `1 / (rrfK + rank)` to each listed document, with ranks from 1.
6. Sort the fused scores the same way, and return the first `topN` documents.

### Correctness

Each distinct term's table counts its occurrences per document, so the table's size is `df` and each entry is `tf`, and the contribution written in step 3 is the stated formula. A document gets a score exactly when it holds a query term, which makes the keyword ranking the stated one. A holder has at least one token, so `avgdl` is above zero wherever it is divided by, and a corpus of empty documents never reaches the division. The fused score adds one term per ranking the document appears in, with ranks from 1. All three sorts use the same total order, score then index, so the output is fully determined.

### Complexity

- Time: O(t + q + n log n + h log h) — one pass over the tokens, the table setup per query token, and three sorts, of at most `n`, `h` and `n + h` documents.
- Space: O(t + h + q) — the tables hold one per query term and at most one entry per token, and the scores hold one per document with a query term or hit.

### Trade-offs

The tables here are postings for one query. A real index builds them once for every term, so a query reads only its own terms and skips the pass over the tokens, at the cost of building and updating the index. A scan of each document per term is simpler, and it costs `O(t q)`, which you would feel on a large corpus.

The parameters are worth knowing. `b = 0` turns length normalization off, and `b = 1` applies it fully. `k1` near 0 makes `tf` almost irrelevant, and a large `k1` lets repeats keep counting. The usual `rrfK` is around 60, which keeps the top places from dominating and rewards agreement between the lists; with a value as small as 1, first place can beat a document that placed well in both.

This `idf` is the variant with `1 +` inside the logarithm, which stays positive for every term. It matters for a corpus where a term is in most documents.

### Pitfalls and edge cases

- **Giving every document a keyword rank.** This is the classic hybrid bug: sorting all documents means non-matching ones collect `1 / (k + rank)`, and they push real results down and appear in the output (`h1`).
- **The older `idf`.** `ln((N - df + 0.5) / (df + 0.5))` goes negative when a term is in more than half the documents, so a document is punished for containing the term (`h10`). Clamping it to zero makes such a term worthless, so documents can no longer be told apart by it (`h11`).
- **Counting a repeated query term twice.** `index index` is one term (`h6`).
- **No saturation.** Without the denominator, repeating one word beats covering the query (`h12`).
- **Length normalization.** The average covers all `N` documents, empty ones and non-matching ones included (`h7`, `h9`). `df` counts documents and not occurrences (`h8`). Getting `b` backwards rewards long documents (`h14`).
- **Fixed parameters.** `k1`, `b` and `rrfK` come from the caller, and hard-coding the usual values changes results (`h15`, `h27`, `h28`).
- **Ranks from 0.** With a small `rrfK` that changes who wins (`h19`).
- **Adding scores instead of ranks.** That is the thing fusion exists to avoid (`h20`, `h23`).
- **Reading the hits in list order.** They arrive unsorted, so you rank them by score (`h17`).
- **Dropping negative similarity.** It is a low score, not a missing one (`h7`, `h18`).
- **Tie-breaks.** All three sorts fall back to the lower index, however the tied documents were found (`ex2`, `h16`, `h21`).
- **Empty input.** An empty query, no hits, or a corpus of empty documents must not divide by zero (`h2`, `h3`, `h4`, `h5`).
- **Partial token matches.** `caches` is not `cache`, and neither is `Cache` (`h24`).

### Language notes

- Python: `sorted(scores, key=lambda d: (-scores[d], d))` is the whole tie-break. `dict.fromkeys(query)` removes duplicates and keeps the order, where a `set` would add the terms in a different order on each run, because string hashes are seeded per process.
- TypeScript: `a - b` as the final comparator keeps document indexes numeric, since `sort()` with no comparator would compare them as strings. A `Map` built from `query` removes duplicates and keeps the order. `Math.log` is the natural logarithm.
