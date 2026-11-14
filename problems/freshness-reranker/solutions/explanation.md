# Freshness Reranker: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| pool-then-rescore | optimal | O(n log n + b) | O(n + b) | default answer |

`n` is the number of candidates and `b` the number of boosted sources.

## Approach: pool-then-rescore (Take the pool by relevance, then rescore and keep the best copy of each document)

### Intuition

A reranker is a second opinion on a short list. Retrieval is good at finding what is about the question and knows nothing about time, so the reranker takes its best few and adjusts them: a page loses half its weight per half-life of age, and a trusted source counts for more. It never reaches back into the long tail, which is why the pool comes first and is chosen by relevance alone. A brand-new page that retrieval ranked 500th is still not about the question.

Copies are a different problem. The same page on two sites fills two places in the context with one piece of information, so only one may stay, and the one to keep is the one the new score prefers: usually the newer copy, or the one from the better source.

The order of the steps is the whole problem. Each pitfall below is a reasonable step done at the wrong time.

### Algorithm

1. Build a lookup from source to boost factor.
2. Sort the candidate indexes by relevance descending, then index ascending, and keep the first `poolSize`.
3. For each candidate in the pool, compute `relevance * 0.5^(ageHours / halfLifeHours) * boost`, with boost 1 for an unlisted source.
4. Keep a map from canonical id to the best (score, index) seen: replace an entry only with a higher score, or an equal score and a lower index.
5. Sort the kept entries by score descending, then index ascending, and return their ids.

### Correctness

Step 2 is the stated pool, since the sort key is the stated order. Step 3 is the stated score. In step 4 each canonical id ends with the copy that is first under (score descending, index ascending) among its pooled copies, which is the stated choice, and copies outside the pool were never considered, so no candidate enters the pool late. Step 5 is the stated order over the survivors.

### Complexity

- Time: O(n log n + b) — the sort of the candidates for the pool dominates, and the lookup takes `O(b)` to build.
- Space: O(n + b) — the sorted indexes, the map of copies and the lookup.

### Trade-offs

Selecting the pool with a heap costs `O(n log p)` for a pool of `p` instead of sorting all `n`, which matters for long candidate lists and not for the hundreds a reranker usually sees.

Multiplying the factors keeps each one meaningful on its own: a boost of 1.5 means 50% more, whatever the age. Adding a boost would let it swamp a small relevance score and barely move a large one.

A half-life is easy to reason about and to tune: after one, half the weight is left. Exponential decay written as `exp(-age / tau)` is the same curve with `tau = halfLife / ln 2`, so a parameter named "half-life" plugged in as `tau` decays too fast.

### Pitfalls and edge cases

- **The wrong decay.** `exp(-age / halfLife)` keeps 37% after one half-life instead of 50% (`h1`, `h15`).
- **Choosing the pool after rescoring.** It lets a fresh but barely relevant candidate in (`ex1`, `h2`, `h13`).
- **Removing copies before choosing the pool.** It frees places in the pool for candidates that were not in it (`ex3`, `h4`), and it keeps the more relevant copy instead of the one with the better new score (`ex2`, `h3`, `h12`).
- **Keeping the first copy.** The copy to keep has the highest new score, not the highest relevance or the earliest place (`ex2`, `h3`, `h12`).
- **Tie-breaks.** Three of them, all to the lower index: the last place in the pool (`h6`), between copies (`h7`) and in the result (`h7`).
- **Boosts.** They multiply, a factor below 1 demotes, and an unlisted source has a factor of 1, not 0 (`h5`, `h12`, `h14`).
- **Returning canonical ids.** The result holds the kept copies' own ids (`ex2`, `h12`).
- **Small and empty.** A score of 0 is still a result (`h11`), a pool larger than the list takes everything (`h8`), and no candidates give an empty result (`h9`).

### Language notes

- Python: `sorted(range(n), key=lambda i: (-relevance[i], i))` is the pool with its tie-break, and the map holds `(-score, index)` tuples, so `<` compares by score and then index in one step. `0.5 ** x` is the decay.
- TypeScript: one comparator, `b.score - a.score || a.index - b.index`, serves both the copies and the final sort. `0.5 ** x` and `Math.pow(0.5, x)` are the same.
