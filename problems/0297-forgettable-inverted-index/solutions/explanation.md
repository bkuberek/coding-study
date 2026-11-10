# Forgettable Inverted Index: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| incremental-postings | optimal | O(t) per add, update or forget; O(q + p + m log m) per search; O(q + p) per score | O(s) | default answer |

`t` is the number of tokens of the documents a change touches (the old and the new version for an update), `q` the number of query tokens, `p` the number of postings of the query's tokens, `m` the number of documents that match, and `s` the number of tokens in the index.

## Approach: incremental-postings (Keep the postings and the totals current on every change)

### Intuition

BM25 reads five numbers: `tf` and `|d|` belong to one document, and `N`, `avgdl` and `df` belong to the whole index. An index that only ever grows can let the last three drift upwards and still rank sensibly. One that forgets cannot: a forgotten note that still counts in `df` makes every remaining holder of its tokens look more common than it is, and one that still counts in `N` and the total length shifts every score. Worse, a posting left behind lets the note be found again, which is exactly what forgetting promised would not happen.

So treat the statistics as part of the index, and change them in the same place that changes the postings. Each change is a pair of opposite operations: indexing a document adds its postings, its length and one to `N`; unindexing it takes exactly those away. An update is unindex then index. If the two operations mirror each other, no sequence of changes can leave a trace.

### Algorithm

1. Keep `postings`, a map from each token to a map from document id to how many times the document holds it; `terms`, each document's distinct tokens; `lengths`, each document's length; and `totalLength`, their sum. `N` is the size of `lengths`.
2. Index a document: count its tokens, write each count into the token's posting map, store its distinct tokens and length, and add its length to `totalLength`.
3. Unindex a document: for each of its stored distinct tokens, delete the document from the token's posting map, and delete the map when it is left empty. Then subtract its length and drop its entries from `terms` and `lengths`.
4. `add` indexes unless the id is present; `update` unindexes and indexes when it is; `forget` unindexes when it is.
5. To score a query: when `totalLength` is 0, nothing can match. Otherwise compute `avgdl = totalLength / N` and, for each distinct query token, `df` as the size of its posting map and `idf` from it; then add the token's term to the score of each document in the map.
6. `search` sorts the scored documents by score descending, then by id, and keeps the first `topN`. `score` reads one document's entry, or 0.

### Correctness

Invariant: after every call, `postings`, `terms`, `lengths` and `totalLength` are exactly what indexing the current documents, in any order, from an empty index would produce. It holds for the empty index. Indexing adds one document's contributions, and unindexing removes exactly the contributions that indexing it added, since `terms` records which posting maps it wrote and `lengths` how much it added to the total. An empty posting map is deleted, so the set of tokens with postings is exactly the set of tokens some document holds. `add`, `update` and `forget` change nothing when they return `false`.

Given the invariant, the size of a token's posting map is its `df`, each entry is a `tf`, `lengths` holds every `|d|`, and `N` and `avgdl` are the current ones, so step 5 computes the stated formula over the current documents. A document gets a score exactly when it holds a query token, so `search` returns only those, in the stated order. When `totalLength` is 0, no document holds a token, so returning no scores is correct and nothing divides by zero; otherwise `N >= 1` and `avgdl > 0`.

### Complexity

- Time: O(t) per add, update or forget; O(q + p + m log m) per search; O(q + p) per score — a change visits each token of the document once (and the old version's distinct tokens for an update); a query visits the posting maps of its distinct tokens and sorts the matches.
- Space: O(s) — every token of every document is counted in at most one posting entry, plus one length and one list of distinct tokens per document.

### Trade-offs

- Recomputing `N`, `avgdl` and every `df` from the documents on each search is simpler and impossible to get out of sync, but each search then costs O(s). For a handful of notes it is a fine first answer; say why you would move to running totals.
- A tombstone makes `forget` O(1): mark the id gone and skip it in `search`. But `df`, `N` and the total length keep counting it until a compaction rewrites the postings, so scores are wrong in between, and a bug in the skip brings the note back. For a memory that a user asked to forget, eager removal is the honest default.
- `score` reuses the search's scoring loop, so it costs the postings of the query rather than O(q). Computing one document's score directly needs its `tf` per token, which the posting maps give in O(1) each; the shared loop is simpler and keeps one formula.

### Pitfalls and edge cases

- **Leaving postings behind on forget.** The document is found again by its old words (`ex1`, `h1`).
- **Leaving postings behind on update.** An update replaces every token, so the old ones must go (`ex2`, `h3`).
- **Statistics that only grow.** Forgetting must lower `N` and the total length, and every `df` the document added to (`ex3`, `h2`, `h10`). An update changes the length and the `df` values too (`h3`, `h9`).
- **`df` counted per occurrence.** A document that says `z` three times adds one to `df`, and takes one away when it goes (`h10`).
- **Empty posting maps.** If a map is kept after its last holder goes, its size is still right, but a map that keeps the document with a count of 0 is not (`h10`).
- **Refused calls that change something.** Adding an id that is there, or updating or forgetting one that is not, returns `false` and changes nothing (`h4`, `ex2`).
- **Re-adding a forgotten id.** It is a new document with only its new tokens (`h5`).
- **Empty documents.** They count in `N` and in `avgdl` but match nothing, and an index of only empty documents must not divide by zero (`h6`, `h9`).
- **A repeated query token.** It counts once (`h8`); `tf` counts repeats in the document.
- **Ties.** Equal scores go to the smaller id in string order, so `doc10` comes before `doc2` (`h7`, `h12`).
- **Hard-coded parameters.** `k1` and `b` come from the constructor (`h12`, `h13`).

### Language notes

- Python: `Counter(tokens)` counts a document in one call. `dict.fromkeys(query)` removes repeated tokens and keeps their order, where a `set` would add the terms in an order that changes from run to run, because string hashes are seeded per process. `sorted(scores, key=lambda d: (-scores[d], d))` is the whole tie-break.
- TypeScript: a `Set` keeps insertion order, so `new Set(query)` is safe to sum over. Compare ids with `<` and `>` rather than `localeCompare`, which orders by locale. `Math.log` is the natural logarithm.
