# Drift Detection

## Statement

Build `DriftDetector`, the part of an infrastructure tool that notices when the real world no longer matches what the tool believes. Someone resizes a server by hand during an incident, a script deletes a disk, a colleague creates a bucket from a web console: none of that goes through the tool, so its records are now wrong. The detector compares its records with a fresh scan of the real world and reports the differences. Later levels filter out false alarms, adopt resources the tool never created, and decide what to do about each difference. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**The words.** A **resource** is one thing the tool manages: a server, a disk, a firewall group. Each has a **type** (`server`) and **attributes**, pairs of a **key** and a **value** (`size = large`). The cloud knows a resource by its **id**, such as `i-100`, which the cloud chose. The tool knows it by an **address** it chose, `type.name`, such as `server.web`. The **desired state** is what you want; the **actual state** is what exists. The tool keeps its own copy of the actual state, the **recorded state**: for each address, the id of the real resource and the attributes it had when the tool last touched it. A **scan** reads the real world and lists every resource it finds by id, with its type and current attributes. **Drift** is any difference between the recorded state and the scan.

**Why it matters.** A tool that plans from stale records makes wrong plans: it may "fix" a hand-made change that was deliberate, or fail because a resource it expects is gone. Detecting drift only reads, so running the detector twice on the same records and scan gives the same report. That is **idempotence**: doing something again changes nothing more. It is also what you want from fixing drift: once the world matches, a second fix must find nothing to do.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 60, level 3 by 85 and level 4 by 110, keeping the last minutes for a final run.

## Input

- `DriftDetector()`: creates a detector with nothing recorded and nothing scanned.
- An **address** is `type.name`. A type, a name and a key are each 1 to 20 characters: lowercase letters, digits and `_`, starting with a letter.
- An **id** is 1 to 20 characters: letters, digits, `-` and `_`.
- A **value** is 1 to 40 printable ASCII characters (codes 33 to 126, so no space).
- `attributes` is a list of `[key, value]` pairs with distinct keys. Their order means nothing.
- Each level's section describes the methods it adds and their parameters.

## Output

Methods that change the detector return a `bool`, except where a level says otherwise. Reports return **rows**: each row is a list of strings, in the order its level specifies. An empty string `""` in a row stands for a key that is missing, since a value is never empty. Where something is "sorted", texts are compared by the numeric value of their characters, so capitals come before lowercase letters, digits before `_`, and `web10` before `web9`.

## Level 1: Records versus the scan

- `record(address, resourceId, attributes)`: records that the address stands for the real resource `resourceId`, with these attributes. It returns `true` when the address was not recorded, and `false` when this replaces an earlier record of it: the earlier id and attributes are forgotten, not merged.
- `observe(resourceId, resourceType, attributes)`: the scan found the resource `resourceId`, of type `resourceType`, with these attributes. It returns `true` when the id was not scanned before, and `false` when this replaces what the scan said about it.
- `drift()`: compares the recorded state with the scan and returns the report.

A recorded address is matched to the scan by its **id**, never by its name. No two addresses record the same id, and a recorded id that the scan found has the type of its address.

| Recorded | Found by the scan | Row |
|----------|-------------------|-----|
| yes | no | `["deleted", address, resourceId]`: someone deleted it outside the tool |
| yes | yes | `["changed", address, key, recorded, scanned]` for each key whose values differ |
| no | yes | `["unmanaged", resourceId, resourceType]`: it exists, but no address records it |

Values compare exactly as text, so `Large` and `large` differ. A key on one side only differs too, and the row shows `""` for the side that lacks it.

**The order.** First the rows about recorded addresses, sorted by address; the changed rows of one address are sorted by key. Then the unmanaged rows, sorted by id.

### Example 1

<!-- case: ex1 -->

The disk `vol-7` is gone, so `disk.data` is deleted. The server `i-100` has a new `size` and a `monitoring` key that the record lacks, shown with `""` on the recorded side. The bucket matches its record and gives no row. The scan also found `i-999`, which no address records: unmanaged.

### Example 2

<!-- case: ex2 -->

At first `vm.a` matches. Recording it again with the id `i-2` replaces the record, so the tool now looks for `i-2`, which the scan has not found: `vm.a` is deleted, and `i-1` becomes unmanaged. Once the scan finds `i-2` with a new size, `vm.a` has a changed row instead; `i-1` is still unmanaged, whatever its attributes.

## Level 2: Ignore rules and normalization

Not every difference is worth an alarm. Some keys change on their own (a tag a billing job writes), some resources belong to someone else, and some values look different while meaning the same thing.

- `ignore(pattern, key)`: from now on, drift on `key` is not reported for the addresses that match `pattern`. The key `*` means the whole resource: no row at all is reported for it. It returns `true` when this rule is new and `false` when the same pattern and key were given before.
- `unordered(resourceType, key)`: from now on, the value of `key` on resources of `resourceType` is a list of items separated by commas, whose order means nothing: `22,80,443` and `443,22,80` are the same. How many times an item appears still counts, so `a,a,b` and `a,b` differ. It returns `true` when new, `false` when declared before.
- `defaultValue(resourceType, key, value)`: from now on, a resource of `resourceType` that lacks `key` is compared as if it had `value`. It returns `true` when the type and key had no default, and `false` when this replaces an earlier default.

**Patterns.** A pattern is 1 to 40 printable ASCII characters. `*` matches any run of characters, including none and including dots; every other character, `?` and `[` included, matches only itself. A pattern must match the whole text: `server.*` matches `server.web`, `*web` matches `server.web`, `server.web*` matches `server.web` and `server.web2`, and `server.we` matches nothing but itself.

**What the rules apply to.** A recorded resource is matched by its address. An unmanaged resource has no address yet, so it is matched by `type.id`, such as `server.tmp-1`, and only a rule with the key `*` can hide it. A rule for a key never hides a deleted resource: only a whole-resource rule does.

**Comparing.** Two values of a key are the same when, after a missing value takes the default of its type and key (if there is one), both are present and equal, or both are lists of the same items for an unordered key. Normalization only decides whether there is drift: the rows still print the values as recorded and scanned, with `""` for a missing one.

### Example 1

<!-- case: ex3 -->

`tags` changes on its own on every server, so it is ignored there; `owner` and `size` still drift on `server.web`. `server.api` is ignored as a whole, and the unmanaged `tmp-1` is hidden by `server.tmp-*`, which matches `server.tmp-1`. Nothing hides the queue `q-5`. The second `ignore("server.*", "tags")` returns `false`.

### Example 2

<!-- case: ex4 -->

The firewall rules are the same set in another order. `server.a` has no `monitoring` in its record, and the default `off` matches the scan. `server.b` records `on` while the scan has nothing, which the default turns into `off`: drift, shown with the raw `""`. When the default becomes `on`, the two servers swap.

## Level 3: Import and the plan

Sometimes the fix for an unmanaged resource is to adopt it: tell the tool which address it should have, and let it manage the resource from now on. That is an **import**. After an import, the tool compares the resource with what you want, which is the plan.

- `importResource(address, resourceId)`: adopts the scanned resource `resourceId` under `address`, recording the attributes the scan found. It returns `"imported"`, or, without changing anything, the first refusal that applies:
  1. `"not-found"`: the scan has not found `resourceId`.
  2. `"type-mismatch"`: the type of the address is not the type the scan found.
  3. `"already-managed"`: some address already records `resourceId`, this one included.
  4. `"address-taken"`: the address already records another id.
- `desire(address, attributes)`: declares that the resource should exist with exactly these attributes. It returns `true` when the address was not desired and `false` when this replaces an earlier declaration.
- `plan()`: compares the desired state with the recorded state, not with the scan, and returns one row per difference, sorted by address, then key:
  - `["create", address]` for an address that is desired and not recorded;
  - `["delete", address]` for an address that is recorded and not desired;
  - `["update", address, key, recorded, desired]` for each key of an address in both whose values differ.

The plan compares with the same normalization as the drift report, but the ignore rules belong to drift alone and do not change the plan. An import with no desired resource therefore plans to delete what you just adopted.

### Example 1

<!-- case: ex5 -->

Before the import, the scan has two unmanaged resources. `i-7` is imported as `server.api`. The bucket `b-2` cannot become a server, `i-404` does not exist, `i-7` is now managed, and `server.web` already stands for `i-1`. After the import `i-7` has no drift, since its record was copied from the scan. The plan compares the desired `server.api` with that record: only `zone` differs.

### Example 2

<!-- case: ex6 -->

The imported group's rules are the desired ones in another order, so the plan has no row for it. `vm.new` is desired and not recorded, and `vm.old` is recorded and not desired. The rule that ignores every `vm` resource does not change the plan.

## Level 4: Reconciliation policies

Finding drift is half the job; the other half is deciding what to do. A **policy** says, for each resource, which way the truth flows:

- `revert`: the desired state is right; change the real resource back.
- `accept`: the real world is right; change the desired state to match it.
- `alert`: report it and change nothing, so a person decides.

Methods:

- `policy(pattern, mode)`: from now on, addresses that match `pattern` (as in level 2) follow `mode`, which is `revert`, `accept` or `alert`. When several rules match an address, the newest one wins. Giving a pattern again replaces its mode and makes it the newest rule. It returns `true` when the pattern had no rule and `false` when it had one. An address that no rule matches follows `alert`.
- `reconcile()`: returns what a reconcile run would do, without doing it. When it is called, every recorded address is also desired.

`reconcile` works through the rows of `drift()`, in the same order, with the same ignore rules and normalization, and turns each into at most one row:

| Drift row | `revert` | `accept` | `alert` |
|-----------|----------|----------|---------|
| `changed` | `["revert", address, key, scanned, desired]` | `["accept", address, key, desired, scanned]` | `["alert", address, key, recorded, scanned]` |
| `deleted` | `["recreate", address]` | `["forget", address]` | `["alert-deleted", address, resourceId]` |
| `unmanaged` | always `["alert-unmanaged", resourceId, resourceType]`, whatever the rules | | |

`desired` is the value of the key in the desired state, `""` when it lacks the key. A `revert` or `accept` row is left out when the scanned value and the desired value are already the same, under the normalization of level 2: the world already agrees with what you want, so neither side needs to change. Each row shows which side changes: a revert changes the real resource from the scanned value to the desired one, and an accept changes the desired state from its value to the scanned one.

### Example 1

<!-- case: ex7 -->

Every server reverts, except `server.api`, whose newer rule accepts. `dns.www` has no rule, so its deletion only raises an alert, as does the unmanaged queue. Giving `server.*` again with `alert` makes it the newest rule, which now beats `server.api` too.

### Example 2

<!-- case: ex8 -->

`vm.a` reverts to its desired size `m`, not to the recorded `s`. `vm.b` drifted to exactly what is desired, so there is nothing to revert. `vm.c` is gone and is recreated, while `vm.d`'s newer rule accepts its loss. `drift()` is unchanged: a policy only changes what a reconcile would do.

## Constraints

- At most 200 recorded, 200 scanned and 200 desired resources, 10 attributes per resource, 50 rules of each kind and 2,000 calls per test.

## Follow-ups

- The scan here is complete. A real scan can miss resources because of permissions or paging. How would you tell "deleted" from "not visible to this scan"?
- `accept` rewrites the desired state. If that state is code in a repository, what would the tool produce instead of a direct change?
- How would you report drift continuously, scanning only what changed since the last scan, without rereading every resource?
- An ignore rule for a key hides real drift too. How would you limit the damage, for example by expiring rules or counting how often they hide a change?

## Hints

### Hint 1

Keep the recorded state as a dictionary from address to a pair (id, attributes), and the scan as a dictionary from id to a pair (type, attributes). For each recorded address, look its id up in the scan: missing means deleted, present means compare the two attribute dictionaries over the union of their keys. Every scanned id that no record mentions is unmanaged.

### Hint 2

Collect the recorded ids in a set while you walk the records, then walk the scanned ids in sorted order and keep the ones that are not in the set. Sort the addresses and the keys before you walk them, and the order of the report comes for free.

### Hint 3

Put all of level 2's comparison rules into one function, `same(type, key, first, second)`, that fills in a default for a missing value and then compares either the texts or the sorted lists of items. Every later feature calls it: drift, the plan and the reconcile.

### Hint 4

Matching a pattern with `*` is a classic problem. Walk the pattern and the text together. On a plain character, both must agree. On `*`, remember where the star is and where you are in the text, and first let it match nothing. If a later character fails, go back to the remembered star and let it swallow one more character of the text. The pattern matches when the text is used up and only stars remain.

### Hint 5

For an import, check the refusals in the order the statement gives them, and copy the scanned attributes rather than sharing the scanner's dictionary: a later scan of the same id must not change the record.

### Hint 6

Keep the policies in a list in the order they were given, removing a pattern before you add it again. The mode of an address is then the mode of the last rule in the list that matches it, or `alert`. `reconcile` can reuse the drift rows as they are and map each to its row; only a `changed` row needs the desired value and one more call to `same`.
