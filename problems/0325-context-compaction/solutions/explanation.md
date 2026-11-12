# Context Compaction: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| rolling-summary | optimal | O(F n^2 L) per add for n live turns, F pinned facts and texts of length L | O(T L) for T turns of length L | default answer; the live context is rebuilt from a small state (system turns, summaries, live units, pinned block) after every add |

Here `n` is the number of live turns, `F` the number of pinned facts, `L` the longest text and `T` the number of turns ever added. The `n^2` is the search for the smallest replacement: up to `n` candidates, each rebuilt in `O(F n L)`.

## How the design grows level by level

| Level | Change | What the state adds |
|-------|--------|---------------------|
| 1 | Token rule, cost of a turn, a window of the latest turns | A list of turns and a walk from the newest back |
| 2 | Units, a summary slot and compaction | A list of units (tool runs are one), the list of live units, one summary and a search for the smallest replacement |
| 3 | A stable prefix | A policy flag that appends summaries and compacts to a mark, and the previous prompt to compare with |
| 4 | Pinned facts | A pinned block recomputed at two moments, a budget for it, and a report of what was dropped |

Everything after level 1 comes from one idea: the live context is **derived** from a small state and never edited in place. A function builds the list of items from the state, another adds up their costs, and a compaction is "try this state, measure it, keep it if it fits". That makes the awkward parts easy to state. The smallest replacement is a loop over candidate states. The pinned block is a function of the other items of a candidate state, so it takes part in the loop for free. The prefix reuse is a comparison of two derived lists.

## Approach: rolling-summary (Units and one live list rebuilt on every add)

### Intuition

A conversation is a sequence of turns, but the thing that is kept, cut and summarized is a **unit**: a single message or a whole run of tool calls and results. A cut that falls inside a tool run leaves a call whose result is gone, or a result with no call, which a model cannot make sense of; making the unit the atom removes that case. A compaction then has one job: choose how many of the oldest units to hand to the summary, so that what remains fits. The rest of the problem is accounting: what is in the context, in what order, and what changed since the last prompt.

### Algorithm

1. Keep `turns` and `units` (lists of turn numbers; a call or a result that follows a call or a result joins the last unit, anything else other than a system turn starts a new one). Keep `live` (the units not replaced), the `summaries` in the live context, the queue of given summaries with a pointer, the pinned facts and the pinned block (a list of fact ids).
2. `countTokens` scans the text for runs of letters and digits (1 token per 4 characters, rounded up) and for single other non-white-space characters. A turn costs that plus 4.
3. `window`: sum the costs of the system turns and subtract from the budget; walk the units from the newest, take a unit if all its turns fit in the remaining turns and its cost fits in the remaining tokens, otherwise stop; return the system turns followed by the taken turns in order.
4. `items(state)` builds the live context: the system turns, then the summaries, then the pinned block if it is not empty, then the live units' turns. Its cost is the sum of the item costs.
5. After each successful add, build the prompt. If compaction is on and the cost is above the threshold, there is an unused summary and there are candidates (live units but the last `keepRecent`), try `k = 1, 2, ...`: the state without the first `k` candidates, with the summary replacing the old one (or appended, under the stable policy), and the pinned block recomputed for it. Keep the first `k` whose cost is at most the target (the threshold, or the low-water mark under the stable policy), or the last one tried. Record the replaced turns, move the pointer and count the compaction.
6. The block is chosen by walking the facts in pin order: skip a fact whose text is a substring of another item of the state, skip one that would push the block over the budget (and go on), take the rest. It is chosen when a fact is pinned and for every candidate state in step 5.
7. `prefixReuse`: after the compaction (if any), compare the new prompt with the previous one item by item, add the costs while kind and text are equal, push the sum, and keep the new prompt as the previous one.

### Correctness

Units are never split because the only operations that remove turns remove whole units from the `live` list, and `window` takes or leaves a unit whole. A tool run is one unit because every turn that continues a run is appended to the last unit, and a run ends at the first turn of another kind; the tests never put another turn between a call and its result, so a run is complete when it is closed. The last `keepRecent` units are never candidates, and `keepRecent` is at least 1, so the unit that is still growing (the last one) is never replaced while a call can still join it.

The minimal `k` is found because the loop tries the replacements in order of size and takes the first that meets the target; the cost of a candidate state is computed from the state, not from the current one, so nothing that was tried can leak into the next try. When no `k` fits, taking all candidates is the largest reduction possible, which is what the statement asks for, and the next add tries again with what is left.

The pinned block is correct by construction: its facts are exactly those not already present in the other items, in pin order, within the budget, and it is recomputed at the two moments the statement names. Because it is computed on the candidate state, a compaction that removes the turn holding a fact brings the fact into the block in the same step, and the size that decides the choice of `k` is the size with the block.

Prefix reuse is correct because a prompt is a list of items compared position by position: the common prefix is the longest run of equal leading items, and an item's cost depends only on its text, so the sum of the costs is the tokens of the common prefix.

### Complexity

- Time: O(F n^2 L) per add for n live turns, F pinned facts and texts of length L — the search tries up to `n` candidate states; each rebuilds the item list in `O(n)` and chooses the block with `F` substring tests against `n` texts of length `L`. Without pinned facts it is `O(n^2)`, and a add that does not trigger compaction is `O(n)` to build the prompt.
- Space: O(T L) for T turns of length L — the turns and the summaries are stored once, and the state keeps only indices; only the previous prompt is kept for the prefix, not one prompt for each add.

### Trade-offs

- **Replace against append.** A single summary slot stays small, and a new summary must cover the old one, which in a real harness means asking the model to summarize its own summary and losing detail each time. Appending keeps old summaries byte-identical, which suits a prefix cache, and the context grows by one summary per compaction until something merges them.
- **Compacting to a mark.** Compacting down to a low-water mark does fewer, bigger compactions: each one rewrites the prefix, so fewer is better for a cache; but each one summarizes more at once, so a summary has to carry more, and the context is smaller than it could be. The choice of the mark is a trade between how often the cache is broken and how much is thrown away each time.
- **Where the pinned facts go.** Putting the block after the summaries keeps the system turns and the summaries as a stable prefix, but it puts the facts in the middle of a long context, which the position study found to be the weakest place. A harness that cares about recall more than about cache hits would put them at the start (after the instructions, rewriting the prefix whenever the block changes) or repeat them at the end.
- **Rule-based tokens against the real count.** The rule here is simple, exact and testable. A real tokenizer splits text into subword units whose vocabulary is built from data, so its counts depend on the model and are not a function of word length. A real harness uses the model's own counter, or keeps a safety margin.
- **Summaries as data.** The summarizer is the part that can fail in production: it can drop a fact, invent one, or be much longer than asked. Treating it as data makes the problem deterministic, and it is why the pinned block checks the text of the facts against what the summary actually says.

### Pitfalls and edge cases

- Level 1: the cost of a turn includes the framing, and an empty turn is not free. System turns are kept even when they alone are over the budget, they come first whatever their position in the conversation, and they do not count against `maxTurns`. The walk stops at the first turn that does not fit; it must not skip it and take an older one. A budget equal to the cost fits.
- Level 2: the threshold is strict (`>`), so a context that is exactly at the threshold is left alone. Cut at units, never at turns: with `maxTurns` smaller than a tool run, the run is left out whole. A call id can be used once, and a result needs an earlier call without a result; a failed add takes no turn number and makes no compaction. The last `keepRecent` units are never replaced, and a window that cannot get under the threshold even with all the candidates replaced is compacted again at the next add. A summary replaces the previous one, whose position then no longer appears in the context. When the summaries are used up nothing happens; `setSummaries` starts a new list from its first. `window` does not look at compaction.
- Level 3: reuse is the tokens of the longest common prefix of items, so compare kind and text, never the turn number (a summary whose text equals a turn's text is a different item). The first add reuses nothing. A failed add makes no prompt. Under the stable policy the summaries stay in order and untouched, and the target is the mark; the trigger is still the threshold.
- Level 4: the block is chosen when a fact is pinned and when a compaction happens, not at every add, so a fact stays in the block after a new turn repeats it, until the next compaction. A fact whose text appears in a system turn is never carried. The budget includes the 4 tokens of framing, so a budget of 4 holds no fact; a fact that does not fit is skipped and the next one is tried. `dropped` lists replaced turns in increasing order and then the lost facts in pin order, and a fact held by a summary is not lost.

### Language notes

- Python: `re.findall` with an alternation gives the words and the single characters in one pass, and `-(-len(piece) // 4)` is the ceiling without floats. `str.__contains__` (`text in item.content`) is the substring test. Dataclasses with `slots=True` keep the items light.
- TypeScript: `String.prototype.match` with the `g` flag returns `null` when there is no match, hence `?? []`. `includes` is the substring test, `Math.ceil` on a division is exact for these small integers, and `flatMap` turns "indices of the system turns" into one expression. A `Map` keeps the facts in pin order and has a `has` and a `get` that need no care about inherited keys.

## Further reading

- N. F. Liu et al., "Lost in the Middle: How Language Models Use Long Contexts", Transactions of the Association for Computational Linguistics 12:157-173, 2024, doi:10.1162/tacl_a_00638 (arXiv:2307.03172): the U-shaped curve of accuracy against the position of the relevant document, the key-value retrieval task, the tests on model design and on repeating the question, and the comparison with the serial-position effect in human memory.
- L. Zheng et al., "SGLang: Efficient Execution of Structured Language Model Programs", arXiv:2312.07104: the observation that the cached keys and values of a prompt depend only on the tokens before them, so that requests with the same prompt prefix can reuse them, and a cache organized as a tree of prefixes.
- W. Kwon et al., "Efficient Memory Management for Large Language Model Serving with PagedAttention", SOSP 2023, arXiv:2309.06180: sharing of the stored keys and values within and across requests to reduce memory use.
- R. Sennrich, B. Haddow and A. Birch, "Neural Machine Translation of Rare Words with Subword Units", ACL 2016, arXiv:1508.07909: splitting words into subword units, including by byte pair encoding, which is why a token count is not a count of words or of characters.
