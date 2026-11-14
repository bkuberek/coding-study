# GraphRAG Context: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| bfs-rank-fill | optimal | O(V + E + F log F) per query | O(V + E) | default answer; each level adds one stage to the same pipeline |

Here `V` is the number of entities, `E` the number of stored facts and `F` the number of facts inside the hop limit.

## How the design grows level by level

| Level | Change | What the pipeline adds |
|-------|--------|------------------------|
| 1 | The neighbourhood | An index from entity to the facts that mention it, and a breadth-first search for distances |
| 2 | The ranking | A score made of three integer factors and a sort on one composite key |
| 3 | The budget | A single pass over the sorted list with a counter of tokens left |
| 4 | The citation | A second use of the same distances: a parent step per entity, followed back to the query entity, and a text format |

The early choice that matters is to run one breadth-first search per query and to reuse its distances for the hop of every fact, and later for every path. Level 4 then adds no new search of the graph, only a rule for choosing among equally short ways in.

## Approach: bfs-rank-fill (Breadth-first distances then one ranked list then a greedy fill)

### Intuition

A query is a pipeline: find what is near, order it, take as much as fits, and say how each piece is connected. Every stage consumes the output of the one before. The distance of each entity from the query entity is computed once. It gives the hop of each fact (level 1), the distance factor of its score (level 2), and the shortest path to it (level 4). The ranking is a sort, the packing is a greedy walk down the sorted list, and the citation is a walk back up the breadth-first tree.

### Algorithm

1. Keep `facts`, a map from the triple to its weight and time, and `incident`, a map from each entity to the facts that mention it (once each, also for a fact about one entity).
2. `egoNetwork`: run a breadth-first search from the entity over `incident`, treating every fact as a link between its two ends in both directions. The hop of a fact is `1 + min(distance of subject, distance of object)`, counting only the ends that were reached. Keep the facts with a hop of at most `hops`, and sort by hop and then by the three names.
3. `rankFacts`: for each fact compute `hopFactor = 16 >> (hop - 1)`, `steps = min(4, floor(max(0, now - time) / halfLife))`, `recencyFactor = 16 >> steps` and `score = weight * hopFactor * recencyFactor`. Sort by the key `(-score, hop, subject, relation, object)`.
4. `buildContext`: walk the ranked list with `remaining = budget`. Take a fact when `tokens <= remaining`, with `tokens = ceil((len(subject) + len(relation) + len(object) + 2) / 4)`, and subtract; otherwise go on to the next.
5. `explain`: take the distances from the entity. The parent step of an entity `v` is the pair (smallest neighbour name at distance `d - 1`, smallest fact between them). Find the nearer end of the fact (ties by name), follow parent steps back to the entity, reverse, and append the fact.
6. `renderContext`: build the header from the chosen facts and the sum of their tokens, then one line per fact with its path written from the entity: forward arrow when standing on the subject, backward arrow when standing on the object.

### Correctness

Distances: breadth-first search from the entity visits the entities in order of distance, so the first time an entity is reached is by a shortest walk. Treating each fact as a link in both directions makes the walk follow the statement's definition.

Hops: a fact is crossed on a walk from the entity as soon as one of its ends is reached, so the fewest facts needed to arrive at it is the distance of its nearer end plus one (the fact itself). A fact whose ends are both unreached cannot be crossed.

Ranking: the score is a pure function of the fact, its hop and the query numbers, and the sort key is a total order (the names break every tie), so the output is unique.

Packing: the loop takes a fact exactly when the statement does, and `remaining` only goes down, so the sum of the tokens never exceeds the budget. Skipping a fact never changes the facts examined after it, only the counter.

Paths: the parent of each entity is defined by a rule that depends on the entity alone (its distance and its neighbours), so the path to an entity is the same whichever fact led there. Every step reduces the distance by one, so the walk ends at the entity after `distance` steps, and with the fact itself the path has `hop` facts. The nearer end is chosen as the statement says, and the final fact never appears in the chain to its own nearer end, because that end has no neighbour closer to the entity through the fact.

### Complexity

- Time: O(V + E + F log F) per query — the search visits each entity and fact once; scoring is constant per fact; the sort is on the `F` facts in range; the packing and the paths add a walk of at most `hops` steps per chosen fact.
- Space: O(V + E) — the index and the distances; the ranked list holds at most `E` entries.

### Trade-offs

- Running the search per query keeps the graph free of precomputed state and is fast for a few hops; for a graph with millions of facts a hub at hop 1 can still pull in a large part of it, so real systems cap the facts a node contributes or use a ranking that prefers specific relations.
- The score is a product of three factors and each halving is an integer shift, which keeps every score exact and the order identical in every language. A smooth exponential decay and learned weights would rank better, at the price of floating point ties and of a score that cannot be checked by hand.
- Greedy filling is simple and explainable, and may miss the choice with the highest total score within the budget, which an exact knapsack solution finds. Because a fact that does not fit is skipped rather than ending the fill, a small fact lower in the ranking can use the space that a larger one could not.
- The budget here counts the facts only, and not the paths or the numbering. That keeps the facts and their citations independent of each other. A system that counts everything the model reads must fill the budget with the rendered lines instead, and then the path length changes what fits.
- Community summaries (clusters of densely connected entities, each summarised in text) answer broad questions that no single entity's neighbourhood can. They are outside this problem, which only retrieves and cites individual facts.

### Pitfalls and edge cases

- Level 1: the hop is decided by the nearer end, so a fact between two entities at the same distance `k` comes at `k + 1`, not at `k`. Direction does not matter for distance. A fact about one entity (subject equal to object) is stored once in the index, and has a hop of one more than the distance of that entity. A repeated triple changes nothing, not even the weight. A fact in the reverse direction is a different fact. An entity with no facts has an empty network.
- Level 2: `age` is clamped at 0, so a future fact is not penalised. `steps` is the integer part of `age / halfLife`: 9 days with a half-life of 10 is none, 10 is one. After 4 halvings the factor stops falling. Ties go to the nearer fact, then to the names, so equal scores from different hops are not a coin toss. Do not float the division: use integer division.
- Level 3: the token count is a ceiling: 8 characters are 2 tokens and 9 are 3. A fact larger than the budget is skipped, and so is one larger than what is left, and the walk goes on. A budget of 0 gives an empty list. The tokens are those of the fact alone.
- Level 4: the parent is the smallest neighbour name at the previous distance, and then the smallest fact between the two, which may be a fact in either direction. For a fact between two entities of the same distance, the path goes through the one with the smaller name. A fact that cannot be reached, or is not stored, has an empty path. The arrow shows the direction in which the fact was stored, not the direction of the walk. The text has no trailing newline, and a context without facts is only its header.

### Language notes

- Python: `x >> k` and `//` on non-negative integers give the exact values of the statement, and tuples compare lexicographically, so `(-score, hop, fact)` is the whole sort key and `(name, fact)` the whole parent choice. `-(-n // 4)` is a ceiling without floats.
- TypeScript: `>>` works on 32-bit integers, which is enough for factors up to 16. `Math.ceil` and `Math.floor` on exact quotients are safe here, since the numbers are small integers. Comparators chain with `||` and compare text with `<` and `>` (code unit order), not `localeCompare`. A `Map` keyed by a joined string stands for the triple.

## Further reading

- P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", NeurIPS 2020, arXiv:2005.11401: the idea of fetching passages at question time and giving them to a generator.
- [Breadth-first search](https://en.wikipedia.org/wiki/Breadth-first_search): the traversal that gives distances in an unweighted graph, and the tree of parents used for paths.
- V. A. Traag, L. Waltman and N. J. van Eck, "From Louvain to Leiden: guaranteeing well-connected communities", Scientific Reports 9:5233, 2019, doi:10.1038/s41598-019-41695-z: community detection, the first step of the community summaries mentioned above (not implemented here).
- M. E. J. Newman, "Networks", 2nd edition, Oxford University Press, 2018, doi:10.1093/oso/9780198805090.001.0001: a textbook on networks, with community detection among its topics.
- N. F. Liu et al., "Lost in the Middle: How Language Models Use Long Contexts", Transactions of the Association for Computational Linguistics 12:157-173, 2024, doi:10.1162/tacl_a_00638: how the position of information in a long context affects its use, which is why the order of the facts matters.
- [NetworkX `ego_graph`](https://networkx.org/documentation/stable/reference/generated/networkx.generators.ego.ego_graph.html): the usual ego network as an induced subgraph of the neighbours within a radius, which level 1 deliberately does not follow.
- S. Martello and P. Toth, "Knapsack Problems: Algorithms and Computer Implementations", Wiley, 1990: the exact alternative to a greedy fill.
