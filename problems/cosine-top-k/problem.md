# Cosine Top K

## Statement

Before an assistant answers a question, a retrieval step finds the passages it should read. Every stored passage has an embedding, a vector of numbers, and the question gets one too. The passages whose vectors point most nearly the same way as the question's are the most likely to be about the same thing. Write `topKCosine`, which returns the indexes of the `k` best documents, best first.

The score of a document is its cosine similarity with the query:

```text
cosine(q, d) = (q · d) / (|q| * |d|)

q · d = q[0] * d[0] + q[1] * d[1] + ... + q[m - 1] * d[m - 1]
|v|   = sqrt(v · v)
```

The rules:

- A higher score is better. **Equal scores go to the lower index.**
- A document whose numbers are all zero has no direction, so it has no score: it is skipped and never returned.
- A query whose numbers are all zero gives no document a score, so the result is empty.
- A negative score is still a score. A document that points away from the query is returned when it is among the `k` best.
- When fewer than `k` documents have a score, all of them are returned.

The collection is large and `k` is small. Aim for `O(n m + n log k)` time and `O(k)` memory besides the input, where `n` is the number of documents and `m` the length of a vector: the scores of all `n` documents are never needed at once.

## Input

- `query`: the query's vector, `m` numbers.
- `documents`: one vector of `m` numbers per document. A document's index is its position in this list.
- `k`: how many indexes to return at most.

## Output

The indexes of at most `k` documents, best score first.

## Examples

### Example 1

<!-- case: ex1 -->

Document 2 points exactly along the query and scores 1. Documents 1 and 4 both score `0.6`, since `[6, 8]` is `[3, 4]` scaled up and length does not count, so the tie goes to index 1. Documents 0 and 3 score 0 and -1, and `k` leaves them out.

### Example 2

<!-- case: ex2 -->

Documents 0 and 2 are all zeros and are skipped. Document 3 points the opposite way and scores -1, but only two documents have a score, so both come back, which is fewer than `k`.

### Example 3

<!-- case: ex3 -->

A zero query has no direction, so no document has a score.

## Constraints

- `1 <= documents.length <= 10^5`.
- `1 <= m <= 256`, every vector has `m` numbers, and `documents.length * m <= 10^6`.
- `-1000 <= query[j], documents[i][j] <= 1000`.
- `1 <= k <= 1000`.
- No test depends on how a score is rounded: documents that tie in a test have scores that are equal however the arithmetic is ordered, and any two other scores near the cut differ by more than `10^-9`.

## Follow-ups

- Many queries arrive against the same documents. What would you compute once, ahead of time?
- With unit-length vectors stored, cosine similarity is a plain dot product. What does that save, and what can go wrong when a stored vector is not quite unit length?
- At ten million documents a full scan is too slow. What does an approximate index trade away to answer faster, and how would you measure what it misses?
- Several workers each scan a slice of the documents and return their own top `k`. How do you combine their answers, and does the tie-break still hold?

## Hints

### Hint 1

You only ever need to know which of the documents kept so far is the weakest, so that a better one can replace it.

### Hint 2

A min-heap of size `k` keeps the weakest kept document at its root. Push while it holds fewer than `k`, and afterwards replace the root only when a new document beats it.

### Hint 3

"Weakest" has to agree with the tie-break: among equal scores, the higher index is the weaker one. Order the heap by the pair (score, negated index), and sort the `k` survivors best first at the end.
