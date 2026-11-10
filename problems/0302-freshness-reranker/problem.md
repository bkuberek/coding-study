# Freshness Reranker

## Statement

An assistant answers questions about a product that changes every week, so a page from last month can be confidently wrong. Retrieval has already found candidates and scored their relevance. Before the best of them are put into the model's context, a small reranker gives fresher pages and trusted sources more weight and removes copies of the same page. Write `rerankByFreshness`, in four steps.

**Step 1: the pool.** Only the `poolSize` most relevant candidates are reranked: those with the highest `relevance`, with ties going to the lower index. Every other candidate is dropped here, however fresh it is.

**Step 2: the new score.** Each candidate in the pool gets

```text
score = relevance * 0.5^(ageHours / halfLifeHours) * boost
```

The middle factor halves the score for every `halfLifeHours` of age: a candidate one half-life old keeps half its relevance, and one two half-lives old keeps a quarter. `boost` is the factor listed for the candidate's source in `boostFactors`, and 1 for a source that is not listed.

**Step 3: one copy per document.** Candidates with the same canonical id are copies of one document, such as the same page on a mirror. Keep only the copy with the highest score, with ties going to the lower index. Dropping a copy does not let another candidate into the pool.

**Step 4: the order.** Return the ids of the candidates that are left, highest score first, with ties going to the lower index.

## Input

- `candidates`: each candidate as `[id, canonicalId, source]`. Ids are unique; canonical ids repeat across copies. A candidate's index is its position here.
- `relevance`: `relevance[i]` is candidate `i`'s relevance from retrieval.
- `ageHours`: `ageHours[i]` is how old candidate `i` is, in hours.
- `halfLifeHours`: the age at which the score is halved.
- `boostSources`, `boostFactors`: `boostFactors[j]` is the factor for source `boostSources[j]`. A factor below 1 demotes a source.
- `poolSize`: how many candidates are reranked.

## Output

The ids of the kept candidates, best first.

## Examples

### Example 1

<!-- case: ex1 -->

The pool is `a1`, `b1` and `c1`; `d1` is the least relevant and is dropped, although it is new and from a boosted source. The scores are `0.9 * 0.25 = 0.225` for `a1` (two half-lives old), `0.8 * 1.5 = 1.2` for `b1`, and `0.7 * 0.5 = 0.35` for `c1`.

### Example 2

<!-- case: ex2 -->

`n1` and `n2` are copies of `news-7`. The mirror's copy is newer: `0.8` against `0.9 * 0.25 = 0.225`, so it is the one kept. `n3` scores `0.6 * 0.5 = 0.3`.

### Example 3

<!-- case: ex3 -->

The pool of 3 holds `x1`, `x2` and `y1`. `x2` is a copy of `x1` with a lower score and is dropped, which leaves two results: `z1` was never in the pool.

## Constraints

- `0 <= candidates.length <= 10^4`, and `relevance`, `ageHours` have the same length.
- `0 <= relevance[i] <= 1` and `0 <= ageHours[i] <= 10^5`.
- `0 < halfLifeHours <= 10^4`.
- `boostSources.length == boostFactors.length <= 100`, sources are unique, and `0 < boostFactors[j] <= 10`.
- `1 <= poolSize <= 10^4`.
- Ids, canonical ids and sources are 1 to 40 characters long and compared exactly.
- No test depends on how a score is rounded: scores that tie in a test are computed from equal values, and other scores differ by more than `10^-9`.

## Follow-ups

- Relevance from some retrievers is negative. What does multiplying a negative score by a decay below 1 do to an old candidate, and how would you fix it?
- Different questions need different half-lives: a pricing question wants last week's page, a concept question does not care. Where would that choice live?
- After reranking, the context has a budget in tokens. Add each candidate's length and stop before the budget is exceeded. Should a long, excellent candidate be skipped for two shorter ones?
- How would you check, with the metrics of a retrieval evaluation, that the freshness weight actually helped?

## Hints

### Hint 1

Do the steps in the stated order. Choosing the pool by the new score, or removing copies before choosing the pool, gives different answers.

### Hint 2

A map from canonical id to the best copy seen so far handles the copies in one pass over the pool. Compare by (score, index), so a tie keeps the lower index.

### Hint 3

`0.5^(age / halfLife)` is not `exp(-age / halfLife)`: that one is down to 37% after one half-life, not 50%.
