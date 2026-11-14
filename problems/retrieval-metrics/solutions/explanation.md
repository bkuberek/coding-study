# Retrieval Metrics: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| grade-lookup | optimal | O(r + j log j) | O(j) | default answer |

`r` is the number of retrieved documents read, at most `k` per query, and `j` the number of judgments.

## Approach: grade-lookup (Look up each retrieved document's grade and sort the judged grades for the ideal ranking)

### Intuition

All three metrics read the same thing: the grades of the first `k` retrieved documents, in rank order. Build a lookup from id to grade per query, turn the top of the ranking into a list of grades, and every metric is a short pass over that list.

They answer different questions. Recall asks how much of what matters was found. Reciprocal rank asks how far a reader has to scroll to the first useful document. nDCG asks whether the most useful documents came first: each document gains `2^grade - 1`, so a grade 3 is worth seven grade 1s, and a gain at rank `i` is divided by `log2(i + 1)`, so lower places count for less. DCG has no fixed scale, so it is divided by the best DCG this query could have had, which puts it between 0 and 1.

That best ranking is the part people get wrong. It is built from every judged document, not from the retrieved ones: a retriever that finds one mediocre document and puts it first has not produced a perfect ranking, because a better document existed.

### Algorithm

1. For each query, build a map from judged id to grade, and count the relevant ones (grade at least 1). If there are none, skip the query.
2. Take the first `k` ids of the ranking and look up their grades, with 0 for an unjudged id.
3. Recall: the relevant grades among them, divided by the relevant count.
4. Reciprocal rank: `1 / rank` of the first relevant grade among them, else 0.
5. nDCG: DCG of the retrieved grades divided by DCG of all the judged grades sorted from highest to lowest and cut at `k`.
6. Average each metric over the queries that were not skipped, or return zeros when all were.

### Correctness

Each step computes the stated formula over the stated documents: the first `k` of the ranking, unjudged ones at grade 0. The ideal list is the judged grades in descending order, which maximizes DCG, since a larger gain at an earlier rank never lowers the sum. A query with a relevant document has a positive ideal DCG, so the division is safe, and queries without one never reach it. Skipping them before averaging gives the stated means.

### Complexity

- Time: O(r + j log j) — one lookup per retrieved document read, and one sort of each query's judged grades.
- Space: O(j) — the lookup and the sorted grades of one query at a time.

### Trade-offs

The grades are 0 to 3, so the ideal list could be built by counting each grade instead of sorting, in `O(j)`. The sort is clearer, and the judgments of one query are small.

The three metrics fit different products. Reciprocal rank suits a single answer, where only the first good document matters. Recall suits retrieval for a model, where the model reads all `k` and missing a relevant document is the failure. nDCG is the one that uses the grades, so it is the one to watch when "somewhat useful" and "exactly right" should not count the same.

Leaving out queries without relevant documents is the usual choice in evaluation. Counting them as 0 would penalize every retriever equally and shrink real differences, and counting them as 1 would reward a retriever for nothing.

### Pitfalls and edge cases

- **The ideal ranking from the retrieved documents.** Sorting the retrieved grades gives every ranking that found few documents a high nDCG. The ideal holds every judged document (`h1`, `ex1`).
- **The ideal ranking not cut at k.** Then a perfect top `k` scores below 1 whenever more than `k` documents are relevant (`h2`).
- **The ideal in the wrong order.** It must be sorted from highest grade to lowest, whatever order the judgments arrive in; otherwise nDCG can exceed 1 (`h13`).
- **The discount.** Rank `i` is divided by `log2(i + 1)`. With 0-based ranks, `log2(0 + 1)` is 0 and the first term divides by zero. An older form divides by `log2(i)` and leaves rank 1 alone, which also leaves rank 2 undiscounted (`h3`). The base itself cancels in nDCG, since it scales DCG and ideal DCG by the same factor, so natural logarithms on both sides give the same result; a different base on each side does not.
- **The gain.** `2^grade - 1`, not the grade: a linear gain changes how much a grade 3 at the top is worth (`h4`).
- **Queries without relevant documents.** They are left out of every mean, not counted as 0, and when all are left out the result is zeros (`ex2`, `h5`, `h6`). A grade of 0 is a judgment of "not relevant" (`h10`).
- **Macro, not micro.** Recall is averaged per query. Pooling found and relevant counts over all queries weighs queries with many relevant documents more (`h7`).
- **Looking past k.** The reciprocal rank of a relevant document at rank `k + 1` is 0 here (`h8`).
- **Recall's denominator.** All relevant documents, even when there are more than `k`; dividing by `min(k, relevant)` is a different metric (`h9`).
- **Short and unjudged.** A ranking shorter than `k`, an empty ranking, and documents nobody judged, which have grade 0 (`h11`, `h12`).

### Language notes

- Python: `dict(zip(ids, grades))` is the lookup, and `zip(*rows)` turns the per-query triples into three columns to average. `math.log2` is exact for powers of two.
- TypeScript: a `Map` from id to grade, with `?? 0` for unjudged ids. `Math.log2` is the base-2 logarithm, and `2 ** grade` the gain.
