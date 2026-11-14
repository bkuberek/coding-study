# Corrective RAG

## Statement

Build `CorrectiveRag`, the retrieval step of a help assistant that checks what it found before it lets a language model read it. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is RAG, and what goes wrong?** A language model answers from what it learned in training, which may be old, incomplete or about someone else's product. *Retrieval-augmented generation* (RAG) fetches relevant text at question time, puts it in the prompt, and asks the model to answer from it. The usual fetch compares *embeddings*: every stored passage, and the question, is turned into a vector of numbers, and the passages whose vectors point most nearly the same way as the question's are taken. That finds passages that *sound* like the question, which is not the same as passages that *answer* it. "Gift cards cannot be refunded" sounds very much like "how long do refunds take", and answers nothing. A model handed such a passage often uses it anyway, and the answer comes out confident and wrong.

A *corrective* retriever adds a check. A grader (in practice a small model, or a person building a test set) reads each retrieved passage against the question and gives a **verdict**: `relevant`, `ambiguous` or `irrelevant`. The retriever then decides what to do with what it found: keep the relevant passages, cut the ambiguous ones down to their useful sentences, look in a second source when nothing is relevant, try the question again in other words, and, when the evidence is still too thin, refuse instead of letting the model guess. In this problem every embedding, verdict, second-source item and rewrite arrives as data, so that the answers are exact.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 35, level 2 by 65, level 3 by 90 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `CorrectiveRag()`: creates an empty retriever.
- An id (`passageId`, and the other ids a level adds) is 1 to 20 characters from `a` to `z`, `0` to `9` and `_`, compared by the numeric value of its characters, so digits come before `_`, which comes before letters.
- A `query` is 1 to 60 characters from `a` to `z`, `0` to `9` and the space, and is compared exactly as given: two queries that differ in one character are two queries.
- An `embedding` is a list of 1 to 8 integers from -100 to 100. Every embedding in one test has the same length.
- A `text` is one or more sentences joined by single spaces. A sentence is one or more words joined by single spaces, with a period right after its last word, as in `refunds are paid within 14 days. the money goes back to your card.` A word is 1 to 20 characters from `a` to `z` and `0` to `9`.
- A `verdict` is `relevant`, `ambiguous` or `irrelevant`.
- `k` is an integer from 1 to 20. Each level's section describes the methods it adds and their parameters.

## Output

Passages and other evidence come back as rows of text, as described by each method. Numbers in rows are written in decimal as text.

## Level 1: Retrieve and grade

- `addPassage(passageId, embedding, text)`: stores a passage. It returns `true` when the id is new, and `false` when it is already stored, in which case nothing changes.
- `addQuery(query, embedding)`: stores the embedding of a question. It returns `true` when the query is new, and `false` otherwise, in which case nothing changes.
- `addVerdict(query, itemId, verdict)`: records the grader's verdict on the item `itemId` (at this level, a passage) for the question `query`. It returns `true` when that item had no verdict for that question, and `false` otherwise, in which case the first verdict stands. A verdict may name a query or an item that is not stored yet; it counts once both are. The same passage can have different verdicts for different questions.
- `retrieve(query, k)`: the `k` passages most similar to the question, best first, as rows `[passageId, verdict]`.
- `keepRelevant(query, k)`: the ids of the passages among `retrieve(query, k)` whose verdict is `relevant`, in the same order.
- `verdictCounts(query, k)`: how many of the passages of `retrieve(query, k)` are `[relevant, ambiguous, irrelevant]`.

**Similarity.** The score of a passage is the **cosine similarity** of its embedding `p` and the query's embedding `q`, the cosine of the angle between them:

```text
cosine(q, p) = (q · p) / (|q| * |p|)

q · p = q[0] * p[0] + q[1] * p[1] + ... + q[m - 1] * p[m - 1]
|v|   = sqrt(v · v)
```

It is 1 when the two point the same way, 0 when they are at right angles and -1 when they point opposite ways. Length does not count: `[6, 8]` scores the same as `[3, 4]`. The rules:

- A higher score is better. **Equal scores go to the smaller id.**
- A passage whose numbers are all zero has no direction, so it has no score: it is never retrieved.
- A query whose numbers are all zero, or a query that was never added, gives no passage a score, so the result is empty (`[]`, and `[0, 0, 0]` for the counts).
- A negative score is still a score: a passage that points away is returned when it is among the `k` best.
- When fewer than `k` passages have a score, all of them are returned.

Two passages tie in a test only when their cosines are equal however the arithmetic is done, so computing the scores in floating point gives the same order as computing them exactly. (An exact way exists too: hint 2.)

**Verdicts.** A retrieved passage with no verdict for the question counts as `irrelevant`: text that nobody has checked is not trusted. The verdict is never derived from the score. A passage can be very similar and irrelevant, and the verdicts are the only judge of relevance.

### Example 1

<!-- case: ex1 -->

`refund_gift` is the second most similar passage to "how long do refunds take", since it is also about refunds, but the grader has judged it irrelevant: it is about gift cards. Similar is not the same as relevant, and that is why the verdicts exist. Of the top 3, one passage is relevant, one ambiguous and one irrelevant. With `k` 5, `ship_times` and `account_pw` join, and nobody graded them, so they count as irrelevant. The second `refund_policy` and the second verdict on `refund_gift` are refused and change nothing. A question that was never added retrieves nothing.

### Example 2

<!-- case: ex2 -->

`b` points the same way as `a` and is twice as long, so both score 1, and the tie goes to the smaller id, `a`. `e` scores `0.96`, and `d`, which points the opposite way, scores -1 and still comes back. `c` has no direction and is skipped, so `k` 5 returns 4 passages. `d` is the only passage with a verdict, `relevant`, so it is kept when `k` reaches it, however low its score: the grader decides what is relevant, not the score. A query of zeros has no direction and retrieves nothing.

## Level 2: Refine or fall back

The verdicts now decide what the retriever does. Relevant passages are kept whole. An ambiguous passage is cut into sentences, and only its sentences that the grader judged relevant are kept. When no passage is relevant, a **fallback** source, such as a search of a larger collection, is asked, and its items are kept when the grader judged them relevant. Every piece of evidence therefore has a `relevant` verdict for the question.

- `addVerdict(query, itemId, verdict)` now also takes, as `itemId`, the id of a sentence or of a fallback item.
- `addFallback(query, fallbackId, text)`: stores an item that the fallback source returns for `query`, after the items already stored for it. It returns `true` when the question has no item with this id yet, and `false` otherwise, in which case nothing changes. A fallback id is never the id of a passage. Fallback items belong to the question they were added for.
- `decide(query, k)`: the action for the top `k` passages, from the table below.
- `evidence(query, k)`: the evidence, as rows `[itemId, text]`, in the order below.

**Sentences.** A passage's text is split after every period. Its sentences are numbered from 1, and sentence `n` of passage `p` has the id `p#n` (as in `returns_how#2`). The text of a sentence includes its period and not the space before the next one.

**The decision.** Among the passages of `retrieve(query, k)`, let `R` be the number with verdict `relevant` and `A` the number with verdict `ambiguous`:

| `R` | `A` | Action | Evidence |
|-----|-----|--------|----------|
| at least 1 | 0 | `keep` | the relevant passages |
| at least 1 | at least 1 | `refine` | the relevant passages and the relevant sentences of the ambiguous passages |
| 0 | at least 1 | `blend` | the relevant sentences of the ambiguous passages, then the relevant fallback items |
| 0 | 0 | `fallback` | the relevant fallback items |

An empty retrieval has `R = A = 0`, so its action is `fallback`.

**The order.** Go through the passages of `retrieve(query, k)` in their order: a relevant passage gives the row `[passageId, text]`, an ambiguous passage gives one row `[sentenceId, sentence]` for each of its relevant sentences, in sentence order, and an irrelevant passage gives nothing. Then, for `blend` and `fallback` only, add one row `[fallbackId, text]` for each of the question's fallback items whose verdict is `relevant`, in the order they were added.

This follows the shape of a published design (see the explanation's further reading), with one simplification: there, a confidence score with two thresholds chooses among three actions, and relevant passages are also cut down to their useful parts.

### Example 1

<!-- case: ex3 -->

For "how long do refunds take" the top 3 hold one relevant passage and two irrelevant ones (one of them ungraded), so the action is `keep` and the evidence is `refund_policy`, whole. For "when does the refund start", `returns_how` comes first and is ambiguous. Its sentence 2 is relevant, sentence 1 is not and sentence 3 has no verdict, so only sentence 2 is kept. `refund_policy`, third, is relevant, so the action is `refine`, and the rows follow the ranking: the sentence first, then the whole passage.

### Example 2

<!-- case: ex4 -->

For "do gift cards expire" the only graded passage, `refund_gift`, is ambiguous, and its second sentence is relevant. No passage is relevant, so the action is `blend`: the sentence, then the fallback item `faq_gift`. For "can i pay with crypto" nothing in the top 3 is relevant or ambiguous, so the action is `fallback`. Of its three fallback items, `web_pay` is ambiguous and `forum_pay` has no verdict, so only `faq_pay` is kept; the second `faq_pay` was refused. A question that was never added has nothing retrieved, falls back, and has no fallback items.

## Level 3: Rewrite and retry

When the evidence is too thin, the question may be badly worded for the collection: "refund for a broken phone" retrieves passages about phones. Trying the question again in other words often finds what the first wording missed.

- `addRewrite(query, rewrite)`: adds `rewrite` to the list of rewrites of `query`, after the ones already there. It returns `true` when it was added, and `false` when `rewrite` equals `query` or is already in its list, in which case nothing changes. A rewrite is a query like any other: its embedding, verdicts and fallback items are its own, and it may have none.
- `attempts(query, k, need, maxRetries)`: tries the question and then its rewrites, and returns one row per attempt, `[query, action, count, mark]`.

**The attempts.** The first attempt is `query` itself; the next ones are the rewrites of `query`, in their order, at most `maxRetries` of them. Only the rewrites of `query` are tried, not the rewrites of a rewrite. The `count` of an attempt is the number of rows of `evidence(attempt, k)`, and its `action` is `decide(attempt, k)`. An attempt has **enough** evidence when `count >= need`. The attempts stop after the first one with enough evidence; no later rewrite is tried.

**The choice.** The chosen attempt is the first one with enough evidence. When none has enough, it is the one with the largest count, the earliest of those on a tie, so the original question wins when every count is 0. The chosen attempt has the mark `chosen`, and every other one `tried`.

### Example 1

<!-- case: ex5 -->

"refund for a broken phone" retrieves passages about phones and warranties, which nobody graded for it, so it falls back and finds nothing. The first rewrite finds one relevant passage, `damaged`. The second keeps `returns_how` and the first sentence of the ambiguous `refund_policy`, 2 pieces, which is enough, so it is chosen and "warranty claim" is never tried. With `maxRetries` 1 only the first rewrite is tried, no attempt has enough, and the one with the most evidence is chosen. With `need` 1 the first rewrite is already enough. The repeated rewrite and the question as its own rewrite were refused.

### Example 2

<!-- case: ex6 -->

The counts are 0, 1, 1 and 0, and none reaches 3. The largest count, 1, is reached first by "refund for a damaged item", which is chosen over "phone refund". "phone refund" has no embedding, so it retrieves nothing and falls back, and its one relevant fallback item is its evidence. With `maxRetries` 0 only the question is tried, and it is chosen with no evidence at all. "broken screen" asked on its own is one attempt: the rewrites belong to the question they were added for.

## Level 4: Grounded answer

The evidence of the chosen attempt is put into the prompt with numbered citations, within a **token budget** (a token is the unit in which a model counts text), and the answer is refused when the support is too thin. This is the point of the whole pipeline. A pipeline that pastes the top passages into the prompt, whatever they say, hands the model text that only sounds related, and models are easily led by it. Here only evidence with a `relevant` verdict is ever shown, and when there is not enough of it, the result says so instead of letting the model fill the gap.

- `groundedContext(query, k, need, maxRetries, budget)`: the context for the chosen attempt of `attempts(query, k, need, maxRetries)`, as rows `[number, cite, tokens, text]`.
- `answer(query, k, need, maxRetries, budget, minSupport)`: the text of the prompt's context, or a refusal.

**Tokens.** `tokens(text)` is the number of words plus the number of periods: `the refund starts when the parcel arrives.` is 7 words and 1 period, 8 tokens.

**The context.** Go through the evidence of the chosen attempt in order, with `budget` tokens left at the start. Take an item when its tokens are at most the tokens left, and subtract them. **Stop at the first item that does not fit**: no later item is taken, even a smaller one, so the context is always the beginning of the evidence, in its order.

**Citations.** The `cite` of an item is the passage it comes from: the passage id for a whole passage and for each of its sentences (`returns_how#2` cites `returns_how`), and its own id for a fallback item. The `number` of an item is the citation number of its `cite`: the distinct cites are numbered from 1 in the order in which they first appear in the context, so two sentences of one passage share a number.

**Support.** The **support** of the context is the number of distinct cites in it. When it is less than `minSupport`, `answer` returns `not enough evidence: <support> of <minSupport> sources`, as in `not enough evidence: 1 of 2 sources`. Otherwise it returns these lines, joined by `\n`, with no newline at the end:

```text
question: <query>
searched: <the query of the chosen attempt>
[<number>] <text>                one line per row of the context, in order
sources: [1] <cite>, [2] <cite>  every distinct cite with its number, in order of number
```

### Example 1

<!-- case: ex7 -->

The evidence is sentence 2 of `returns_how` (8 tokens), its sentence 3 (4 tokens) and `refund_policy` (13 words and 2 periods, 15 tokens). With 30 tokens all three fit. Both sentences cite `returns_how`, which is number 1, and `refund_policy` is number 2. With 20 tokens the two sentences use 12, `refund_policy` does not fit in the 8 left, and the context stops there. Its only source is `returns_how`, so asking for 2 sources gets a refusal.

### Example 2

<!-- case: ex8 -->

"how do i cancel my order" retrieves two passages about shipping and returns, which share its words and not its subject, and both are judged irrelevant. There is no evidence, so the answer is refused. A pipeline that pasted the top passages in anyway would hand the model "orders ship within 2 days", from which it could well invent a cancellation rule. With one retry the rewrite "cancel an order" falls back to `faq_cancel`, which answers it, and the context cites that item; the second line shows the rewrite that was searched. Asking for 2 sources refuses again, and so does a budget of 0, in which nothing fits.

## Constraints

- At most 2000 calls per test, at most 300 passages and at most 100 queries.
- A text has at most 10 sentences and at most 60 words. `need` is from 1 to 20, `maxRetries` from 0 to 5, `budget` from 0 to 10^4 and `minSupport` from 1 to 10.
- A query has at most 5 rewrites and at most 10 fallback items.

## Follow-ups

- Here the verdicts are given. A real grader is a model call per passage, and another per sentence when a passage is refined. How would you keep that affordable: a cheaper grader first, a cache keyed by question and passage, grading only what could fit the budget?
- The decision table counts verdicts. A grader that returns a confidence score needs thresholds instead. How would you choose an upper and a lower threshold from labelled examples, and what does the band between them buy?
- The rewrites are given. Generated rewrites can drift from what the user asked ("refund for a broken phone" becoming "phone repair"). How would you check that a rewrite still asks the same question, and which of the evidence would you show the user?
- A fallback source such as a web search returns text that anyone could have written, including instructions aimed at the model. What would you do with that text before it reaches the prompt, besides grading its relevance?
- Two passages copied from one page are not two independent sources. How would you count support so that duplicates do not pass the threshold?
- A refusal is safe but unhelpful. How would you measure the trade-off between refusing too often and answering without support, and what would you put in the refusal so that the user can act on it?

## Hints

### Hint 1

Start with the ranking alone. For each passage, compute how similar its vector is to the question's vector with the formula of the statement, skip the passages whose vector is all zeros, sort from the highest score down (smaller id first on a tie), and keep the first `k`. Then the verdicts: a dictionary keyed by the pair (question, item id), where a missing key reads as `irrelevant`. Everything else in level 1 is a pass over those `k` passages.

### Hint 2

Floating point works here, but the order can also be decided exactly with integers. The question's length is the same for every passage, so comparing `cosine(q, a)` with `cosine(q, b)` is comparing `(q·a) / |a|` with `(q·b) / |b|`. Square roots go away if you compare `(q·a) * |q·a| / (a·a)`, a fraction that keeps the sign and orders the passages the same way: cross-multiply two of them, and every product stays below 2^53.

### Hint 3

The decision depends on two facts about the top `k`: whether any passage is relevant, and whether any is ambiguous. Compute both, and the table becomes four branches. Build the evidence in one pass over the top `k`, then add the fallback items only when no passage was relevant.

### Hint 4

Splitting after every period, rather than on ". ", handles the last sentence, which has no space after it. Number the sentences from 1 and look each one up as `passageId#n` in the same dictionary of verdicts, under the same question. The fallback items need their own list per question, kept in the order they were added.

### Hint 5

The attempts are a loop over `[query] + rewrites[:maxRetries]` that stops early. Keep the count of each attempt as you go. If the loop finishes without enough evidence, choose the largest count, and on a tie the earlier attempt, which a strict `>` comparison while scanning gives you.

### Hint 6

Level 4 is one pass over the evidence of the chosen attempt with a counter of tokens left; it `break`s at the first item that does not fit. Give citation numbers with a dictionary from cite to number, assigning `len(dictionary) + 1` the first time a cite appears. The support is the size of that dictionary, and the answer is refused when it is smaller than `minSupport`, not when it is equal.
