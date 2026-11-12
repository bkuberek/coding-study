# Context Compaction

## Statement

Build `ContextWindow`, the part of a chat assistant that keeps a long conversation inside the model's *context window*. A language model reads text as *tokens* (small pieces of words), and it can read only so many at once: the instructions, the conversation so far and the room for its answer must fit in that window. A conversation that runs for hours does not fit. So the harness around the model (the ordinary program that calls it) has to decide what to send: keep the instructions, keep the latest turns, and replace old turns with a short summary. This problem is that decision, with no model involved: texts, summaries and costs are all data. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**Why the order matters.** The weak spot of a long context is its middle. Liu and others (*Lost in the Middle: How Language Models Use Long Contexts*, Transactions of the Association for Computational Linguistics, 2024) hid the one document that held the answer among many others, moved it around, and measured how often the model answered right. The answers were best when the document came first or last and worst when it was in the middle, a U-shaped curve, and in a second test, finding the value of a key in a long list of key-value pairs, several models showed the same shape. It held even for models explicitly built for long inputs. The paper reports the effect and tests some explanations without settling on one: it compared model designs, it found that repeating the question before the documents fixed the key-value test and barely changed the question-answering one, and it points out that people also remember the first and last items of a list best. For a harness the lesson is practical. Put what must always be obeyed at the start, keep the newest turns at the end, and do not expect a long middle to be used as well as its edges.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 25, level 2 by 60, level 3 by 85 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `ContextWindow()`: creates a window with no turns, no summaries, no compaction and no pinned facts.
- A **turn** is one message of the conversation. Its `role` is `system` (the instructions), `user` or `assistant`; level 2 adds `call` (the assistant asks for a tool to be run) and `result` (what the tool returned). Turns are numbered from 0 in the order they are added, whatever their role.
- `content` is text of printable ASCII characters (codes 32 to 126), tabs and newlines, at most 200 characters, possibly empty.
- Each level's section describes the methods it adds and their other parameters.

## Output

Methods that add something return the number of the turn. Lists of turn numbers are in the order described by their level. A text that is a number (a size, a number of tokens) is written in decimal. No method throws, whatever order they are called in.

## Level 1: Counting tokens and keeping the latest turns

**How tokens are counted.** Real tokenizers are learned from data and differ from model to model; this problem uses a rule of its own that is simple and exact. A **word** is a maximal run of the letters `A` to `Z`, `a` to `z` and the digits `0` to `9`. A word costs one token for each 4 characters, rounded up (`abcd` is 1, `abcde` is 2). Every other character that is not a space, a tab or a newline costs one token by itself, so `_` and `-` are tokens, and `snake_case_name` is `snake`, `_`, `case`, `_`, `name`, which is 2 + 1 + 1 + 1 + 1 = 6. Spaces, tabs and newlines are free. A turn also costs a fixed 4 tokens of framing (the markers that tell the model who is speaking), so **the cost of a turn is the tokens of its content plus 4**, and an empty turn costs 4.

- `countTokens(text)`: the number of tokens of a text by this rule, without the framing.
- `addTurn(role, content)`: adds a turn with the role `system`, `user` or `assistant` and returns its number.
- `window(budget, maxTurns)`: the turns to send, as a list of turn numbers, so that they fit in `budget` tokens (the sum of the costs of the turns).

`window` works like this. All the `system` turns are always kept, even if they alone cost more than `budget`, and they come first, in the order they were added, wherever in the conversation they were added. The other turns are then taken from the newest to the oldest while they fit: a turn is taken when the tokens left after the system turns and the turns already taken are at least its cost, and when taking it would not make more than `maxTurns` turns that are not system turns. The first turn that does not fit ends the walk, even if an older one would fit: the kept turns are a run of the most recent ones, never a run with a hole. They are listed after the system turns, oldest first.

### Example 1

<!-- case: ex1 -->

`Hello, world!` is `Hello` (2), `,` (1), `world` (2) and `!` (1), which makes 6. The system turn `Be brief.` costs 8: 4 tokens of content (`Be` 1, `brief` 2, `.` 1) and 4 of framing. With a budget of 100 and room for 10 turns, every turn is kept. With 30 tokens, 22 are left after the system turn, and the walk takes `6.` (6), then `And 3+3?` (9), and stops at `It is 4.` (8) because 7 are left. With room for two turns the answer is the same list. With 7 tokens, the system turn alone already costs more than the budget and it is kept anyway, and nothing else fits.

## Level 2: Compacting old turns into a summary

A fixed window forgets everything older. **Compaction** keeps the gist instead: when the conversation grows too big, the oldest turns are replaced by a **summary**, a short text that stands for them. A real harness would ask a model to write it; here the summaries are given as data, as a list that is used in order.

**Tool calls.** An assistant can ask for a tool to be run, and the harness answers with the result. Both are turns:

- `addCall(callId, content)`: adds a `call` turn for the call called `callId` and returns its number. It returns `-1` and adds nothing when `callId` was used by an earlier call.
- `addResult(callId, content)`: adds a `result` turn for the call `callId`. It returns `-1` and adds nothing when there is no earlier call with that id, or when that call already has a result.

A result without its call, or a call without its result, makes no sense to a model, so the two must never be separated. Calls and results can come in any order within a group (several calls can be made at once, and their results come back in any order), so the unit that is never split is a **tool run**: a maximal run of consecutive `call` and `result` turns. A **unit** is either one turn that is not a system turn and not part of a tool run, or a whole tool run. From now on, `window` takes and leaves units: it takes a unit when its total cost fits and when all its turns fit in the `maxTurns` left, and otherwise the walk ends. (Tests never add a turn between a call and its result.)

- `setSummaries(texts)`: sets the list of summaries, replacing any earlier list, and starts again from its first.
- `setCompaction(threshold, keepRecent)`: turns compaction on. `threshold` is a number of tokens and `keepRecent` is at least 1. The settings can be changed at any time.
- `context()`: what would be sent now, as rows `[kind, ref, tokens]` in order (the **live context**), described below.
- `compactions()`: how many compactions have happened.

**The live context** holds, in this order: every system turn; then the summary, if there is one; then the units that have not been replaced, in order. Its size is the sum of the costs of its items, where a summary costs its tokens plus 4 like a turn. A row has the `kind` (the role of a turn, or `summary`), a `ref` (the number of the turn, or, for a summary, its position in the list given to `setSummaries`, from 0) and the cost.

**When to compact.** After each successful add (`addTurn`, `addCall` or `addResult`), if compaction is on and the live context is **over** the threshold (strictly more than it), one compaction is attempted. The **candidates** are the live units that are not among the last `keepRecent` units. If there are no candidates, or no unused summary is left, nothing happens. Otherwise the next unused summary is used, and the oldest `k` candidates are replaced by it, where `k` is the smallest number from 1 to the number of candidates for which the live context, after the replacement, is at most the threshold; if no `k` does that, all the candidates are replaced. The summary **replaces** the previous one, if there was one: the new summary is understood to cover everything that the old one did. A replacement is made even if the summary costs more than what it replaces. One add makes at most one compaction, so a window that is still over the threshold is compacted again at the next add. `window` is not affected by compaction: it looks at all the turns ever added.

### Example 1

<!-- case: ex2 -->

The threshold is 60 and the last 2 units are kept. After the 7 turns of the first part the live context costs 56 and nothing has happened. The turn `Now 10*10?` brings it to 65: the candidates are the first four units (the question, the tool run, the answer and the next question), and replacing the first one is not enough (66), but replacing two, the question and the whole tool run, gives 51, so that is what happens, and the first summary (cost 11) takes their place. After two more turns the context is over again; the second summary (cost 9) replaces the first, which is no longer in the context, and one unit is enough this time. `window` still sees every turn.

## Level 3: A stable prefix

A model reads its input in order, and what it computes for a token depends only on the tokens before it. A serving system can therefore keep that work for a prefix of the input and reuse it when a later request begins with exactly the same tokens, which makes long prompts cheaper and faster (this is called *prefix caching*; the idea of sharing the stored work of a common prefix is described in the papers listed in the explanation). One changed token ends the reuse: everything after it has to be computed again. For a conversation this means that rewriting the beginning of the context at every turn wastes the saving, while appending to it keeps the saving. Compaction rewrites the beginning, so this level measures what it costs and offers a policy that rewrites less.

- `prefixReuse()`: one number for each successful add, in order. Call the **prompt** of an add the live context right after that add, with any compaction. The number is the tokens of the longest prefix that this prompt shares with the prompt of the previous add: the leading items that are equal one by one, an item being equal to another when its kind and its text are equal (the `ref` does not matter), summed by their cost. The first add shares nothing, so its number is 0. An add that returns `-1` makes no prompt.
- `setStablePrefix(lowWater)`: turns on the **stable policy**, with `0 <= lowWater <= threshold`; it can be called again to change the mark. With it, compaction changes in two ways. Summaries are **appended**: the new summary goes after the summaries that are already there, which stay as they are and in order, and the live context holds them all. And a compaction goes down to `lowWater` instead of the threshold: `k` is the smallest number for which the live context, after the replacement, is at most `lowWater`. Compactions are still triggered by the threshold.

The stable policy has the two ingredients of a cache-friendly design. The summaries and the instructions never change once written, so the prefix before the new material stays the same; and compacting in bigger steps down to a mark happens less often, so the prefix is rewritten less often. Without the policy, every compaction rewrites the single summary and everything after it.

### Example 1

<!-- case: ex3 -->

A system turn and ten more turns, with the threshold 60, the stable policy and a mark of 40. There is one compaction, at the eighth turn, when the context reaches 63: the smallest replacement that reaches 40 or less takes five units and leaves 32, with the first summary appended after the instructions. `prefixReuse` shows the cost of that moment: 8, only the instructions, because the summary took the place of the turns that followed them. Before it every add shared the whole previous prompt (8, 18, 26, 35, 41 and 50 are the growing sizes), and after it the whole previous prompt again (32, 39 and 45). Without the policy, the same chat is compacted three times in a row, each time sharing only the instructions.

## Level 4: Pinned facts

A summary is a guess about what matters. Some facts must survive however the conversation is compacted: the user's name, a deadline, a rule of the task. This level lets the harness name them, and carries them forward when a compaction would lose them.

- `pinFact(factId, text)`: pins a fact: a short text that must stay in the context. Returns `false` and changes nothing when `factId` is already pinned.
- `setPinBudget(tokens)`: the most the **pinned block** may cost, framing included; `-1` (the default) means no limit.
- `recall(factId)`: `true` when the fact is pinned and its text occurs, as written (a substring, with the same letter case), in the content of some item of the live context, including the pinned block. `false` otherwise, and for an unknown fact.
- `dropped()`: what compaction took out of the context, as rows: first one row `["turn", n]` for each turn that a compaction replaced (`n` is the turn number written as a string, such as `"1"`), with the numbers in increasing order, then one row `["fact", factId]` for each pinned fact that cannot be recalled now, in the order they were pinned.

**The pinned block.** It is one more item of the live context, of kind `pinned`, placed after the summaries and before the turns. Its content is the texts of its facts, one per line, in the order the facts were pinned, and its `ref` is their ids joined by `,`; it costs its tokens plus 4 like any item, and it is absent when it has no fact. Its facts are chosen as follows: take the pinned facts in order; skip a fact whose text occurs in the content of any other item of the live context (a system turn, a summary or a turn that is still there), because it is already present; and skip a fact that does not fit, which means that the block, with the facts chosen so far and this one, would cost more than the pin budget, but go on to look at the next fact. The block is chosen again **when a fact is pinned** and **when a compaction happens**, and not at every add: in between it does not change, even if a new turn happens to hold a fact. The block counts in the size of the live context, so the choice of `k` in a compaction is made with the block that each candidate replacement would leave behind.

### Example 1

<!-- case: ex4 -->

The user's first message holds both facts, so when they are pinned nothing needs to be carried and there is no block. The threshold is 55; when the sixth turn arrives the context costs 60, and the oldest two units are replaced by the first summary. That summary mentions the date but not `I am Rui`, so the date is safe and the name is not: the block now carries the name, and `recall` is true for both. `dropped` lists the two replaced turns, and no fact, because every fact can still be recalled.

## Constraints

- At most 400 calls per test, at most 200 turns, at most 50 summaries and at most 20 pinned facts.
- `0 <= budget <= 10^5`, `0 <= maxTurns <= 10^3`, `0 <= threshold <= 10^5`, `1 <= keepRecent <= 20`, `-1 <= tokens <= 10^5`. A call id and a fact id have 1 to 20 characters from `a` to `z`, `0` to `9` and `_`. A summary and the text of a fact are non-empty and have at most 100 characters.
- A tool run never has another turn between a call and its result.

## Follow-ups

- The pinned block sits between the summaries and the newest turns, which is the middle of a long context, the place where the paper found models weakest. If recall mattered more than a cache hit, where would you put it, and what would it cost the stable prefix?
- A summary is written by a model and can be wrong. How could the harness check that a pinned fact survived a real summary, and what should it do when the check fails?
- Summaries pile up under the stable policy. Design the rule that merges the oldest two when they pass a limit, and say when it rewrites the prefix.
- Counting tokens with a rule of your own is an approximation of the real count. What breaks when the real count is larger than yours, and how much margin would you keep?

## Hints

### Hint 1

A context window is a budget. Start with the cost of one turn: count its tokens by the rule, add the framing, and keep the number. Then `window` is a walk from the newest turn backwards that stops at the first turn that no longer fits.

### Hint 2

Keep the system turns apart from the rest, since they are always kept and always first. For the others, keep a list in the order they were added, and build the answer by walking it from the end and putting the kept turns back in order.

### Hint 3

Group turns before you cut anything. Make a list of units, where a tool run is one unit holding the numbers of its turns, and let `window` and the compaction work on units. Then there is no way to split a call from its result.

### Hint 4

Keep the live context as a list of items you can rebuild: the system turns, the summaries, the units that are still there. A function that turns this state into the list of rows, and another that adds up their costs, are used everywhere after that.

### Hint 5

Finding how many units to replace is a search. How would you try each possible answer without changing the real state, so that only the winner is kept?

### Hint 6

You do not need to keep every old prompt to measure the prefix. What is the least you must remember between two adds, and what exactly makes two items "the same" for a cache?

### Hint 7

The pinned block depends on what else is in the context, and the context depends on the choice of `k`. Write one function that both pinning and the search for `k` can call, so that the two always agree.
