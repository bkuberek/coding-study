# Retrieval Metrics

## Statement

A team changes how its assistant retrieves documents, and wants to know whether the change helped before anyone reads an answer. They keep a fixed set of test queries. For each one, reviewers have judged some documents with a **grade**: 0 for not relevant, and 1 to 3 for more and more useful. Write `retrievalMetrics`, which scores the retriever's rankings for these queries with three metrics and averages each over the queries.

For one query, a document is **relevant** when its grade is at least 1. A document nobody judged has grade 0. Only the first `k` documents of the ranking count, and a ranking shorter than `k` counts what it has. Ranks start at 1.

- **Recall at k**: the number of relevant documents in the first `k`, divided by the number of relevant documents judged for the query, retrieved or not.
- **Reciprocal rank at k**: `1 / r`, where `r` is the rank of the first relevant document in the first `k`; 0 when there is none.
- **nDCG at k**, which rewards putting the most useful documents first:

```text
DCG@k  = sum over ranks i = 1 .. min(k, ranking length) of (2^grade_i - 1) / log2(i + 1)
IDCG@k = the same sum over the query's judged grades sorted from highest to lowest, cut at k
nDCG@k = DCG@k / IDCG@k
```

`grade_i` is the grade of the document at rank `i`, and `log2` is the logarithm in base 2, so rank 1 is not discounted (`log2(2) = 1`). The ideal ranking in `IDCG@k` puts every judged document in grade order, including the ones the retriever never found.

**Averaging.** Each metric is the plain mean of its per-query values. A query with no relevant document has no meaningful recall, reciprocal rank or nDCG, so it is **left out** of all three means. If every query is left out, all three results are 0.

## Input

- `rankings`: for each query, the retrieved document ids, best first. A ranking holds no id twice.
- `judgedDocs`, `grades`: for each query, the judged document ids and their grades: `grades[q][j]` is the grade of `judgedDocs[q][j]`. A query judges no id twice.
- `k`: how many documents of each ranking count.

## Output

`[mean recall at k, mean reciprocal rank at k, mean nDCG at k]`, compared with a relative tolerance of `10^-9`.

## Examples

### Example 1

<!-- case: ex1 -->

Three documents are relevant: `d1`, `d3` and `d4`. The first three retrieved are `d3` (grade 1), `d1` (grade 3) and `d7`, which nobody judged. That finds two of the three, so recall is `2/3`, and the first one is at rank 1. `DCG@3 = 1/1 + 7/log2(3) + 0`, and the ideal grades `[3, 2, 1]` give `IDCG@3 = 7/1 + 3/log2(3) + 1/2`, so nDCG is about `0.577`.

### Example 2

<!-- case: ex2 -->

The second query judged only `x`, as not relevant, so it is left out and the means are those of the first query. Its one relevant document is at rank 2: reciprocal rank `1/2`, and nDCG `(3 / log2(3)) / 3`.

### Example 3

<!-- case: ex3 -->

With `k = 2`, the first query's `r` at rank 3 does not count: recall `1/2`, reciprocal rank `1/2`. The second query finds one of three: recall `1/3`, reciprocal rank 1. Each mean averages the two queries equally, so recall is `(1/2 + 1/3) / 2`.

## Constraints

- `1 <= rankings.length == judgedDocs.length == grades.length <= 1000`.
- `0 <= rankings[q].length <= 1000`, and `judgedDocs[q].length == grades[q].length <= 1000`.
- `0 <= grades[q][j] <= 3`.
- `1 <= k <= 1000`.
- Ids are 1 to 20 characters long and compared exactly.

## Follow-ups

- Two retrievers differ by 0.01 in mean nDCG over 50 queries. How would you decide whether that difference is real?
- Judgments cover only the documents someone looked at. What does that do to recall for a new retriever that finds documents nobody judged?
- Report each metric per query as well as the mean. Which queries would you read first?
- Some teams count a query without relevant documents as 0, or as 1. What does each choice do to the comparison of two retrievers?

## Hints

### Hint 1

Turn each query's judgments into a lookup from id to grade. Every metric then reads the grades of the first `k` retrieved documents, with 0 for the unjudged ones.

### Hint 2

Write one function that computes DCG from a list of grades in rank order, and call it twice: on the retrieved grades, and on all the judged grades sorted from highest to lowest and cut at `k`.

### Hint 3

Decide what a query with no relevant document returns before you average: it is skipped, not counted as 0.
