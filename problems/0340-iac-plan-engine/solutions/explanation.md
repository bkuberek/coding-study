# Infrastructure Plan Engine: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| step-graph | optimal | O(R (R + E) + S log S) per plan or apply, for R resources, E references and S attribute rows | O(R K + E) for K keys per resource | default answer; one graph of steps serves the plan, its order and the apply |

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Classify and diff | two maps from address to attributes, desired and actual; a plan is a sorted pass over their union |
| 2 | References, errors and order | the recorded links of the actual state; a plan resolves values in dependency order, and each step becomes a node with before-rules as edges |
| 3 | Replace and unknown values | the forced keys, the computed keys and the marks; the action of a resource is decided while resolving, since it changes what references to it mean |
| 4 | Apply | a map of old objects with their links; apply walks the ordered nodes and gives each an outcome |

The choice that keeps the later levels cheap is to make the order a graph from level 2 on, instead of sorting by a fixed key. Level 1's "deletes last, by address" is then just the smallest-first order of a graph with no edges, and levels 3 and 4 only add nodes and edges: the two halves of a replace, the delete of an old object, and rules 3 and 4.

## Approach: step-graph (Resolve in dependency order, then place the smallest ready step)

### Intuition

A plan has two jobs: decide what happens to each resource, and decide in which order. The first depends on resolved values, and a value can depend on another resource's action: a reference to the identifier of a resource that is being replaced is unknown. So the actions are decided in dependency order, where everything a resource refers to has been decided before it. The second job is a topological sort, but of steps rather than resources, because a replace is two steps that can sit far apart, and the order must be one fixed answer. Taking, at each position, the smallest step whose predecessors are all placed gives that one answer, and a heap makes it cheap.

### Algorithm

1. Level 1: for each address in the union of the two maps, take the action from membership and from comparing the attribute maps. The attribute rows walk the union of keys in sorted order. Steps that are not deletes come first by address, then deletes by address.
2. Level 2: collect the references of every desired attribute. A reference whose target is not desired, or does not declare the key, is an error row. Among the others, find for each resource the set it can reach; a resource that reaches itself is on a cycle, and the resources that reach each other form a group. If there is any error, return the rows.
3. Order the desired resources so that each comes after the targets of its references (Kahn's algorithm). Walk that order and resolve each attribute: a plain value is itself, a reference takes the target's resolved value, which is already known.
4. Make one node per step, with rank 0 for the steps that are not deletes and 1 for deletes. Add an edge for each before-rule: target before user for each reference, and dependent delete before the delete it was built on. Keep a count of incoming edges per node, push the nodes with no incoming edge onto a heap keyed by rank and address, and repeatedly pop the smallest, append it with its attribute rows, and push each successor whose count drops to zero.
5. Level 3: while resolving in dependency order, a reference to a computed key is `<unknown>` if its target was created or replaced, and the target's actual value otherwise. Compare the resolved values with the actual attributes minus the computed keys. If a differing key is forced for the type, the action is a replace: the create node keeps the rank-0 slot, a delete node is added, and rule 3 links them in the order the mark asks for. Before building the steps, walk the dependencies from every marked address to spread the mark. Rule 4 adds an edge from the step of each recorded user to every delete that is not the delete of a delete-first replace.
6. Level 4: build the same nodes and edges, then walk them in order. A node whose predecessors did not all end `ok` is skipped; otherwise it fails if listed and succeeds if not. A success writes to the actual state at once, resolving references against that state, so a reference to a computed key reads the value the cloud just picked. The create of a create-first replace moves the current object, with its links, into a map of old objects; the delete of that replace, like the delete of an old object, removes it from there. Every old object becomes a rank-1 delete node in the next plan, kept apart from the delete of the current object, so an address can have two deletes; rule 5 puts the old object's first, and before the create of a new replace.

### Correctness

Classification: an address is in exactly one row of the table, and an update has at least one differing key, so every address gets exactly one action, and the attribute rows of an update are exactly the keys on which the two maps disagree.

Resolution: the dependency order puts every target before its users, so when a resource is resolved, each target's values and action are final. A chain of references is followed by induction along that order. An action can depend only on the actions of targets, which are already decided, so deciding in that order never needs a value that is not known.

Cycles: a resource is on a cycle exactly when it can reach itself, and mutual reachability is an equivalence on those resources, so the groups are well defined and do not depend on the order of the search. A resource that only reaches a group cannot be reached back from it, so it is in no group.

Order: Kahn's algorithm with a priority queue outputs a node only when all its predecessors are output, so every rule holds. At each position it outputs the smallest node among those that may come next, which is the definition of the order in the statement, so the order is unique. When no rules exist, every node is ready from the start and the heap yields rank 0 by address, then rank 1 by address, which is level 1's order.

The mark: if a marked `Y` depends on `X` and `X` were replaced delete-first, rule 1 would put `X`'s create before `Y`'s create, rule 3 would put `X`'s delete before `X`'s create and `Y`'s create before `Y`'s delete, and rule 2 would put `Y`'s delete before `X`'s delete: a circle. Spreading the mark along dependencies makes `X` create-first, which reverses its rule 3 edge and breaks the circle.

Apply: since a node runs after all its predecessors, the outcome rule carries a failure downstream through any number of steps: a skipped node skips its own successors. The state after the walk is the starting state plus the effects of exactly the successful steps, so a new plan compares the desired state with what really happened. An old object stays recorded until a delete of it succeeds, so it cannot be leaked: rule 5 runs its delete before a second create-first replace of the address, and if that delete fails or is skipped, the new create is skipped too, so a new old object never overwrites the first. Rule 4 orders the delete after every recorded user has moved, except when the address is replaced again, where the users can only move to the resource that rule 5 creates later.

### Complexity

- Time: O(R (R + E) + S log S) per plan or apply, for R resources, E references and S attribute rows — finding the cycle groups searches from every resource, O(R + E) each; the dependency order and the step order are heap-driven topological sorts over O(R) nodes and O(R + E + L) edges for L recorded links; sorting the attribute rows costs O(S log S).
- Space: O(R K + E) for K keys per resource — the maps of attributes, the resolved values, the nodes and their edge lists.

### Trade-offs

- Reachability from every resource is quadratic. Tarjan's strongly connected components find the same groups in one linear pass; with at most 40 resources the simpler search is fast and easy to check.
- A heap keyed by rank and address makes the order unique, which a person reading the plan and a test both need. A real engine runs independent steps at the same time and only promises that the before-rules hold.
- Resolving references against the recorded state, as here, keeps the plan pure but can be stale. Reading every resource from the cloud first (a refresh) gives a truer plan at the cost of many API calls.
- One old object per address, deleted before any new replace of it, keeps the plan's rows and the failures unambiguous. The cost is that, when the address is replaced again, its users still point at the old object when it goes. A tool that keeps a list of old objects, each with an identifier, can let them wait for the users instead.

### Pitfalls and edge cases

- `desire` and `observe` replace the attributes of an address; merging keeps keys that were removed (hidden case `h2`).
- Deletes come after every other step, whatever their address (`h3`), and an extra actual key makes an update (`h5`).
- Sort by character code: `web10` precedes `web9`, and `.` precedes `_` (`h1`).
- Compare resolved values, never the reference text (`h6`), and resolve to the desired value of the target, not its actual one (`h11`).
- Take the smallest ready step, not the shallowest: a lone resource with a large address waits to the end (`h7`).
- A reference to a resource that is only actual points nowhere, a self-reference is a cycle of one, and a reference that points nowhere closes no cycle (`h8`, `h9`).
- Computed keys are never compared, take their place in key order on a create, and are listed by a plain delete (`h12`). Only references to computed keys of a replaced resource become unknown, and the unknown passes on through a chain (`h14`).
- Adding or removing a forced key forces a replace too, and only the forcing rows carry the marker (`h13`).
- The mark spreads to what a marked resource depends on, not to its dependents (`h15`), and it spreads even from a marked resource that is only created (`h18b`). Without rule 4, an old resource can go before a user that waits behind another replace (`h16`).
- In apply, a skipped step skips its own successors (`h21`); values are resolved when the step runs, not copied from the plan, which held `<unknown>` (`h23`); and the links that apply records drive the order of later deletes (`h24`). An address with an old object can have two deletes, the old object's first (`h25`), and a second create-first replace deletes the old object before it creates, so nothing is overwritten (`h26`).

### Language notes

- Steps are small objects with lists of successors and a count of predecessors. Python and TypeScript push tuples or keep a sorted ready list; Java and Kotlin use a `PriorityQueue` with a comparator on rank and address; Go implements `container/heap`; Rust wraps the key in `Reverse` inside a `BinaryHeap`.
- Sorting compares strings by code point in Python, by UTF-16 unit in TypeScript, Java and Kotlin, and by byte in Go and Rust; all agree on printable ASCII, which the statement fixes.
- The values of computed keys and the plan rows of variable length are lists of strings in every language; Go and Rust build them as slices and vectors and copy them out, so the caller never holds the engine's own maps.
- `type` is a keyword in Go and Rust and shadows a built-in in Python, which is why the parameter is `resourceType`.

## Further reading

- [Resource Behavior, OpenTofu documentation](https://opentofu.org/docs/language/resources/behavior/): create, destroy, update in place, destroy and re-create; references as implicit ordering; `create_before_destroy` and its spread to dependencies.
- A. B. Kahn, "Topological sorting of large networks", Communications of the ACM 5(11), 1962, pp. 558-562 ([doi:10.1145/368996.369025](https://doi.org/10.1145/368996.369025)): the in-degree algorithm behind both orders here.
- R. Tarjan, "Depth-First Search and Linear Graph Algorithms", SIAM Journal on Computing 1(2), 1972, pp. 146-160 ([doi:10.1137/0201010](https://doi.org/10.1137/0201010)): strongly connected components in linear time, the faster way to find the cycle groups.
