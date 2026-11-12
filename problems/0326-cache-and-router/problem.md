# Cache and Router

## Statement

Every call to a large language model has a price, and the price grows with the number of **tokens** (the pieces of text a model reads and writes) that go in and come out. A product that sends every question to the biggest model pays the most it can. Two plain ideas cut the bill without changing what the user sees:

- **A cache.** If the same question was already answered, hand back the saved answer and make no call at all. A cache is a notebook you check before doing the expensive thing.
- **A router.** If a small, cheap model can answer a question well, do not use the big, expensive one. When the small model's answer turns out to be unusable, try the next model up, once.

Build `CacheRouter`, the small gateway that sits in front of the models and does both, and then tells you what it saved. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

The gateway never calls a model. What each model would answer, and which vectors stand for the questions, arrive as data with each request, so every result is exact and the same in every language. The prices are made up and are counted in *micro-credits*, a unit that exists only in this problem.

Aim to finish in 150 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 70, level 3 by 100 and level 4 by 140, keeping the last minutes for a final run.

## Input

- `CacheRouter()`: creates an empty gateway.
- A **prompt** is a question as the user typed it: 1 to 200 characters, each a space, a tab, a newline or a visible ASCII character (`!` to `~`), with at least one visible character.
- A **response** or an **answer** is text: 0 to 100 characters of the same kind. A response that is stored has at least one character.
- A **source**, a **label** and a **prefix id** are 1 to 20 characters from `a` to `z`, `0` to `9` and `_` (a prefix id may also be empty, which means "none"). They are compared exactly as given.
- Text is compared by the numeric value of its characters. Numbers in lists of text are written in decimal.
- Each level's section describes the methods it adds and their parameters.

## Output

Methods answer with a flag, a number, a piece of text or a list of text, as each section says. A method that only changes the gateway's settings returns nothing.

## Level 1: An exact cache

The simplest cache keeps the answer under the question and returns it when the same question comes back. The catch is that people never type the same question the same way twice: capital letters, extra spaces, a stray line break. So the cache does not use the raw text as the key. It uses a *normal form* of it.

- `key(prompt)`: the normal form of the prompt. Take the prompt, remove the spaces, tabs and newlines at both ends, replace each run of spaces, tabs and newlines inside it by one space, and turn each letter `A` to `Z` into `a` to `z`. Nothing else changes: a question mark, a comma and a digit all stay.
- `put(prompt, response)`: stores the response under the key of the prompt. It returns `true` when the key is new. It returns `false` when the key is already stored, and then nothing changes: the response that was stored first stays.
- `lookup(prompt)`: asks for the response stored under the key of the prompt. It returns `["hit", response]`, or `["miss"]` when nothing is stored. It counts as one hit or one miss.
- `stats()`: `[hits, misses, entries, hitPercent]`: the hits and the misses counted so far, the number of entries stored, and the share of lookups that hit as a whole percent rounded **down** (`floor(100 * hits / (hits + misses))`, and 0 when there has been no lookup).

An *entry* is one stored key with its response.

### Example 1

<!-- case: ex1 -->

The key of `"  What IS\tthe   capital of France?\n"` is the lowercase text with single spaces and no outer whitespace, and its question mark stays. `"  what is THE capital of france?  "` and `"WHAT IS THE CAPITAL OF FRANCE?"` have the same key as the stored question, so they hit; Spain's question has another key and misses. The second `put` has an existing key, so it returns `false` and `"Paris"` stays. Two hits and one miss are 66.67%, which is written `66`.

### Example 2

<!-- case: ex2 -->

A new gateway has nothing to report: `[0, 0, 0, 0]`. The question mark is part of the key, so the stored question and the same words without it are different keys, and the first lookup misses. Capitals, a doubled space and a line break do not change the key, so the second lookup hits. One hit and one miss are 50%.

## Level 2: A semantic cache

People also ask the same thing in different words: "how do I get a refund?" and "how can I be refunded?". An exact key cannot see it. A **semantic cache** compares *meaning* instead of text. Each question has an **embedding**: a short list of numbers that a model computed so that questions with similar meaning point in similar directions. Here the embeddings are given. The measure is the **cosine similarity** of two embeddings: the cosine of the angle between them, `(a . b) / (|a| * |b|)`. It is 1 for the same direction, 0 for directions at a right angle and negative for opposite directions, and the length of a vector does not matter, only its direction.

To keep every result exact, the similarity is written as an integer in **permille** (thousandths): the largest whole `p` such that `p / 1000` is at most the cosine, which is `floor(1000 * cosine)`. It is computed with integers (the statement below shows how), never with decimals.

- `putSemantic(prompt, embedding, response, source)`: like `put`, with an embedding and a `source`: the name of the document or the data the response was built from. The identity is still the key of the prompt: it returns `true` when the key is new and `false` when it is stored (by `put` or by `putSemantic`), and then nothing changes.
- `lookupSemantic(prompt, embedding, threshold)`: finds a response for a prompt in this order, and counts one hit or one miss.
  1. If the key of the prompt is stored, it is an **exact** hit, and the answer is `["hit", "exact", response]`. The embedding is not looked at.
  2. Otherwise, take the stored entries that have an embedding and whose similarity with `embedding` is **at least** `threshold` permille. The best one is a **semantic** hit: `["hit", "semantic", response, key, permille]`, where `key` is the key the entry is stored under and `permille` is its similarity, written as text.
  3. Otherwise `["miss"]`.
- `setSourceVersion(source, version)`: says that the source is now at this version, and returns how many entries it removed.

**Which entry is best.** The one with the greatest cosine similarity. Compare the exact values, not the rounded permille. When two entries have exactly the same cosine, the one that was **stored first** wins. (The order of storing is the order in which `put` and `putSemantic` returned `true`.)

**No direction, no similarity.** An entry stored by `put` has no embedding and is never a semantic match. A vector of only zeros has no direction: it is never a match, and a query that is a zero vector matches nothing. A similarity that is zero or negative never matches either, whatever the threshold (the threshold is at least 1).

**Exact arithmetic.** For a query `q` and an entry `d`, let `dot = q . d`, `nq = q . q` and `nd = d . d`. When `dot > 0`, `permille = floor(sqrt(10^6 * dot^2 / (nq * nd)))`, which is `isqrt((10^6 * dot^2) // (nq * nd))`, where `//` is whole-number division that rounds down and `isqrt(x)` is the largest whole number whose square is at most `x`. Comparing two entries `a` and `b` for the same query needs no division: `a` is closer when `dot_a^2 * nd_b > dot_b^2 * nd_a`.

**Sources and versions.** A response is only as good as the data behind it. When a policy changes, the answers built from the old policy are wrong, and the cache must stop serving them. Each source has a current version, `0` until it is set. An entry stores its source and the *current version of that source at the moment it was stored* (an entry stored by `put` has no source and no version). `setSourceVersion(source, version)` first makes `version` the current version of the source, and then removes every entry whose source is that one and whose stored version is **different** (older or newer, so that going back to an older version also retires the entries of the version you left). It returns the number of entries removed. Entries of other sources, and entries without a source, stay.

**The risk of a false hit.** A semantic hit is a guess. Two questions can be close in meaning-space and still need different answers: "how do I get a refund?" and "how do I cancel my order?" are about the same order and the same words, and an embedding may put them very near each other. A hit on the wrong one gives the user a confident, wrong answer, and nothing in the cache will show it. The threshold sets the trade: a low one saves more calls and makes more false hits, a high one is safe and saves little. An exact hit has no such risk, which is why it is tried first. The second example below shows a false hit.

### Example 1

<!-- case: ex3 -->

The new question `"How can I be refunded"` has no exact key, but its embedding is close to the refund question's: its similarity is 990 permille, above the threshold 950, so it is a semantic hit and carries the stored key. With the threshold 991 the same lookup misses. `"HOW do I get a REFUND?"` has the stored key once normalized, so it is an exact hit even though the embedding sent with it points elsewhere. `"Where is my parcel"` is nowhere near either entry. Two hits and two misses are 50%.

### Example 2

<!-- case: ex4 -->

The cancel question has an embedding at 932 permille from the refund question's. With the threshold 900 the cache answers it with the **refund** answer: a false hit. With 950 it misses, and the cache is told the real answer. After that, a paraphrase of the cancel question matches the cancel entry (998), and a paraphrase of the refund question still matches the refund entry (990), because each is the nearest. `setSourceVersion("policy", 2)` removes both entries (they were stored at version 0), and the paraphrase misses afterwards.

## Level 3: Routing to a tier

Models come in sizes. A small one is cheap and quick, and is often enough for a simple question. A large one is better and many times dearer. A **router** picks one for each question. A **tier** is one model size; tiers are numbered from `0`, the cheapest, upward, and there are 2 to 4 of them.

- `configureRouting(tierLimits, labels, labelTiers, invalidMarkers)`: sets the router once, before any other method of this level and of the next. `tierLimits[t]` is the most prompt tokens tier `t` accepts (a longer prompt does not fit its window). The limits do not decrease from one tier to the next. `labels[i]` is a difficulty label that a classifier gave the question, and `labelTiers[i]` the tier where questions with that label start. `invalidMarkers` are pieces of text that mark an answer as unusable.
- `route(label, promptTokens)`: the tier for a question. Start at the tier of the label, or at the **highest tier** when the label is not in `labels` (when unsure, do not risk the quality). If the prompt does not fit that tier, move up to the first tier whose limit is at least `promptTokens`. A prompt that fits a tier fits it exactly when `promptTokens <= limit`. When no tier fits, the answer is `-1`.
- `answer(label, promptTokens, answers)`: runs the question through the tiers and returns `[status, calls, text]`. `answers[t]` is what tier `t` would answer, for every tier.

**The validity check.** An answer is **valid** unless it is empty after removing the spaces, tabs and newlines at both ends, or it **contains** one of the markers as a piece of text, compared exactly (capitals matter, and the marker can sit inside a longer word).

**Escalation.** The question goes to the tier given by `route`. If its answer is valid, that is the result. If not, and a higher tier exists, the question escalates **once**, to the next tier up; its answer is the result, valid or not. There is no second escalation. The `status` and `calls` are:

| Case | `status` | `calls` | `text` |
|------|----------|---------|--------|
| no tier fits | `too_long` | empty | empty |
| the first call is valid | `ok` | the tier, such as `1` | its answer |
| the first is not valid and the next tier's is | `escalated` | such as `1>2` | the next tier's answer |
| the last call made is not valid | `invalid` | one tier, or two as `0>1` | the last call's answer |

An `invalid` result is returned to the caller as it is; whether to show it is not this method's business. It is still a result of the calls that were made, and the next level pays for each call.

### Example 1

<!-- case: ex5 -->

The limits are 20, 50 and 200 tokens. A simple question of 12 tokens starts at tier 0 and fits. At 21 tokens it does not fit tier 0 and moves up to tier 1. A standard question starts at tier 1, a hard one at tier 2, and 201 tokens fit nowhere. In the last two calls, the first answer of tier 0 is valid, and then `"I cannot say"` contains a marker, so the question escalates to tier 1, whose answer is valid.

### Example 2

<!-- case: ex6 -->

A hard question starts at the last tier. Its answer contains `ERROR`, there is no tier above, and the result is `invalid` after one call. A blank answer (`"  \n"`) is invalid, and so is `"ERROR"` from tier 1: the question escalated once and stops, even though tier 2 would have answered `"fine"`. The fifth call asks for the tier of a label that is not known, and the answer is the highest tier.

## Level 4: What it costs and what it saves

The gateway now has everything needed to handle a request: look in the cache, otherwise route, call, and remember. This level puts it together and keeps the books.

**Prices.** Every price is a whole number of micro-credits **per token**.

- `setPrices(inputPrices, outputPrices, cachedPrices)`: sets, once and after `configureRouting`, the price of every tier: what one input token costs, what one output token costs, and what one input token costs when it belongs to a reused prompt prefix. `cachedPrices[t]` is at most `inputPrices[t]`.
- `definePrefix(prefixId, tokens)`: says that prompts which use the prefix `prefixId` start with a shared part of this many tokens, such as a long instruction that every request repeats. Defining it again replaces the length.
- `setThreshold(permille)`: the similarity threshold of `handle`. It is 1000 until it is set.
- `handle(prompt, embedding, label, source, answers, prefixId)`: handles one request and returns `[status, calls, text, cost, baseline]`. `answers[t]` is what tier `t` would answer. `prefixId` may be empty.
- `report()`: the books so far.

**Tokens.** The tokens of a text are its number of characters divided by 4, rounded up: `ceil(length / 4)`, so an empty text has none. The tokens of a prompt are those of the prompt **as sent**, with its capitals and spaces, not those of its key.

**What `handle` does.**

1. Look the prompt up as `lookupSemantic(prompt, embedding, threshold)` does, with the threshold of `setThreshold`. On a hit, the `status` is `exact` or `semantic`, `calls` is empty, `text` is the stored response and `cost` is `0`.
2. On a miss, run `answer(label, promptTokens, answers)`. The `status`, `calls` and `text` are its. Every call that was made is paid for, **including a call whose answer was not valid**.
3. When the status is `ok` or `escalated`, store the answer as `putSemantic(prompt, embedding, text, source)`. An `invalid` answer is not stored: caching a bad answer would serve it again and again. A `too_long` request makes no call and costs `0`.

**The cost of a call** to tier `t` with a prompt of `n` tokens and an answer of `m` tokens is

```text
cost = (n - c) * input[t] + c * cached[t] + m * output[t]
```

where `c` is the reused part of the prefix: `min(prefixTokens, n)` when `prefixId` has been defined and the prefix is **warm** at tier `t`, and `0` otherwise. A prefix is warm at a tier once **a call to that tier has been made with it** (the first call pays in full and warms it; a later call at the same tier gets the cached price; another tier is cold until it is called itself). An empty or never defined prefix id is no prefix. The cost of a request is the sum of the costs of its calls.

**The baseline** is what the same request would have cost if every request went to the largest tier with no cache and no prefix discount: `n * input[last] + m * output[last]`, with `m` the tokens of `answers[last]`. It is `0` for a `too_long` request, which the largest tier could not take either. The baseline is counted for every request, hit or not.

**The report.** `report()` returns these rows, as text, in this order:

- `["total", requests, cost, baseline, savings, savingsPercent]`: the number of `handle` calls, the sum of their costs, the sum of their baselines, `savings = baseline - cost` (negative when the plan cost more), and `savingsPercent = floor(100 * savings / baseline)` rounded toward negative infinity, `0` when the baseline is `0`.
- `["cache", exactHits, semanticHits, misses]`: the counters of every lookup so far.
- one row `["tier", t, calls, fullInputTokens, cachedInputTokens, outputTokens, cost]` for each tier, from tier 0, with the calls made to the tier and the tokens and micro-credits billed there.

### Example 1

<!-- case: ex7 -->

Prices are 2, 6 and 20 per input token, 4, 12 and 40 per output token, and 1, 2 and 5 for a cached input token. The first request is 9 tokens, goes to tier 0 and gets a 7-token answer: `9 * 2 + 7 * 4 = 46`. The prefix `sys` is now warm at tier 0. The second is 7 tokens and `sys` has 8, so the reused part is 7: `0 * 2 + 7 * 1 + 5 * 4 = 27`. The next two requests hit, an exact one (the capitals do not matter) and a semantic one (990 permille is at least the threshold of 900), and cost nothing. The baseline of the four is 860, the cost 73, and the saving 787, which is 91%.

### Example 2

<!-- case: ex8 -->

The cancel question starts at tier 0, whose answer holds `SORRY`, so it escalates to tier 1: both calls are paid, `34 + 150 = 184`, against a baseline of 220. The answer is stored, and the next ask of the same question is an exact hit. The question about limits goes to tier 2, whose answer is `SORRY` and is the last tier: `invalid`, paid (200) and **not** stored, so the second ask calls the model again, with the `doc` prefix now warm. `setSourceVersion("plans", 2)` removes the two entries stored from `plans`, so the cancel question is answered by a call again.

## Constraints

- At most 200 calls per test.
- Prompts, responses, answers and names follow the rules of **Input**. A marker is 1 to 20 characters, each a space or a visible ASCII character.
- An embedding has 2 to 8 integers from -50 to 50, and all the embeddings in a test have the same length. A threshold is an integer from 1 to 1000. A version is an integer from 0 to 1000.
- There are 2 to 4 tiers. A tier limit is an integer from 1 to 1000. There are at most 5 labels and at most 5 markers. A price, a prefix length and `promptTokens` are integers from 0 or 1 (for `promptTokens`) to 1000. `answers` has one text for each tier.
- Every product and sum the statement asks for stays below 2^53 - 1.

## Follow-ups

- The cache has no limit on its size. Which entry would you evict when it is full, and does the answer change if an entry is cheap to compute again but was expensive to learn?
- A semantic hit is a guess. How would you measure how often it is wrong without asking the user, and how would you pick the threshold from that measurement? Would one threshold do for every kind of question?
- The embedding of the question costs something too, and so does a lookup through a large cache. Where is the break-even between a call and a lookup?
- The router here follows a label that someone else computed. What would you do to learn when the cheap tier is good enough, and what do you lose when the check on its answer is itself wrong?
- Escalating pays for the cheap call and the dear call. At what failure rate of the cheap tier does the plan cost more than going straight to the large one, as in the report?
- The cached prefix price here has no expiry and no minimum length. What would you add for a prefix that is evicted after some idle time, and how would that change what a report can promise?

## Hints

### Hint 1

A cache is a notebook. Before doing something slow or costly, you look in the notebook for an earlier result; if it is there you use it, and if not you do the work and write the result down. In a program the notebook is a dictionary (a map) from a key to a value. The only real question is what to use as the key: two questions that mean the same thing should find the same page, so clean up the text first (spaces, capitals) and use the cleaned text.

### Hint 2

Write `key` first and test it alone on messy text. Then `put` and `lookup` are a few lines each. Keep a count of hits and a count of misses, and compute the percent with whole-number division so that it rounds down.

### Hint 3

For the semantic cache, keep one table of entries, each with its key, response, embedding, source, version and the order in which it was stored. A lookup tries the key first, then scans the entries that have an embedding. For the cosine, do not use a square root and a division of decimals: the statement gives an integer formula, and a threshold that is met exactly (such as 0.5) must be met.

### Hint 4

Two entries can have the same permille and still differ a little in cosine, and two can be exactly equal. Decide the winner in two steps: the greater exact cosine first (use the cross-multiplied comparison), then the entry stored first. For `setSourceVersion`, remember that an entry keeps the version it was stored with, and that the removed entries are those of that source with a different version.

### Hint 5

For routing, think of the tiers as a ladder. Start at the rung the label names (or the top, for an unknown label), and climb while the prompt does not fit. Escalation is a second, separate climb of exactly one rung, done only after a call fails the check. Write the validity check as its own small function, with trimming that only removes spaces, tabs and newlines.

### Hint 6

Billing is the part that goes wrong quietly. Write one function that bills a single call to a tier and updates that tier's totals, and call it once for each call that was made, valid or not. Keep, for each tier, the set of prefix ids that have been used there. Compute the reused part before adding the prefix to the set.

### Hint 7

Work out the baseline from the request alone: the prompt tokens and the last answer, priced at the last tier, before the cache or the router has done anything. Total the cost and the baseline over all requests. For the percent, use a floor division that rounds toward negative infinity, since the saving can be below zero.
