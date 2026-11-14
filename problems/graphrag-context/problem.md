# GraphRAG Context

## Statement

Build `GraphContext`, the part of a question-answering assistant that prepares the facts a language model will read. The assistant keeps its knowledge as a *graph* of facts, finds the entity a question is about, and has to turn "everything known around this entity" into a short, ordered and traceable piece of text that fits the model's context window. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is GraphRAG?** A language model answers from what it learned in training, which may be old or incomplete. *Retrieval-augmented generation* (RAG) fixes this by fetching relevant information at question time and putting it in the prompt, so that the model can answer from it and cite it. The usual retrieval compares the question with passages of text and takes the most similar passages. One *graph* variant keeps knowledge as facts that connect entities (`ada works_at acme`, `acme based_in paris`), finds the entities named in the question, and fetches the facts around them. That helps with questions that need facts joined together: "in which city does Ada's employer have its office?" needs two facts one step apart, and no single passage may state both. The fetched facts then have to be ranked, because there are usually more than the prompt can hold, cut to a *token budget* (a token is the unit in which a model counts text), and shown with where each came from, so that the answer can cite it. This problem builds those four steps, one per level: the neighbourhood, the ranking, the packing and the citation.

**The graph.** A fact is a *triple* of `subject`, `relation` and `object` (as in the companion problems on facts and triples), with a **weight** (how much the fact is trusted or how salient it is) and a **time** (when it was recorded or last confirmed). The entities are the subjects and objects. Facts have a direction in what they say, but when looking for what is near an entity, a fact links its two entities in both directions: `bob knows ada` is near `bob` and near `ada`.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 55, level 3 by 80 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `GraphContext()`: creates an empty graph.
- An entity or a relation is 1 to 20 characters from `a` to `z`, `0` to `9` and `_`, compared exactly as given and sorted by the numeric value of the characters, so digits come before `_`, which comes before letters.
- `weight` is an integer from 1 to 100, `time` and `now` are integers from 0 to 10^6 (days, but any unit works), `halfLife` from 1 to 10^6, `hops` from 1 to 5 and `budget` from 0 to 10^4.
- Each level's section describes the methods it adds and their parameters.

## Output

Facts come back as rows of text, `[subject, relation, object]` followed by the columns a level adds. Numbers in rows are written in decimal as text. "Sorted" means compared by the numeric value of the characters of each column in turn; a column that is a number is compared as a number.

## Level 1: Facts around an entity

- `addFact(subject, relation, obj, weight, time)`: stores a fact. The identity of a fact is its triple. It returns `true` when the triple is new, and `false` when it is already stored, in which case nothing changes (the weight and the time stay). A relation in the other direction (`b r a` after `a r b`) or another relation between the same entities is a different fact. (The object is called `obj` because some languages reserve `object`.)
- `size()`: the number of facts.
- `egoNetwork(entity, hops)`: the facts within `hops` hops of `entity`, as rows `[subject, relation, object, hop]`, sorted by `hop` and then by subject, relation and object. An *ego network* is the neighbourhood of one node.

**Distance and hops.** The **distance** of an entity from `entity` is the fewest facts in a walk that starts at `entity` and goes from fact to fact through shared entities, in either direction of the facts. `entity` itself is at distance 0. A fact connects its subject and its object. Its **hop** is `1 + min(distance of its subject, distance of its object)`: how many facts a walk crosses to arrive at it, counting itself. A fact is in the ego network when its hop is at most `hops`. A fact touching neither a reachable entity nor `entity` is never in it. For an entity that has no facts the answer is `[]`.

Note how this differs from the usual definition. In social-network analysis an ego network is the induced subgraph of the entities within a radius of the ego (for example, NetworkX's `ego_graph` returns the induced subgraph of the neighbours within a radius), so at radius 1 it includes the ties among the ego's neighbours. Here a fact between two entities that are both at distance `k` has hop `k + 1` and comes one hop later. The difference is deliberate: a context is built from facts that a walk can cross, so a hop is the number of facts crossed to reach a fact, which is also the length of the path that level 4 cites, and a fact that the induced subgraph would include at `k` would have a path of `k + 1` facts.

### Example 1

<!-- case: ex1 -->

`ada` has two facts of her own (`works_at acme` and the one from `bob`), so `egoNetwork("ada", 1)` is those two at hop 1. At 2 hops, the facts of `acme`, `bob` and the other people at `acme` join. At 3 hops the facts of `paris`, and of `carol`, join, among them `paris near carol`: both ends are two facts away from `ada`, so its hop is 3. Adding `ada works_at acme` a second time with other numbers is refused and changes nothing.

### Example 2

<!-- case: ex2 -->

`a` has the facts `a next b` and `a next c` at hop 1. `b next c` joins two entities that are each one fact away from `a`, so its hop is 2, even though both of its ends are already reached. `b next d` and `c next d` reach `d`, also at hop 2. From `d`, the facts that touch `d` come first, and `a next b`, `a next c` and `b next c` follow at hop 2: the first two because one end (`b` or `c`) is one fact away from `d`, the third because both are.

## Level 2: Ranking the facts

Language models do not use every position of a long context equally well: they tend to use the start and the end best and the middle worst (see the explanation's further reading). A budget may also cut the facts at the end, so the facts must come in an order of usefulness that a reader or a cut can rely on. This level scores each fact of the ego network from three signals: how heavy it is, how near it is, and how recent it is.

- `rankFacts(entity, hops, now, halfLife)`: the facts of `egoNetwork(entity, hops)` as rows `[subject, relation, object, hop, score]`, best first.

The **score** is an integer, with no rounding:

- `hopFactor = 16 >> (hop - 1)`, which is 16, 8, 4, 2, 1 for hops 1 to 5: each extra hop halves it.
- `age = max(0, now - time)`, so a fact from the future is as fresh as one from now.
- `steps = min(4, floor(age / halfLife))`: the number of whole half-lives, at most 4.
- `recencyFactor = 16 >> steps`, which is 16, 8, 4, 2, 1: each whole half-life halves it, and a fact older than 4 half-lives is not penalised further.
- `score = weight * hopFactor * recencyFactor`.

(`x >> k` is `x` halved `k` times, in whole numbers; here it is exact.) The order is: higher score first; equal scores, the smaller `hop` first; then subject, relation and object as text.

The score shows a design choice, not a law. A real system might decay with a smooth curve and combine the signals with learned weights. Here the halving steps keep every score an exact integer, so that two correct programs always agree, and make the effect of each signal easy to read.

### Example 1

<!-- case: ex3 -->

With `now` 100 and a half-life of 10 days, `ada works_at acme` is heavy (90), one hop away and 2 days old: `90 * 16 * 16 = 23040`. `bob knows ada` has weight 60 but is 10 days old, one half-life: `60 * 16 * 8 = 7680`. `carol works_at acme`, at hop 2, is still ahead of it because it is fresh: `70 * 8 * 16 = 8960`. A fact 50 days old, `acme based_in paris`, has taken the 4 halvings: `80 * 8 * 1 = 640`.

### Example 2

<!-- case: ex4 -->

A fact from the future (`a s d` has time 500 when `now` is 40) has age 0 and so the best recency factor. `q t e` is brand new but weighs only 7, while `q r b` weighs 100 and is 40 days old, four half-lives of 10 days: `100 * 16 * 1 = 1600` against `7 * 16 * 16 = 1792`. Asked again with `now` 400 and a half-life of 100, `q r b` and `q r a` (time 0) have taken the four halvings and `q t e` (age 360) three, so it falls to the bottom. With `now` 0 and a half-life of 1 no fact has any age, and weight and hop decide alone.

## Level 3: Filling a token budget

The facts have to fit the model's window. A **token** is the unit in which the model counts its input. Real tokenizers split text in model-specific ways; here the size of a fact is fixed by a simple rule, so that it is exact.

- `tokens(fact) = ceil(c / 4)`, where `c` is the number of characters in the three names plus 2 (the two spaces in `subject relation object`). A fact of 8 characters in all is 2 tokens, one of 9 is 3.
- `buildContext(entity, hops, now, halfLife, budget)`: chooses facts for a context of at most `budget` tokens and returns them as rows `[subject, relation, object, hop, score, tokens]`, in the order of the ranking of level 2.

The choice is **greedy**: go through the ranked facts once, in order. Take a fact when its tokens are at most the tokens still left, and subtract them; otherwise skip it and carry on, since a smaller fact further down may still fit. A fact larger than the whole budget is never taken, and `budget` 0 gives `[]`. Nothing is stored: asking again gives the same answer, and the facts added since are taken into account.

Greedy is not optimal: a different choice can reach a higher total score within the same budget (the exact choice is a knapsack problem). It is a common choice, since the order says why each fact is in or out, and the fill can stop as soon as the budget is gone.

### Example 1

<!-- case: ex5 -->

The ranking of level 2 is `ada works_at acme` (5 tokens), `carol works_at acme` (5), `bob knows ada` (4), `bob likes tea` (4), `acme based_in paris` (5). With 14 tokens the first three fit exactly. With 12, the third no longer fits and nothing after it does. With 9 tokens, the second fact (5) does not fit in the 4 left, and is skipped, and the third (4) does. With 3 tokens nothing fits.

### Example 2

<!-- case: ex6 -->

The count is by characters, rounded up: `aa bb cc` is 8 characters and 2 tokens, `aaa bb cc` is 9 and 3 tokens, `aaaa bbbb cccc` is 14 and 4 tokens, and the shortest possible fact, `a b c`, is 5 characters and 2 tokens. All have the same weight and time, so they have the same score.

## Level 4: Paths and rendered context

A fact in a context is more useful when the reader can see how it connects to the question. Each fact gets a **path**: the facts that lead from the query entity to it. This is what a citation is made of: "this fact, reached from `ada` by way of `works_at acme`".

- `explain(entity, subject, relation, obj)`: the path to the stored fact `subject relation obj`, as the rows `[subject, relation, object]` of the facts to cross, in order from the entity, the fact itself last. `[]` when the fact is not stored, or `entity` has no facts, or the fact cannot be reached from `entity`.
- `renderContext(entity, hops, now, halfLife, budget)`: the context as text, built from the facts of `buildContext` with the same arguments.

**The shortest path, and which one.** Use the distances of level 1. Every entity `v` other than `entity` has exactly one **parent step**: among the entities `u` linked to `v` by a fact and at distance `distance(v) - 1`, take the one whose name is smallest, and between `u` and `v` the smallest fact (by subject, relation and object). The path to `v` follows the parent steps back to `entity`. For a fact, the path goes to the endpoint of the fact that is nearer to `entity` (when both are as near, the one with the smaller name) and then crosses the fact itself. Its length equals the fact's hop. A fact that touches `entity` has a path of just itself.

The tie-break makes one correct answer out of several equally short ones, which is what a citation needs: the same fact must always point to the same path.

**The text.** One line of header, then one line for each fact in the order of `buildContext`, joined with a single newline and with no newline at the end:

```
Context for <entity> (<n> facts, <used> of <budget> tokens)
[1] <subject> <relation> <object> | path: <path>
[2] ...
```

`<n>` is the number of facts chosen (the word is always `facts`), `<used>` the sum of their tokens, `<budget>` the budget given. `<path>` starts with the entity, and then each fact of the path is written as it is crossed from the entity's side: ` -<relation>-> <object>` when the walk is at the subject, ` <-<relation>- <subject>` when it is at the object. A fact whose subject and object are the same entity is crossed with the first form. With no fact chosen, the text is the header alone. The budget caps only the fact lines; the paths are provenance and are not counted.

### Example 1

<!-- case: ex7 -->

`paris near carol` joins `paris` and `carol`, both two facts from `ada`; the nearer end with the smaller name is `carol`, reached through `acme`, so the path is `ada works_at acme`, `carol works_at acme`, `paris near carol`. A fact next to `ada` is a path of one. A fact that is not stored has no path. From `france` the path to `bob likes tea` crosses `paris`, `acme`, `ada` and `bob`, one fact each, and then the fact.

### Example 2

<!-- case: ex8 -->

The first context holds the three facts of the example at level 3. In the path of the second fact, `ada -works_at-> acme` is followed by `<-works_at- carol`, since `carol works_at acme` is crossed from its object. With a budget of 1 nothing fits, and only the header is returned. An entity that has no facts also gives only the header.

## Constraints

- At most 2000 calls per test and at most 1000 facts.
- Scores are exact integers below 10^6. A graph may have cycles, parallel facts between two entities, and facts whose subject and object are the same.
- A path is at most 5 facts long when asked through `renderContext`; `explain` can be asked about any stored fact and its path can be longer.

## Follow-ups

- The neighbourhood is cut by a number of hops. A hub with thousands of facts floods the context at hop 1. How would you cap what a hub contributes, and what ranking signal would you add to prefer specific facts over generic ones?
- Some systems also precompute *communities* of densely connected entities, write a summary of each, and retrieve summaries for broad questions ("what are the main themes?") where the facts around one entity are not enough. What would you store, and when would a summary be stale?
- Here a fact costs the same whether or not its path is printed. A real context also pays for the path text and the numbering. How would you make the budget cover them, and how does that change the greedy fill?
- Greedy fills by score order and can miss the choice with the highest total score. When would you pay for an exact knapsack choice, and what would a "diversity" rule (no two facts about the same pair) cost in score?
- The same fact can be reached by two paths of the same length. If the entity's neighbours change, the cited path can change too. What would you store with a fact to keep a citation stable?

## Hints

### Hint 1

A graph is just a list of facts, and "near" means "reachable in few steps". Start by answering one question: given an entity, which entities are one step away? Those are the ones that share a fact with it. Then ask the same of those, and keep track of how many steps it took to reach each entity. A queue handles this: take an entity off the front, look at its facts, and put every entity you have not seen yet at the back, one step further.

### Hint 2

Keep a dictionary from each entity to the list of facts that mention it, so that "the facts of this entity" is one lookup. A fact that mentions the same entity twice (a fact about itself) should be in the list once.

### Hint 3

A fact belongs to the network by its nearer end. Once you have the distance of every entity, compute for each fact `1 + min(distance of subject, distance of object)`. An entity you never reached has no distance: leave it out of the `min`, and a fact where neither end was reached is not in the network.

### Hint 4

The score is a product of three integers. Work out each factor in a small function, using whole-number division and a shift, and test them on the values of the example (`23040`, `7680`, `8960`, `640`). Sort with one comparison that holds all four keys: score (largest first), hop, and the three names.

### Hint 5

Filling the budget is one pass over the sorted list with a counter of tokens left. Do not stop at the first fact that does not fit. Compute the tokens of a fact with integer arithmetic: `(characters + 3) // 4`.

### Hint 6

For the path, run the breadth-first search again from the entity, and for each entity remember its distance. The parent of an entity is found by looking at its facts, keeping those whose other end is one step closer, and choosing the smallest name, then the smallest fact. Follow the parents back to the entity, then reverse the list.

### Hint 7

To write the path, walk it from the entity and keep the entity you are standing on. For each fact, if you are standing on its subject, write the forward arrow and move to its object; otherwise write the backward arrow and move to its subject.
