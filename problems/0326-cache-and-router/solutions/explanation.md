# Cache and Router: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| entry-table-pipeline | optimal | O(1) per exact lookup, O(n m) per semantic lookup | O(n m) | default answer; every level adds one stage to the same table of entries |

Here `n` is the number of entries and `m` the length of an embedding.

## How the design grows level by level

| Level | Change | What the gateway adds |
|-------|--------|-----------------------|
| 1 | The exact cache | A normal form of the prompt as the key of a map, and three counters |
| 2 | The semantic cache | An embedding, a source and a version on each entry; an integer cosine; a scan for the nearest entry |
| 3 | The router | A ladder of tiers, a start by label, a move up by length, and one escalation after a failed check |
| 4 | The books | A price per call, a prefix memory per tier, a baseline per request, and a report |

The early choice that matters is to keep **one** table of entries for both caches. An entry has a key, and may also have an embedding and a source. Then the exact lookup is a map access, the semantic lookup is a scan over the same table, a source version retires entries of both kinds at once, and level 4 stores what it learned with a single call.

## Approach: entry-table-pipeline (One table of entries, an exact key lookup, then a scan for the nearest embedding)

### Intuition

A request meets three questions in turn, from the cheapest to the most expensive: did we answer exactly this before (a map access), did we answer something close enough (a scan of the embeddings), and if not, which model should we pay for (a ladder of tiers). Each answer that comes back from a model is written into the table, so the next question may be answered for free. The books are kept by one small function that bills one call, and every call goes through it, valid or not.

### Algorithm

1. Keep `entries`, a map from the normal form of the prompt to the entry (response, optional embedding, source, version, and the order of storing), a counter for that order, a map from each source to its current version, and the counters `exactHits`, `semanticHits` and `misses`.
2. `key`: trim spaces, tabs and newlines, replace each inner run by one space, and lowercase `A` to `Z`.
3. `put` and `putSemantic`: compute the key; if it is stored, return `false`; otherwise store the entry with the current version of its source and return `true`.
4. `lookup`: a map access, one counter.
5. `lookupSemantic`: try the map; otherwise scan the entries with an embedding. For each, compute `dot`, `nq`, `nd`; skip it when `dot <= 0` or a vector is zero; compute `permille = isqrt(10^6 * dot^2 // (nq * nd))`; skip it below the threshold; keep the entry with the greater `dot^2 / nd` (compared by cross-multiplication), and on equal values the one stored first.
6. `setSourceVersion`: store the version, then delete the entries of that source whose version differs, and count them.
7. `route`: start at the tier of the label (the last tier for an unknown label) and take the first tier from there with `promptTokens <= limit`.
8. `answer`: route; if the answer of that tier is valid, stop; otherwise, if a higher tier exists, take the answer of the next tier as the result. The status follows from which of the calls was valid.
9. `handle`: count the tokens of the prompt as sent; look up; on a miss run `answer`, bill each call that was made, and store the result when it is `ok` or `escalated`. Compute the baseline from the prompt tokens and the last answer. Add to the totals.
10. `report`: the totals, the cache counters, and one row per tier.

### Correctness

The key is a function of the prompt that is the same for all prompts the statement calls equal, and different for the others, since the three steps remove only what the statement says is irrelevant. `put` stores only a new key, so the first response stays.

The permille is exact. `floor(sqrt(x))` equals `isqrt(floor(x))` for `x >= 0`, so taking the integer division before the root loses nothing, and `isqrt` is exact for integers. The comparison `permille >= threshold` is then the statement's test that the cosine is at least `threshold / 1000`: for a whole `threshold`, `floor(1000 * cosine) >= threshold` holds exactly when `1000 * cosine >= threshold`. Two entries compare by `dot^2 / nd` because `nq` is the same for both and, with both dot products positive, squaring keeps the order.

A version is attached to an entry when it is stored and the table is cleaned at once when a version is set, so the table never holds an entry of an older version of its source, and an entry stored afterwards carries the version that is current. No other lookup can see a stale entry.

The router only moves up. `route` starts at a tier given by the label and moves up to the first tier that fits; as the limits do not decrease, every tier above also fits, so the escalation to `tier + 1` never needs another length check. The status table of the statement covers each outcome of the two checks.

The bill of a request is the sum over the calls that were made, and a call is billed by one function, so a call whose answer was not valid is paid for like any other. The prefix is added to the memory of a tier after the cost is computed, so the first call pays in full and the second gets the cached price. The baseline depends on the request alone, so it is the same whatever the cache and the router did.

### Complexity

- Time: O(1) per exact lookup, O(n m) per semantic lookup — a map access with a key of bounded length for the exact path; the semantic path computes one dot product of `m` numbers for each of the `n` entries. Routing and billing take time proportional to the number of tiers, at most 4.
- Space: O(n m) — the table holds `n` entries with an embedding of `m` numbers each.

### Trade-offs

- A scan is fine for the sizes here and for a few thousand entries. A cache of millions needs an approximate nearest-neighbour index, which trades a small chance of missing the closest entry for a lookup that does not touch every entry; with it, the tie-break "stored first" is no longer free and has to be built into the index.
- The semantic path can be wrong, and the exact path cannot. Trying the exact key first is both cheaper and safer, and it is why a semantic hit is only ever reported for a key that is not stored.
- The threshold is a single number for all questions. A higher one for questions where a wrong answer costs more (money, health, law), or a check that the cached answer still fits the new question, would lose some savings and avoid some false hits. How much depends on the data, which is why the rate of false hits has to be measured and not assumed.
- Retiring entries by source version is simple and strict: everything built from a changed source goes, even entries that did not depend on the change. Finer tracking (the part of the source an answer used) keeps more, at the price of recording it.
- Escalating once bounds the cost of a failed cheap call: at most two calls per request. The report shows when that is not enough to beat going straight to the large tier, so the router's label and the check on answers are worth measuring too.
- A cached-prefix price turns a long, repeated instruction from a cost per request into a cost per tier. Its value depends on how often the same prefix returns before it is forgotten, which this problem does not model.

### Pitfalls and edge cases

- Level 1: the key keeps punctuation, so a question with and without its question mark are different keys. Only spaces, tabs and newlines count as whitespace and only `A` to `Z` change case. `put` on a stored key returns `false` and keeps the first response, whatever the second says. The percent rounds down (2 of 3 is 66), and is 0 with no lookup. `entries` counts keys, not calls.
- Level 2: the exact key is tried first, and the embedding sent with an exact hit is ignored. An entry stored by `put` is found by `lookup` and `lookupSemantic` through its key and never by similarity. A zero vector, a zero dot product and a negative cosine never match. The threshold test must be exact: with decimals, `0.5` can come out as `0.4999999999999999` and miss at a threshold of 500. Rank by the exact cosine and not by the rounded permille: two entries can share a permille and differ, and only the exact value tells which is closer. On equal cosines the entry stored first wins, not the first by name. A hit reports the stored key (the normal form), not the query. `setSourceVersion` removes entries of a *different* version, so going back also retires them, and the first call for a source retires everything stored before any version was set (they have version 0). Setting the same version again removes nothing.
- Level 3: a prompt of exactly `limit` tokens fits. An unknown label starts at the last tier. The label never lowers the tier: a hard question with a tiny prompt stays on the last tier. Escalation happens once, from the tier that was routed (after the length move), to the next tier up, whatever the third tier would have answered. The marker test is a plain substring test: `ERROR` is found inside `TERRORS`, and `error` is not found. A blank answer is invalid even with no markers. An `invalid` result carries the answer of the last call, not the first.
- Level 4: the tokens are those of the prompt as sent, so extra spaces count even though the key ignores them. The reused part of a prefix is capped by the prompt's tokens. A prefix id that was never defined, or is empty, is no prefix at all (and does not break the books). A prefix is warm per tier: a request that escalates to a tier that has never seen the prefix pays full price there. An invalid answer is billed and not stored, so asking again calls the model again. A too-long request has a baseline of 0. The percent is rounded toward negative infinity, so -38.2 becomes -39, and the plan can cost more than the baseline when the cheap call fails.

### Language notes

- Python: `//` on non-negative integers is exact, and on a negative numerator it rounds down, which is the rule of the report. `math.isqrt` is the exact integer square root. `str.split()` splits on more characters than the statement allows, which the inputs never contain, but a regular expression on `[ \t\n]+` says what it means. A dictionary keeps the order of insertion, but the order of storing is kept in the entry so that deleting does not matter.
- TypeScript: numbers are doubles, and everything here stays below 2^53 - 1, so products and sums are exact. `Math.floor(a / b)` is exact for the sizes here but a remainder-based division says it without relying on the size. `%` returns a negative result for a negative left side, so the floor division adds the denominator back. There is no integer square root: `Math.sqrt` rounded down and then corrected by one step each way gives the exact value. `Map` keeps the order of insertion, but the order is kept in the entry as well. `String.prototype.toLowerCase` on ASCII text is the same as the statement's rule.

## Further reading

- L. Chen, M. Zaharia and J. Zou, "FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance", arXiv:2305.05176, 2023: three families of strategies for lowering the cost of calling language models (prompt adaptation, model approximation and cascades of models), the last of which is the escalation of level 3.
- I. Ong et al., "RouteLLM: Learning to Route LLMs with Preference Data", arXiv:2406.18665, 2024: routers that choose between a stronger and a weaker model for each query, trained from preference data.
- D. Ding et al., "Hybrid LLM: Cost-Efficient and Quality-Aware Query Routing", arXiv:2404.14618, 2024: a router that sends a query to a small or a large model by its predicted difficulty and the quality wanted.
- W. Gill et al., "MeanCache: User-Centric Semantic Caching for LLM Web Services", 2025 IEEE International Parallel and Distributed Processing Symposium (IPDPS), pp. 1298-1310, doi:10.1109/IPDPS64566.2025.00117 (arXiv:2403.02694): a semantic cache and the hit and miss errors it makes.
- I. Gim et al., "Prompt Cache: Modular Attention Reuse for Low-Latency Inference", arXiv:2311.04934, 2023: reusing the work done on text that many prompts share, such as system messages and templates, the idea behind the cached-prefix price of level 4.
- C. D. Manning, P. Raghavan and H. Schütze, "Introduction to Information Retrieval", Cambridge University Press, 2008, doi:10.1017/CBO9780511809071: chapter 6, "Scoring, term weighting, and the vector space model", for documents and queries as vectors.
- [Cosine similarity](https://en.wikipedia.org/wiki/Cosine_similarity): the measure of level 2 for two non-zero vectors.
- [Python `math.isqrt`](https://docs.python.org/3.12/library/math.html#math.isqrt): the integer square root, "the floor of the exact square root".
