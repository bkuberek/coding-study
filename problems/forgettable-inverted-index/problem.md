# Forgettable Inverted Index

## Statement

An assistant keeps short notes about a user, its memories, and before it answers it looks up the few that match the question by keyword. Memories change: a user moves, and the note about their city is rewritten; a user asks the assistant to forget something, and the note must go. A forgotten memory must never come back, not through its old words and not through the statistics it left behind, because the ranking of every other memory depends on them.

Implement `ForgettableIndex`, a keyword index that ranks with BM25 computed from what it holds **now**:

- `ForgettableIndex(k1, b)`: an empty index with these BM25 parameters.
- `add(docId, tokens)`: indexes a new document. Returns `true`, or `false` and changes nothing when `docId` is already in the index.
- `update(docId, tokens)`: replaces every token of the document `docId`. Returns `true`, or `false` and changes nothing when `docId` is not in the index.
- `forget(docId)`: removes the document. Returns `true`, or `false` when it is not in the index. A forgotten `docId` can be added again later, as a new document.
- `search(query, topN)`: the ids of the documents that hold at least one query token, best score first, with equal scores going to the smaller `docId` in plain string order, and at most `topN` of them. **A document with no query token is never returned.**
- `score(query, docId)`: the BM25 score of `docId` for `query`, or `0` when it holds no query token or is not in the index.

The score of a document `d` is the sum, over the distinct tokens `t` of the query that `d` holds, of

```text
idf(t) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * |d| / avgdl))

idf(t) = ln(1 + (N - df(t) + 0.5) / (df(t) + 0.5))
```

where every statistic describes the index at the moment of the call: `N` is the number of documents in it, `avgdl` the mean length of those `N` documents in tokens, `df(t)` the number of them that hold `t`, `tf` the number of times `t` occurs in `d`, `|d|` the length of `d`, and `ln` the natural logarithm. A token repeated in the query counts once.

## Input

- `k1`, `b`: the BM25 parameters. `k1` controls how fast a repeated token stops adding score, and `b` how much a long document is held back.
- `docId`: the id of a document.
- `tokens`: the document's tokens, already lowercased and split. Tokens are compared exactly. A document may have no tokens at all; it still counts in `N` and in `avgdl`.
- `query`: the query's tokens, in the same form. It may be empty.
- `topN`: how many ids `search` returns at most.

Each test is a sequence of calls: the constructor first, then the other calls in order.

## Output

One result per call: `null` for the constructor, a boolean for `add`, `update` and `forget`, a list of ids for `search`, and a number for `score`. Scores are compared with a tolerance of `10^-6`, relative to their size.

## Examples

### Example 1

<!-- case: ex1 -->

`trip` and `pet` both say `lisbon` once, and `trip` is the shorter, so it ranks first. Once `trip` is forgotten, no query finds it, and forgetting it a second time finds nothing.

### Example 2

<!-- case: ex2 -->

The update replaces every token of `home`, so `porto` no longer finds it and `faro` does. `gym` is not in the index, so updating it changes nothing.

### Example 3

<!-- case: ex3 -->

`b` itself does not change, but forgetting `c` changes the statistics: `N` drops from 3 to 2, `avgdl` from `7/3` to `3/2`, and `tea` is now in every document. So the score of `b` for `tea` drops from about `0.613` to about `0.211`.

## Constraints

- At most 1000 calls per test.
- `0 < k1 <= 10` and `0 <= b <= 1`.
- Ids and tokens are 1 to 20 lowercase letters or digits.
- A document has at most 200 tokens, and a query at most 20.
- `1 <= topN <= 100`.
- No case depends on the order in which the parts of one score are added: two documents either have exactly the same score, or scores far enough apart for any order of addition.

## Follow-ups

- Forgetting by tombstone, a flag that marks a document as gone, is cheaper than taking it out of every posting list. What does `search` then have to skip, and which statistics stay wrong until the postings are compacted?
- A memory store holds a million notes, and a search reads only a few posting lists. Which statistics would you keep as running totals, and which would you compute on demand?
- The user asks what the assistant still remembers about a topic after forgetting some notes. How would you prove to them that a forgotten note left nothing behind?

## Hints

### Hint 1

Keep a posting list per token, from each document to its count, plus a running total of the lengths. Every statistic in the formula then comes from them.

### Hint 2

To forget a document you need to know which posting lists hold it. Remember each document's distinct tokens when you add it.

### Hint 3

An update is a forget followed by an add, under the same id.
