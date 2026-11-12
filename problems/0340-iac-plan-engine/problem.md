# Infrastructure Plan Engine

## Statement

Build `PlanEngine`, the part of an infrastructure tool that works out what to change. You write down the servers, networks and disks you want, the engine compares that description with what exists, and it prints a **plan**: the steps that would turn what exists into what you want. Later levels order the steps, decide when a change needs a brand-new resource, and finally carry the plan out against a simulated cloud whose calls can fail. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**The words.** A **resource** is one thing the tool manages: a server, a network, a DNS record. It has a **type** (`server`), a **name** that is unique within its type (`web`), and **attributes**, pairs of a **key** and a **value** (`size = large`). Its **address** joins type and name with a dot: `server.web`. The **desired state** is the set of resources you want, as you wrote them down. The **actual state** is the set of resources that exist, as the tool last saw them. A plan is the difference between the two: create what is desired and missing, delete what exists and is no longer desired, update what exists with other attributes, and leave alone what already matches. Leaving a resource alone is called a **no-op** ("no operation").

**Why plan first.** Changing infrastructure is slow, costs money and can destroy data, so a careful tool shows the plan before it touches anything, and a person reads it. Planning only reads. Carrying out a plan and then planning again should find nothing left to do: every resource is a no-op. That property, where doing something a second time changes nothing more, is called **idempotence**, and it is what lets a team apply the same description again and again without fear.

Aim to finish in 150 minutes. A good split: read the statement in the first 15 minutes, then finish level 1 by about minute 40, level 2 by 75, level 3 by 110 and level 4 by 140, keeping the last minutes for a final run.

## Input

- `PlanEngine()`: creates an engine whose desired and actual states are empty.
- An **address** is `type.name`. A type, a name and a key are each 1 to 20 characters: lowercase letters, digits and `_`, starting with a letter.
- A **value** is 1 to 40 printable ASCII characters (codes 33 to 126, so no space), and never the text `<unknown>`.
- `attributes` is a list of `[key, value]` pairs with distinct keys. Their order means nothing.
- Each level's section describes the methods it adds and their parameters.

## Output

Methods that change the engine return a `bool`. `plan` and the later reports return **rows**: each row is a list of strings, in the order its level specifies. Where something is "sorted", texts are compared by the numeric value of their characters, so digits come before `_`, `_` before lowercase letters, `.` before all of them, and `web10` before `web9`.

## Level 1: Desired versus actual

- `desire(address, attributes)`: declares that the resource should exist with exactly these attributes. It returns `true` when the address was not desired, and `false` when this declaration replaces an earlier one: the earlier attributes are forgotten, not merged.
- `remove(address)`: takes the resource out of the desired state. It returns `true` when it was desired and `false` when it was not.
- `observe(address, attributes)`: records that the resource exists with exactly these attributes. It returns `true` and `false` as `desire` does, for the actual state.
- `plan()`: compares the two states and returns the plan. It changes neither state, so asking twice gives the same plan.

Every address in either state gets one **action**:

| Desired | Actual | Action |
|---------|--------|--------|
| yes | no | `create` |
| no | yes | `delete` |
| yes | yes, with the same attributes | `no-op` |
| yes | yes, with different attributes | `update` |

Two resources have the same attributes when they have the same keys with the same values. Values are compared exactly as text: `Large` and `large` differ, and so do `10` and `010`.

**The rows.** Each resource gives one **step row**, `[action, address]`, followed by its **attribute rows**, sorted by key:

- `["+", key, value]`: the key is new. A create lists every desired attribute this way.
- `["-", key, value]`: the key goes away. A delete lists every actual attribute this way.
- `["~", key, old, new]`: the value changes.

An update lists only the keys that differ: a key that is only desired is a `+` row, a key that is only actual a `-` row, and a key with two different values a `~` row. A no-op has no attribute rows.

**The order.** First the steps that create, update or leave alone, sorted by address; then the deletes, sorted by address. In this problem deletes go last, so that whatever replaces a resource is in place before it goes.

### Example 1

<!-- case: ex1 -->

`dns.www` exists with the same attributes, given in another order, so it is a no-op. `network.main` is created, with a `+` row for each key. `server.web` is updated: `owner` exists but is not desired, `size` changes, and `tag` is new; `image` is the same and gets no row. `disk.old` is no longer desired, so it is deleted, and it comes last although `disk` sorts before the others.

### Example 2

<!-- case: ex2 -->

The second `desire` of `app.api` returns `false` and replaces the first one, so the plan compares port `9090`, not `8080`. Planning twice gives the same plan. When `app.api` is observed again with only a port, its `replicas` key is gone from the actual state, and the plan adds it back.

## Level 2: References and dependencies

Resources depend on each other: a subnet lives in a network, and a server needs the subnet's identifier. Instead of copying a value by hand, an attribute can **refer** to an attribute of another desired resource.

- A value of the form `${type.name.key}` is a **reference**: its value is the value of attribute `key` of the desired resource `type.name`. The reference is always the whole value, never mixed with other text, and the three parts follow the rules for types, names and keys. The referenced attribute can be a reference too: follow the chain to a plain value. That plain value is the **resolved** value, and the plan compares and prints resolved values, never the reference text.
- A resource that refers to another **depends on** it.
- `observeDependency(address, dependsOn)`: records that the actual resource `address` was built on top of the actual resource `dependsOn`: a disk attached to a server, a server inside a network. It returns `true` when this link is new, and `false` when it was already recorded or either address is not in the actual state, in which case nothing changes. A new `observe` of a resource keeps its links. The recorded links never form a loop.

**Errors.** A description can be broken. When it is, `plan` returns only error rows, and no steps:

1. `["error", "unknown-reference", address, key, target]` for each attribute whose reference points nowhere: `type.name` is not desired, or it is desired without the key. `target` is the text between `${` and `}`. These rows come first, sorted by address, then key.
2. `["error", "cycle", address1, address2, ...]` for each group of resources that depend on themselves. A resource depends on itself when following references from it, one or more times, leads back to it; a resource that refers to its own attribute does so at once. Two such resources are in the same group when each depends on the other, directly or through others. The addresses in a row are sorted, and the rows are sorted by their first address. A resource that depends on a group without being in it belongs to no group. A reference that points nowhere takes no part in this.

**The order with rules.** Each step row is now a **step**, and **before-rules** say that one step must come before another:

1. When `Y` depends on `X`, the step of `X` comes before the step of `Y`: a resource is created or updated after what it refers to, which also gives the order in which values resolve.
2. When the actual `Y` was recorded as built on `X` and both are deleted, the delete of `Y` comes before the delete of `X`: deletes go in the reverse order.

Each step has a **rank**: 0 for a step that is not a delete, 1 for a delete. The plan places the steps one at a time: among the steps whose earlier steps, under the rules, are all placed, it takes the one with the smallest rank, and among those the smallest address. Without rules this is the order of level 1.

### Example 1

<!-- case: ex3 -->

`app.web` refers to `db.main`, which refers to `net.core`, so they come in that order, although `app` sorts first. `cache.edge` depends on nothing, so it goes first. `db.main` resolves its `net` to `core`, which is its actual value, so it is a no-op. The `+` row of `app.web` shows the resolved `db-1.internal`. `vm.legacy` was built on `disk.legacy`, so it is deleted first.

### Example 2

<!-- case: ex4 -->

`db.main` is not desired, and `app.web` has no `port`, so two references point nowhere. `queue.a` and `queue.b` refer to each other: a cycle. The first plan is only errors. Once they are fixed, `lb.front` resolves `target` to `80` and follows `app.web`, and `queue.a` follows `queue.b`.

## Level 3: Replacement and unknown values

Some attributes cannot change on a resource that exists: a network's address range, the zone of a disk. Changing one means deleting the resource and creating a new one, which is a **replace**. And some attributes are chosen by the cloud when it creates a resource, such as its identifier, so no one knows them before.

- `forceReplacement(resourceType, key)`: from now on, a change of `key` on any resource of type `resourceType` forces a replace. It returns `true` when this is new and `false` when it was declared before.
- `computed(resourceType, key)`: from now on, `key` is **computed** for the type `resourceType`: the cloud sets it when it creates a resource of that type. It returns `true` and `false` like `forceReplacement`. A desired resource never declares a computed key, and every actual resource has a value for each computed key of its type.
- `createBeforeDestroy(address)`: marks the address so that, when its desired resource is replaced, the new one is created before the old one is deleted. Without the mark a replace deletes first. It returns `true` when the mark is new and `false` when it was there.

**Comparing.** Computed keys are left out when desired and actual are compared: they belong to the cloud.

**Unknown values.** A reference may name a computed key of the target's type, although the desired target does not declare it. Such a reference resolves to `<unknown>` when the target is created or replaced, since the cloud has not chosen the value yet, and otherwise to the target's actual value, since an update keeps computed values. A reference to any other key resolves as in level 2. `<unknown>` differs from every value, so a resource with an unknown value always changes.

**Replace.** A resource that is desired and actual is replaced when one of its differing keys is forced for its type; otherwise its action is as before. Since whether a resource is replaced decides what its references resolve to, decide the actions in an order where each resource comes after what it refers to. A replace gives two steps:

- `["delete", address, "replace"]`, with no attribute rows, and `["create", address, "replace"]`, which carries the attribute rows: the differing keys as for an update, plus a row for each computed key of the type, whose new value is `<unknown>`. Every row of a key that forces the replace ends with one more string, `"forces-replacement"`.
- A plain create also lists each computed key of its type, as `["+", key, "<unknown>"]`. All attribute rows stay sorted by key.

A replace ripples: whatever refers to the identifier of a replaced resource gets `<unknown>`, so it changes too, and is replaced as well when that key forces it.

**More before-rules.** Rule 1 applies to the create of a replace, and rule 2 to the delete of a replace as well as to plain deletes.

3. A replace without the mark deletes, then creates: its delete comes before its create. With the mark, its create comes before its delete.
4. When the actual `Y` was recorded as built on `X`, `Y` has a step that is not a delete, and `X` has a delete that is not the delete of a replace without the mark, then that step of `Y` comes before the delete of `X`: `Y` stops using the old `X` before it goes.

**The mark spreads.** The mark spreads from a desired marked resource to every resource it depends on, directly or through others, even when the marked resource itself is not replaced: any of them that is replaced creates first too. Without this, rules 1 to 4 can ask two steps to wait for each other. On an address that is not desired, the mark does nothing.

### Example 1

<!-- case: ex5 -->

`network.main` is created, so its computed `id` is listed as `<unknown>`, and `server.web`, which refers to it, gets `<unknown>` too. `network.vpc` exists: its `id`, `net-7`, is not compared, so it is a no-op, and `server.db` resolves its reference to `net-7`. Only `size` changes on `server.db`.

### Example 2

<!-- case: ex6 -->

The new range forces a replace of `network.main`. Its new `id` is unknown, so the `network` key of `subnet.a` becomes unknown, which forces a replace of the subnet as well. `server.web` refers to the subnet's `id` with a key that forces nothing, so it is only updated. Without a mark each replace deletes first, and the subnet, built on the network, goes before it. Once `subnet.a` is marked, `network.main` gets the mark too, since the subnet depends on it: both are created first, `server.web` moves to the new subnet, and only then do the old ones go.

## Level 4: Applying the plan

Now carry the plan out. The simulated cloud is data: you are told which steps fail and which values the cloud picks.

- `apply(failures, values)`: computes the plan as `plan` would. If it has errors, `apply` returns the error rows and changes nothing. Otherwise it runs the steps in plan order and returns one row per step, `[action, address, outcome]`, without the `replace` tag and without attribute rows. The outcome is `ok`, `failed` or `skipped`.
  - `failures` is a list of `[action, address]` pairs: the cloud fails that step. A pair that names no step of the plan, or a no-op, changes nothing.
  - `values` is a list of `[address, key, value]`: the value the cloud picks for the computed `key` when it creates `address` during this call, by a plain create or the create of a replace. Every resource created gets a value for each computed key of its type; other rows are ignored.
- A step is **skipped** when a step that some before-rule puts before it failed or was skipped. Otherwise it fails when `failures` names it, and succeeds when not. A no-op step does nothing and succeeds unless it is skipped.
- Each step that succeeds is recorded in the actual state at once, and the steps after it see the change:
  - A create records the resource with its desired attributes, resolved **now**, plus the values the cloud picked for its computed keys. Its recorded links become the resources it depends on.
  - An update sets the desired attributes, resolved now, keeps the actual values of the computed keys, and drops every other key. Its recorded links become the resources it depends on.
  - A delete removes the resource and its own links. Links that other resources have to its address stay recorded.
  - Resolving **now** means: a reference to a computed key takes the value the target has in the actual state at that moment, which, for a target just created, is the value the cloud picked; a reference to any other key resolves to the desired value.
- A replace without the mark: its delete removes the actual resource, and its create records the new one. A replace with the mark: when its create succeeds, the resource that was there becomes the **old object** of the address, keeping its attributes and links, and the new resource takes its place. The delete of the replace removes the old object. If that delete fails or is skipped, the old object stays.
- While an address has an old object, every plan has a step `["delete", address, "old"]`, followed by a `-` row for each attribute of the old object. It has rank 1. If the current resource at that address is deleted or replaced as well, both deletes appear. Rules 2 and 4 apply to every delete of an address, the old object's included: rule 2 with the links of the object that the step deletes, and rule 4 as to any delete that is not part of a replace without the mark, with one exception below.
- **Rule 5** keeps an address to one old object at a time: the delete of an old object comes before the other delete of its address, and before the create of a replace of its address. So a second replace with the mark finds the old object gone before it makes a new one, and nothing is ever overwritten.
- The exception to rule 4: it does not hold back the delete of an old object when its address is replaced again. The users can only move to the newest resource, which rule 5 creates after that delete, so waiting for them would make the steps wait for each other.
- `state()`: the actual state, sorted by address. Each resource is a row `[address, "current", key1, value1, key2, value2, ...]` with its keys sorted. An address with an old object has a second row right after it, `[address, "old", ...]`, built the same way.

**Converging.** After a partial failure, the actual state says exactly what happened, so the next plan holds exactly what is left to do, and applying it finishes the job. Once every step succeeds, a new plan is all no-ops.

### Example 1

<!-- case: ex7 -->

The first `apply` creates both resources: the network first, so that the server's `network` key can take the `id` the cloud picked, `net-1`. The state holds that value, not `<unknown>`. A new plan is all no-ops, and applying it changes nothing. After `size` changes, `apply` updates the server, and the computed `id` stays `srv-1`.

### Example 2

<!-- case: ex8 -->

The cloud fails the create of `network.main`. `server.web` depends on it and is skipped, and so is `dns.www`, which depends on the server. `bucket.logs` and the delete of `vm.old` do not depend on the failure and succeed. The state now holds only the bucket, and the next plan is exactly the three creates still missing. Applying it succeeds, and the plan after that is all no-ops.

## Constraints

- At most 40 desired and 40 actual resources, 8 attributes per resource and 300 calls per test.
- Every reference is well formed: a value that starts with `${` is a reference.
- The recorded links of the actual state never form a loop, and the before-rules of a plan without errors always allow an order.
- `values` gives a value for each computed key of each resource that a call creates.

## Follow-ups

- The plan here is computed from what the tool last recorded. Real tools first read the current state of every resource from the cloud, a "refresh". What would a refresh add to the plan, and what can it no longer promise when the cloud changes during the run?
- The steps of a plan form a graph, and steps with no path between them could run at the same time. How would you run the plan with at most `k` cloud calls in flight, and what would a failure do to the steps already running?
- A replace without the mark leaves a window in which the resource does not exist. Which resources can never be replaced with the create first, and why?
- A reference here is a whole value. How would you allow references inside a longer text, and what would that do to the way unknown values print?

## Hints

### Hint 1

Keep two dictionaries from address to attributes, one for the desired state and one for the actual state, where the attributes are themselves a dictionary from key to value. The action of an address then depends on two questions: is it in the first dictionary, and is it in the second? For the attribute rows, walk the union of the keys of both sides in sorted order.

### Hint 2

Resolving a reference means looking up another resource's attribute, which may itself need resolving. If you visit the resources so that each one comes after everything it refers to, every value you look up is already resolved. That order is a topological order of the "depends on" graph.

### Hint 3

A topological order exists only when the graph has no cycle. To find the groups for the errors, compute for each resource the set of resources it can reach by following references. A resource is on a cycle when it can reach itself, and two such resources are in the same group when each can reach the other.

### Hint 4

Turn every step row into a node, and every before-rule into an edge from the earlier step to the later one. Then the plan's order is a topological order where you always take the smallest available node first. A priority queue (a heap) keyed by rank and address gives you that node quickly: start with the nodes that have no incoming edges, and each time you take one, lower the count of its successors and push those that reach zero.

### Hint 5

Decide replace while you resolve, in dependency order. When you reach a resource, every resource it refers to already has its action, so you know whether a reference to a computed key resolves to `<unknown>` or to an actual value, and from that whether this resource is replaced. To spread the mark, walk from each marked address along its dependencies before you build the steps.

### Hint 6

For `apply`, keep the edges you built for the order. Walk the steps in plan order and give each one an outcome: if any of its predecessors did not end `ok`, it is skipped; that check alone carries a failure to everything downstream. When a step succeeds, resolve its references against the actual state as it is at that moment, not against the plan, which only knew `<unknown>`.

### Hint 7

Give the actual state a second dictionary for old objects, with their links. The create of a replace with the mark moves the current resource into it before it records the new one, and the delete of that replace, like the delete of an old object, removes the entry from there. The plan then turns every entry into a delete step of its own, next to any other delete of the address, and its rank and rules 2, 4 and 5 put it where it belongs.
