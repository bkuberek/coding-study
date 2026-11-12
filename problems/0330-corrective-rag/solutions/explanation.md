# Corrective RAG: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| rank-grade-gate | optimal | O(r (n m + n log n + s)) per query | O(n + v) | default answer; each level adds one gate to the same pipeline |

Here `n` is the number of passages, `m` the length of an embedding, `r` the number of attempts (at most `maxRetries + 1`), `s` the number of sentences and fallback items looked at for one attempt, and `v` the number of verdicts stored.

## How the design grows level by level

| Level | Change | What the pipeline adds |
|-------|--------|------------------------|
| 1 | Retrieve and grade | An exact cosine ranking and a verdict table keyed by (question, item), with `irrelevant` as the default |
| 2 | Refine or fall back | A four-row decision on two booleans, a sentence split, and one ordered pass that builds the evidence |
| 3 | Rewrite and retry | A bounded loop over the question and its rewrites that stops at the first attempt with enough evidence |
| 4 | Grounded answer | A prefix fill under a token budget, citation numbers per source, and a support threshold that can refuse |

The choice that carries the whole design is made at level 1: the verdict table is the only judge of relevance, and a missing verdict reads as `irrelevant`. Every later level only reads that table. Level 2 never trusts a piece without a `relevant` verdict, level 3 counts only such pieces, and level 4 cites only them, so "what reaches the prompt has been checked" holds by construction rather than by care at each step.

## Approach: rank-grade-gate (Exact cosine ranking then verdicts decide what is trusted retried and cited)

### Intuition

Retrieval answers "what sounds like the question?", and the grader answers "what answers it?". The two disagree often enough to matter: a passage about gift card refunds is close to a question about refund times in embedding space and useless to it. So the pipeline ranks by similarity, which is cheap, and then lets the verdicts gate everything after the ranking. Each gate is small: a decision on two facts about the top `k`, a split into sentences for passages that are partly useful, a second source when nothing is useful, another wording when the evidence is thin, and a refusal when it stays thin.

### Algorithm

1. Keep `passages` (id to embedding and text, in the order added), `queries` (query to embedding), `verdicts` ((query, item id) to verdict), `fallbacks` (query to an ordered map of fallback id to text) and `rewrites` (query to an ordered list). Every `add` refuses a key it already has.
2. `retrieve`: return `[]` for an unknown or all-zero query. Otherwise score each passage with a non-zero embedding and sort by the key `(-(d * |d|) / (p · p), id)`, where `d = q · p`. That fraction orders the passages exactly as the cosine does (proof below), so no floating point is needed. Keep the first `k`, each with its verdict (default `irrelevant`). `keepRelevant` and `verdictCounts` filter and count those rows.
3. `decide`: from the top `k`, `R` is "some passage is relevant" and `A` "some passage is ambiguous": `keep` for `R` and not `A`, `refine` for both, `blend` for `A` alone, `fallback` for neither.
4. `evidence`: walk the top `k` in order. A relevant passage gives itself. An ambiguous passage is split after every period, and gives each sentence `n` (from 1) whose verdict for `(query, passageId#n)` is `relevant`. Then, if the action is `blend` or `fallback`, append the question's fallback items whose verdict is `relevant`, in the order added.
5. `attempts`: the candidates are `[query] + rewrites[query][:maxRetries]`. For each, count its evidence and stop after the first with `count >= need`. If none has enough, choose the largest count, the earliest on a tie.
6. `groundedContext`: take the evidence of the chosen attempt and walk it with `remaining = budget`. Stop at the first item with `tokens > remaining`; otherwise subtract. The cite is the passage id (for a passage or one of its sentences) or the fallback id, and a dictionary assigns `len + 1` the first time a cite appears.
7. `answer`: the support is the number of distinct cites in the context. Below `minSupport`, return the refusal; otherwise the `question`, `searched`, numbered lines and `sources` lines, joined by newlines.

### Correctness

Ranking: the query's length `|q|` is the same positive number for every passage, so `cosine(q, p)` orders like `d / |p|` with `d = q · p`. The map `x -> x * |x|` is strictly increasing, so `d / |p|` orders like `(d / |p|) * |d / |p|| = d * |d| / (p · p)`. That is a fraction of integers, and comparing two of them by cross-multiplication is exact. The id breaks every remaining tie, so the order is unique, and because ties in the tests are exact, floating point gives the same order.

Decision and evidence: the action reads only the verdicts of the top `k`, as the table does, and the evidence walk visits the top `k` once in rank order, emitting for each passage exactly the rows its verdict allows. The fallback items are appended exactly when no passage is relevant (`blend` or `fallback`). Every emitted row has a `relevant` verdict for the question: a relevant passage, a relevant sentence, or a relevant fallback item.

Attempts: the candidate list holds the question and at most `maxRetries` rewrites, in order, and the loop stops at the first attempt that meets the threshold, so no attempt after it is made. If none meets it, the earliest attempt with the largest count is the chosen one, which is the statement's tie rule.

Context and support: `remaining` only decreases, so the tokens taken never exceed the budget, and stopping at the first misfit makes the context a prefix of the evidence. A cite gets its number the first time it is seen, so the numbers are 1, 2, 3, ... in order of first appearance, and the support is the number of distinct cites, which is the number of numbers given.

### Complexity

- Time: O(r (n m + n log n + s)) per query — each attempt scores `n` passages of `m` numbers, sorts them, and looks at the sentences and fallback items of its evidence; `r` attempts at most. The add methods are O(1) on average, apart from copying an embedding.
- Space: O(n + v) — the passages, the queries, the verdicts, the fallback items and the rewrites; one query call holds the scores of at most `n` passages.

### Trade-offs

- The full sort costs `n log n`. A heap of size `k` would make each ranking `O(n m + n log k)`, which matters for a large collection; here `k` is small and the evidence and the attempts recompute the ranking several times, so caching the top `k` per question within one call would save more than a heap. A real system keeps an approximate nearest-neighbour index instead of scanning.
- Comparing `d * |d| / (p · p)` exactly makes the two languages agree on every order with no tolerance. Floating point is simpler to write and fine for the tests (their ties are exact), but at a scale where scores crowd together, two programs can disagree in the last bits.
- The decision table counts verdicts. A confidence score with an upper and a lower threshold, as in the published design, says how sure the grader is, and lets the middle band combine both sources; counts are easier to test and to explain.
- Relevant passages are kept whole here. Cutting them down to their relevant sentences too would save tokens and remove distracting text, at the cost of one more grader call per sentence.
- Stopping at the first item that does not fit keeps the context a prefix of the evidence, so a reader knows that everything above the cut was included. Skipping a misfit and going on fits more text into the budget, but a weaker item can then take the place of a stronger one.
- Refusing below a support threshold trades helpfulness for safety. The threshold counts distinct sources, which is a rough stand-in for independent confirmation: two passages copied from one page count twice.

### Pitfalls and edge cases

- Level 1: a missing verdict is `irrelevant`, not `ambiguous`. A verdict belongs to one question: the same passage can be relevant to one and irrelevant to another, and a second verdict on the same pair is refused. Ties go to the smaller id, not to the passage added first. A zero passage is skipped, not scored 0, and a zero or unknown query retrieves nothing. Ranking by the dot product lets a long vector beat a well-aimed one, and ranking by distance is a different order again. Negative scores are returned.
- Level 2: only the top `k` decide the action; a relevant passage just below the cut does not stop the fallback. Ambiguous passages are refined and irrelevant ones are not, even when one of their sentences has a `relevant` verdict. Sentences are numbered from 1 and keep their periods, and an `ambiguous` sentence is dropped. The rows follow the ranking, so a sentence of the first passage comes before a whole passage ranked second. Fallback items are graded too, kept in the order added, and belong to one question. `blend` uses the fallback; `refine` does not.
- Level 3: the threshold is `count >= need`. A rewrite equal to the question, or listed twice, is refused, so it is never tried twice. Only the question's own rewrites are tried. When none has enough evidence, the earliest attempt with the most wins, not the last one tried. The count includes sentences and fallback items.
- Level 4: the tokens are words plus periods, not characters over 4 and not words alone. The fill stops at the first misfit, and an item that fits exactly is taken. A sentence cites its passage, so two sentences of one passage share a number and count as one source. The support counts what was packed, not all the evidence, and an equal support answers. The `question` line is the original question and the `searched` line the chosen attempt.

### Language notes

- Python: `fractions.Fraction(d * abs(d), length)` is an exact sort key, and tuples `(-fraction, id)` sort by score and then by id in one call. `text.split(".")[:-1]` gives the sentences without their periods, because the text ends with a period. A dictionary keeps insertion order, which gives the fallback items their order and the citation numbers theirs.
- TypeScript: plain numbers are exact for integers below 2^53, and with embeddings of at most 8 numbers from -100 to 100 every cross product stays below about 6 * 10^14, so `b.signed * a.length - a.signed * b.length` is an exact comparator. Compare ids with `<` and `>` (code unit order), not `localeCompare`. A `Map` keyed by a joined string stands for the pair (question, item); the separator `|` cannot appear in either part.

## Further reading

- P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", NeurIPS 2020, arXiv:2005.11401: fetching passages at question time and giving them to a generator.
- S.-Q. Yan, J.-C. Gu, Y. Zhu and Z.-H. Ling, "Corrective Retrieval Augmented Generation", arXiv:2401.15884, 2024: a lightweight evaluator scores the retrieved documents; when at least one scores above an upper threshold, refined strips of the documents are used, when all score below a lower threshold, a web search replaces them, and otherwise both are combined. The refinement splits documents into strips, filters them with the evaluator and joins the rest in order. Level 2 is a simplified, count-based version of this shape.
- A. Asai, Z. Wu, Y. Wang, A. Sil and H. Hajishirzi, "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection", arXiv:2310.11511, 2023: a model that generates special tokens to assess the passages it retrieved and its own output.
- X. Ma, Y. Gong, P. He, H. Zhao and N. Duan, "Query Rewriting for Retrieval-Augmented Large Language Models", EMNLP 2023, arXiv:2305.14283: rewriting the input into a better search query before retrieval, the idea behind level 3.
- F. Shi et al., "Large Language Models Can Be Easily Distracted by Irrelevant Context", ICML 2023, arXiv:2302.00093: adding irrelevant information to a problem sharply lowers a model's accuracy, which is the failure level 4 guards against.
- O. Yoran, T. Wolfson, O. Ram and J. Berant, "Making Retrieval-Augmented Language Models Robust to Irrelevant Context", arXiv:2310.01558: when retrieval lowers accuracy instead of helping, and two remedies: filtering passages with an inference model, and training on a mix of relevant and irrelevant contexts.
