# Manifest Policy Checks

## Statement

Build `PolicyChecker`, which checks deployment manifests against rules before anything is deployed, and decides which manifests to admit. The API grows over four levels: every level adds methods or rules to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is a manifest?** A manifest is a document that describes something to run: a *workload* (the containers of a service, which image each runs, how much memory it may use, which ports it opens) or a *service* (a stable address that sends traffic to the workloads it selects). Teams write manifests by hand or produce them from templates, and a deployment system turns them into running software.

**What is a policy?** A policy is a rule that every manifest must follow, because breaking it causes trouble later: every workload names the team that owns it, so someone can be paged; every container has a memory limit, so one leak cannot starve its neighbours; no image is referenced by a *moving* tag such as `latest`, so the same manifest always runs the same code. Checked by people in review, such rules are forgotten under pressure. Checked by a program, they hold every time.

**Policy as code.** Here a rule is data, not code: an id, what to check, and where. One general checker runs all the rules over all the manifests and reports every violation in a fixed order, so the report of the same inputs is always the same and can be compared from one change to the next. Later levels add what real policies need to be adopted: exceptions with a reason and an end date, severities and enforcement modes, so that a new rule can warn before it starts to reject, and fixes that a tool or a person can apply.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 35, level 2 by 65, level 3 by 85 and level 4 by 110, keeping the last minutes for a final run.

## Input

- `PolicyChecker()`: creates a checker with no manifests and no rules.
- A manifest is a JSON document and arrives as a list of **rows**, one for each value in the document except the outermost object. A row is `[pointer, kind, text]`:
  - `pointer` says where the value sits: `/name` is the member `name` of the outermost object, `/labels/team` the member `team` inside `labels`, and `/containers/0/image` the `image` of the first item of the list `containers`. This is a *JSON Pointer* (RFC 6901): segments, each after a `/`, that name an object member by its key or a list item by its index counted from 0. The empty pointer `""` means the whole document.
  - `kind` is one of the kinds of JSON value (RFC 8259): `object`, `array` (a list), `string`, `number`, `boolean` or `null`.
  - `text` is the value: the characters of a string, a number in decimal, `true` or `false`, and `""` for an object, an array or a null, whose content is in the rows that follow.
  - A row comes after the row of its parent, list items come in index order, and the members of an object in any order.

  For example, `{"kind": "workload", "name": "web", "labels": {"team": "core"}}` arrives as `[["/kind", "string", "workload"], ["/name", "string", "web"], ["/labels", "object", ""], ["/labels/team", "string", "core"]]`.
- Every manifest has a string `kind` and a string `name`. Its **id** is the kind, a `/` and the name: `workload/web`, `service/web`. Ids are compared as texts.
- The checker does not require any other shape, but the tests use two. A workload has `labels` (an object of texts) and `containers`, a list of objects with a `name`, an `image`, `limits` (an object such as `{"cpu": "500m", "memory": "256Mi"}`) and `ports` (a list of objects with a `name` and a `port`). A service has `labels`, a `selector` (an object of texts) and `ports` (a list of objects with a `name`, a `port` and a `target`).
- A **key** is made of letters, digits and `_`, and does not start with a digit, so a pointer needs none of RFC 6901's escapes.
- Each level's section describes the methods it adds and their parameters.

## Output

Each method's section describes what it returns. Lists of violations come in **report order**: by manifest id, then by rule in the order the rules were first defined, then by pointer in the order the rule produces them. Texts are compared by the numeric value of their characters, so `Z` comes before `a`, and `web10` before `web9`.

## Level 1: Rules on one field

- `addManifest(rows)`: stores a manifest under its id. It returns `true` when the id is new, and `false` when it replaces the manifest that had the id.
- `requireField(ruleId, kind, pointer)`: defines a rule that the value at `pointer` must be present.
- `forbidTags(ruleId, kind, pointer, tags)`: defines a rule that the image reference at `pointer` must be pinned: not referenced by a tag in `tags`, and not without a tag.
- `check()`: every violation of every rule in every manifest, as `[manifestId, ruleId, pointer]` in report order.

**Rules.** A rule applies to the manifests whose `kind` equals the rule's `kind`, or to all manifests when its `kind` is `"*"`. Defining a rule with a new id returns `true` and puts the rule last in the order. Defining one with an id that exists returns `false` and replaces that rule's definition, even with a rule of another sort, while the rule keeps its place in the order.

**Present.** A value is present when the pointer leads to it and it is neither `null` nor the empty string `""`. So `"0"`, `false`, `0`, `{}` and `[]` are all present. A pointer leads nowhere when an object lacks the key, when a list has no item at the index, or when a segment follows a value that is neither an object nor a list. A `requireField` violation is reported at the rule's pointer.

**Image references and tags.** An image is named by a reference such as `registry.local:5000/shop/web:1.4.2`: an optional registry host (which may have a port), the repository path, and then an optional `:tag`. A reference may also end with `@` and a *digest*, such as `web@sha256:4f1c9e`. A tag is a name that whoever publishes images can give to a newer image later, so `web:latest` may run different code next week; such tags are called *moving*. A digest is computed from the content of the image, so it always names the same image.

- When the reference holds an `@`, it is pinned by its digest and never violates a `forbidTags` rule, whatever its tag.
- Otherwise, its tag is the text after the last `:` that comes after the last `/`. With no such `:`, it has no tag: `registry.local:5000/web` has none, since its only `:` comes before a `/`.
- A reference with no tag violates the rule, and so does one whose tag equals one of `tags`, compared exactly (`LATEST` is not `latest`). Anything else passes.
- When the pointer leads nowhere, or to a value that is not a string, the rule passes: whether the field is there is a question for `requireField`.

### Example 1

<!-- case: ex1 -->

`web` passes every rule. `worker` has no `team` label, uses the moving tag `latest`, and its container has a `cpu` limit but no `memory` limit. The violations of one manifest follow the order in which the rules were defined, not the order of the fields.

### Example 2

<!-- case: ex2 -->

The `team` label of the workload `api` is empty, which counts as missing, and its image `api` has no tag at all. The service `api` has no `team` label either, because `team-label` applies to every kind; it is checked first, since `service/api` comes before `workload/api`. The image of `batch` is pinned by its digest. Adding `workload/api` again returns `false` and replaces it. Defining `team-label` again for workloads only returns `false` and leaves the service alone.

## Level 2: Rules across a manifest

**Wildcards.** The pointer of a `requireField` or `forbidTags` rule may now hold the segment `*`, which stands for every item of a list: `/containers/*/limits/memory` asks every container for a memory limit. A rule's pointer is a *pattern*, and expanding it gives the concrete pointers that the rule checks, each reported with its own indexes. To expand a pattern, replace each `*`, from left to right, by the index of every item of the list found at that place. When the value at that place is not a list (it is missing, or an object, or a scalar), that `*` matches nothing and adds no pointer. A segment after a `*` is not looked up while expanding: `/containers/*/limits/memory` gives `/containers/1/limits/memory` for a container without limits, and `requireField` then reports it as missing. Concrete pointers come in the order of their indexes, the leftmost `*` changing slowest, so `/containers/10` comes after `/containers/9`.

- `requirePortTargets(ruleId)`: defines a rule for services: each port of a service must lead to a port that the workloads behind it actually open. Like the other rules, it takes its place in the order, and a later definition with the same id replaces it.

**Selectors.** A service's `selector` is an object of label texts. It **selects** each workload (a manifest of kind `workload`) whose `labels` hold every one of the selector's keys with exactly the same text. Other labels of the workload do not matter, and a selector never selects a service.

**The port rule.** For each service:

- When the service has no `selector`, when its selector is empty, or when it selects no workload, the rule reports one violation at `/selector`, and nothing else for that service.
- Otherwise, for each item `i` of the service's `ports`, in index order, that has a string `target`: the target names a port, and it must be the `name` of a port (`/containers/*/ports/*/name`) of every selected workload, on any of its containers. When one selected workload lacks it, the rule reports a violation at `/ports/i/target`. A port without a string `target` is not checked.

### Example 1

<!-- case: ex3 -->

The first container has a memory limit. The second has none, and the third has an empty one, so both are reported, each with its own index. Only the second container uses `latest`. The port pattern has two wildcards: the first container's port has a number, the `admin` port of the second container has none, and the third container has no `ports` list, so its `*` adds nothing.

### Example 2

<!-- case: ex4 -->

The service `web` selects the workload `web`, whose container opens `http`. The service `api` selects the workload `api`, which opens `http` but not `grpc`, so its first port is reported and its second is fine. No workload has the label `app: legacy`, so the service `old` is reported at `/selector`.

## Level 3: Exceptions

A rule sometimes has to be broken for a while: a vendor image that has no pinned version yet, a team being formed. An **exception** allows one rule to fail in one manifest, with a reason that the report shows and an expiry date after which the exception stops working. Exceptions that never end pile up, so an expired exception is reported until someone renews or removes it.

- `allow(ruleId, manifestId, reason, expires)`: allows the rule `ruleId` to fail in the manifest `manifestId`, for any of its pointers, through the date `expires`. It returns `true` when the pair of rule and manifest had no exception, and `false` when it replaces the existing one's reason and expiry date, even with an earlier date. The rule and the manifest do not need to exist: an exception follows the ids, also when the rule is defined again or the manifest replaced.
- `checkOn(today)`: the report as of the date `today`, as rows of five strings:
  - First, every violation of `check()`, in report order, as `[manifestId, ruleId, pointer, "violation", ""]`, or as `[manifestId, ruleId, pointer, "excepted", reason]` when an exception for its rule and manifest is active on `today`.
  - Then every exception that has expired by `today`, whether or not it still matches a violation, as `[manifestId, ruleId, "", "expired", expires]` with the date written `YYYY-MM-DD`, sorted by manifest id, then by rule id.

An exception is **active** on every day up to and including its expiry date, and **expired** from the next day on. A violation covered only by an expired exception is reported as a `violation`. `check()` does not change: it ignores exceptions.

### Example 1

<!-- case: ex5 -->

On 2026-11-12, the exception for `pinned-image` in `workload/web` is active until the end of the year, so that violation is `excepted` with its reason. The exception for `team-label` in `workload/web` ended on 2026-10-31, so the missing label is a `violation` again, and the exception is listed as `expired` after all the violations. `check()` still lists all three violations.

### Example 2

<!-- case: ex6 -->

On its expiry date, 2026-11-30, the exception for `workload/worker` still applies; a day later it has expired. The exception for `workload/gone` names a manifest that does not exist, and is reported as expired all the same. Allowing the worker's rule again returns `false`, with a new reason and a new date.

## Level 4: Severity, enforcement and fixes

- `configure(ruleId, severity, mode, fix)`: sets the severity, the mode and the fix of the rule `ruleId`, and returns `true`; when no rule has that id, it changes nothing and returns `false`. Defining a rule again keeps its configuration. A rule that was never configured has the severity `medium`, the mode `deny` and no fix.
- `findings(today)`: every violation that no exception active on `today` covers, as `[manifestId, ruleId, pointer, severity, mode, op, value]`. They are sorted by severity, from `critical` to `high`, `medium` and `low`, and in report order within a severity.
- `decide(today)`: one row per manifest, in order of manifest id, `[manifestId, decision, denyCount, warnCount]`: the numbers of its findings in the modes `deny` and `warn`, in decimal, and the decision `reject` when it has at least one `deny` finding, otherwise `admit`.

**Severity and mode.** The severity says how bad a violation is: `low`, `medium`, `high` or `critical`. The mode says what the checker does about it: a `deny` finding rejects its manifest, while a `warn` finding is reported and never rejects, whatever its severity. Keeping the two apart is how a new rule is rolled out: it starts in `warn` mode, its findings are fixed, and then it is switched to `deny`.

**Fixes.** A rule's `fix` is a text; the empty text means the rule has no fix. A finding of a rule with a fix gets a suggestion in the form of an operation of JSON Patch (RFC 6902), an `op` and a `value` that apply at the finding's pointer:

- `requireField`: when the value at the pointer is `null` or `""`, the suggestion is `replace` with the fix as the value. When the pointer leads nowhere and its parent (the pointer without its last segment) is an object, the suggestion is `add` with the fix as the value. When the parent is missing or is not an object, there is no suggestion, because RFC 6902 lets `add` create a member only in an object that exists.
- `forbidTags`: the suggestion is `replace` with the reference rewritten to the fix as its tag: the reference without its tag, then `:` and the fix. `web:latest` with the fix `1.4.2` becomes `web:1.4.2`, and `registry.local:5000/web` becomes `registry.local:5000/web:1.4.2`.
- `requirePortTargets`: never has a suggestion; its fix is ignored.

With no suggestion, `op` and `value` are both `""`.

### Example 1

<!-- case: ex7 -->

Configuring an unknown rule returns `false`. The two memory findings come first because their rule is `critical`, but they are in `warn` mode and never reject; neither container has a `limits` object, so there is nothing to `add` to. The `pinned-image` findings are `high` and `deny`, with the image rewritten to the fixed tag. The `team-label` finding is `low` and `warn`, and its suggestion adds the missing label to the existing `labels` object. Each workload has one `deny` finding and is rejected.

### Example 2

<!-- case: ex8 -->

The empty `team` label is replaced, while the missing `owner` label is added. The first container has a `limits` object without `memory`, so the limit can be added; the second container has no `limits` object at all, so there is no suggestion. The first image has a registry port and no tag, and keeps the port when the fixed tag is added.

## Constraints

- At most 2000 calls in a test, at most 200 manifests and at most 50 rules at once, and at most 500 rows in a manifest.
- Rule ids, kinds, names and keys are 1 to 30 characters: letters, digits, `-` and `_`, except that keys contain no `-`. A rule's `kind` is a manifest kind or `"*"`.
- Strings hold printable ASCII characters (codes 32 to 126), at most 100 of them; numbers are whole numbers of at most 9 digits. Values nest at most 10 levels deep.
- A rule's pointer starts with `/` and has at most 8 segments, each a key, an index or (from level 2) `*`. An image tag, when present, is not empty.
- `tags` has at most 10 items. Dates are real calendar days from 2000-01-01 to 2099-12-31. A severity is `low`, `medium`, `high` or `critical`, and a mode is `warn` or `deny`.

## Follow-ups

- A selector here matches labels by equality. How would you add set-based selectors (`tier in (web, api)`, `track notin (canary)`), and what should an empty set mean?
- Every rule runs over every manifest. How would you index the manifests by kind and by label so that a check after one changed manifest re-evaluates only what it can affect?
- A fix suggestion is one JSON Patch operation. How would you combine the suggestions for one manifest into one patch, and what if two of them touch the same pointer, or one adds the parent another needs?
- Exceptions here are per rule and manifest. What would it take to allow a rule for every manifest that carries a label, and how would you keep such broad exceptions from hiding new problems?
- How would you test a policy itself: the manifests it must reject and the ones it must admit, kept next to the rule?

## Hints

### Hint 1

Start with a small helper: turn the rows of a manifest into a tree, then write a function that follows a pointer through the tree and returns the value it leads to, or nothing. Split the pointer on `/`, skip the empty first part, and at each step look the segment up as a key in an object or as an index in a list. Most of level 1 is that function plus the definition of "present".

### Hint 2

Keep the rules as records in a list (or an ordered map) by id, and the manifests in a map by id. `check` is three nested loops: manifests sorted by id, rules in their order, and the pointers of each rule. Make "the pointers of a rule in a manifest" its own function: at level 1 it returns the rule's pointer, and at level 2 it expands the pattern.

### Hint 3

For a tag, find the last `/` and the last `:` in the reference. If the colon comes after the slash, everything after it is the tag. Check for `@` before you look for the tag at all.

### Hint 4

Expand a pattern with a list of partial pointers that starts as `[""]`. For a plain segment, append it to every partial pointer. For `*`, replace each partial pointer by one pointer per item of the list it leads to, and drop it when it does not lead to a list. Because you never look up the plain segments, a missing field after a `*` still gives a pointer to report.

### Hint 5

For the port rule, first collect the selected workloads, then, for each of them, the set of port names on all of its containers, which is the pattern `/containers/*/ports/*/name` again. A target is fine when it is in every one of those sets.

### Hint 6

Keep exceptions in a map from the pair (rule id, manifest id) to the reason and the date. `checkOn` walks the violations of `check` and looks each one up in that map; the expired exceptions are a separate pass over the map, sorted at the end. Compare dates as dates, or as `YYYY-MM-DD` texts, which sort the same way.

### Hint 7

For `findings`, build the list of active violations in report order, then sort it by the rank of the severity with a stable sort, which keeps report order within a severity. The fix of a missing field needs one more lookup: the parent pointer, everything before the last `/`, which is the whole manifest when that is empty. `decide` counts the findings per manifest and must also list the manifests that have none.
