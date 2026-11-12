# Manifest Policy Checks: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| expand-and-match | optimal | O(M log M + M R P + V M) per check, for M manifests, R rules, P pointers per rule and manifest, and V services; findings add O(F log F) for F findings | O(N + E + F) for N rows in all manifests, E exceptions and F findings | default answer; one list of violations in report order feeds every level |

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Manifests become trees; rules are records in an ordered map | manifests by id, rules by id in definition order |
| 2 | A rule's pointer becomes a pattern; a third sort of rule reads other manifests | nothing new: the port rule computes the selection on each check |
| 3 | Exceptions by (rule, manifest) | a map from that pair to a reason and a date |
| 4 | Each rule carries a severity, a mode and a fix | three fields on the rule record |

The choice that carries the problem is to compute one list of violations, in report order, and build every other answer from it. `check` prints it, `checkOn` labels each item and appends the expired exceptions, `findings` filters it by the active exceptions and sorts it by severity with a stable sort, and `decide` counts it. None of the later levels changes how a violation is found, so none of them can disturb the order that level 1 fixed. The second choice is to keep a rule's configuration on the rule record and its exceptions outside it, keyed by ids: redefining a rule then keeps both, as the statement asks, without any extra code.

## Approach: expand-and-match (Expand each rule's pattern over each manifest, then layer exceptions, modes and fixes)

### Intuition

A rule is three things: which manifests it applies to (a kind), where it looks (a pointer pattern), and what it requires there (present, pinned, served). Keeping those apart makes the checker general: every rule runs the same loop, and only the last step, the test at one concrete pointer, differs between the sorts of rules. Wildcards then cost nothing extra in the loop: they only change how many concrete pointers a pattern gives.

Exceptions, severities and modes are not part of finding a violation; they are decisions about it. So they live on top of the list of violations, as filters and labels, which is the policy-as-code idea of separating the check from the enforcement.

### Algorithm

1. Level 1: `addManifest` decodes the rows into a tree (an object node with members, a list node with items, a scalar with a kind and a text) and stores it under `kind/name`. A rule is a record with its sort (`field`, `tags` or `ports`), its kind, its pointer, its tags, and the configuration of level 4; defining an existing id overwrites the definition in place. `check` sorts the manifest ids, and for each manifest walks the rules in order, skipping those for another kind, and collects the failing pointers of each rule. A field fails when the pointer leads nowhere, to a `null` or to `""`. A tag rule fails when the pointer leads to a string without `@` whose tag is missing or listed; the tag is what follows the last `:` when that `:` comes after the last `/`.
2. Level 2: expanding a pattern keeps a list of partial pointers, starting with `[""]`. A plain segment is appended to each; a `*` replaces each partial pointer by one pointer per item of the list it leads to, and drops it when it leads to anything else. The port rule reads the service's selector, keeps the workloads whose labels hold every selector pair, and fails at `/selector` when there is no usable selector or nothing is selected. Otherwise it builds, for each selected workload, the set of names given by `/containers/*/ports/*/name`, and fails at `/ports/i/target` for each port whose target is missing from one of those sets.
3. Level 3: `allow` stores the reason and the date under (rule id, manifest id). `checkOn` walks the violations and looks each one up: an exception whose date is on or after `today` makes the row `excepted` with its reason, anything else is a `violation`. It then lists the exceptions whose date is before `today`, sorted by manifest id and rule id.
4. Level 4: `configure` writes three fields on an existing rule. `findings` keeps the violations without an active exception, adds the rule's severity, mode and fix suggestion, and sorts by the rank of the severity with a stable sort. A field's suggestion is `replace` when the value is there but `null` or empty, `add` when it is missing and its parent is an object, and nothing otherwise; a tag's suggestion replaces the reference by its repository, `:` and the fixed tag. `decide` counts the `deny` and `warn` findings of every manifest, including the manifests with none.

### Correctness

Report order: the outer loop visits manifest ids in sorted order, the middle loop the rules in definition order, and the inner loop the concrete pointers in the order the expansion produces them, so the list is in report order by construction. A redefinition overwrites the record in place, so the rule keeps its position.

Expansion: by induction on the segments of the pattern, the list after `k` segments holds exactly the pointers that match the first `k` segments, with every `*` bound to an existing index of a list, in the order of those indexes with the leftmost `*` slowest. A plain segment extends each pointer without changing the order; a `*` replaces each pointer, in order, by its items in index order. Plain segments are never looked up, so a missing field after the last `*` still yields its pointer, which is what lets `requireField` report it.

Selection: a workload is selected exactly when every selector pair is among its labels, and a target passes exactly when it is in the port names of every selected workload. Both are direct translations of the statement's "every".

Exceptions: an exception is looked up by the exact pair, so it covers that rule in that manifest and nothing else, at any of its pointers. `today <= expires` is the statement's "up to and including its expiry date", and the expired list is the complement among the stored exceptions, independent of the violations.

Findings and decisions: a stable sort by severity rank keeps the report order inside each severity. A finding counts toward its mode only, so a `warn` finding can never reject; and `decide` iterates the manifests, not the findings, so a manifest without findings still gets its row.

### Complexity

- Time: O(M log M + M R P + V M) per check, for M manifests, R rules, P pointers per rule and manifest, and V services; findings add O(F log F) for F findings — the ids are sorted once, each rule tests each of its concrete pointers with a lookup of at most 8 segments, and each service scans the manifests for the workloads it selects; findings sort what they keep.
- Space: O(N + E + F) for N rows in all manifests, E exceptions and F findings — the trees hold one node per row, the exception map one entry per pair, and the answers one row per violation.

### Trade-offs

- Rules as data, run by one generic loop, are easy to add, list, compare and explain; the price is that a rule can say only what the loop understands. Real policy engines give rules a small language of their own, which is more expressive and harder to analyze.
- The port rule scans every manifest for each service. An index from each label pair to the workloads that carry it would make selection a set intersection, at the cost of keeping it up to date when a manifest is replaced.
- Recomputing everything on each call keeps the answer obviously consistent with the current manifests, rules and exceptions. A checker in a busy pipeline would cache the violations per manifest and recompute only the manifests that changed, or the rules that were redefined.
- One suggestion per finding is simple to show and to apply by hand. Applying several of them as one JSON Patch needs an order (a parent `add` before the child's), which this design does not attempt.

### Pitfalls and edge cases

- A `null` and an empty text count as missing; `"0"`, `false`, `0`, `{}` and `[]` are present (`h1`, `h12`).
- A rule's kind decides which manifests it reads; `"*"` means all of them (`h1`, `h4`).
- The tag starts after the last `:` only when that `:` comes after the last `/`, so a registry port is not a tag. A digest pins the reference whatever its tag says, tags compare exactly, and an image without a tag fails (`h2`).
- A missing image or one that is not a text passes a tag rule; reporting it is the job of a field rule (`h2`).
- Manifests sort by id as text, case included; rules keep their definition order, through redefinition and even when the sort of rule changes. A service and a workload with the same name are different manifests (`h3`, `h4`).
- Wildcard pointers come in index order, not text order; a `*` walks lists only; a fixed segment after a `*` is reported when it is missing, while a later `*` on a missing list adds nothing (`h5`).
- A selector needs every pair to match exactly, never selects services, and an empty or missing selector selects nothing. A target must be on every selected workload, on any container (`h6`).
- An exception lasts through its expiry day, covers one rule in one manifest at all its pointers, and is reported once it expires even when nothing matches it any more; expired rows sort by manifest, then rule. A second `allow` replaces the first (`h8`, `h9`, `h10`).
- Severity orders the findings and mode decides the outcome; a critical warning never rejects, and redefining a rule keeps its configuration (`h11`).
- A missing value gets `add` only when its parent object exists: a missing parent gets no suggestion, since RFC 6902 would refuse the `add`, and neither does a parent list, by this problem's choice. `null` or `""` get `replace` (`h12`).
- Every manifest gets a decision row, and excepted findings do not count until their exception expires (`h13`).

### Language notes

- Python and TypeScript keep insertion order in `dict` and `Map`, which gives the rule order for free; Java uses a `LinkedHashMap`, Kotlin a `LinkedHashMap` (its `mutableMapOf` is one), and Go and Rust keep a list of rule ids next to a map from id to rule.
- Exceptions are keyed by a pair: a tuple in Python, a `Pair` or a record in Kotlin and Java, a struct in Go and Rust, and a joined string in TypeScript, with a separator (a NUL character) that no id contains.
- Dates: Python's `date`, Java's and Kotlin's `LocalDate` and Rust's `NaiveDate` compare directly; Go compares `time.Time` with `Before` and `After`, and TypeScript receives `YYYY-MM-DD` strings, which compare correctly as texts. Each language formats the expiry date back as `YYYY-MM-DD`.
- Every language's sort used for `findings` must be stable: Python's `sorted`, Java's `List.sort` and Kotlin's `sortedBy` are; TypeScript's `Array.prototype.sort` is stable since ES2019; Go needs `sort.SliceStable` (or `slices.SortStableFunc`), and Rust's `sort_by_key` is stable.

## Further reading

- [RFC 6901, JSON Pointer, P. Bryan, K. Zyp and M. Nottingham, April 2013](https://www.rfc-editor.org/rfc/rfc6901): the pointer syntax used by rules and reports.
- [RFC 6902, JSON Patch, P. Bryan and M. Nottingham, April 2013](https://www.rfc-editor.org/rfc/rfc6902): the operations `add`, `remove`, `replace`, `move`, `copy` and `test`; section 4.1 says that `add` replaces an existing member but needs the object that receives it to exist, and section 4.3 that `replace` needs its target to exist.
- [RFC 8259, The JSON Data Interchange Format, T. Bray, December 2017](https://www.rfc-editor.org/rfc/rfc8259): the kinds of JSON value that rows carry.
- [OCI Distribution Specification](https://github.com/opencontainers/distribution-spec/blob/main/spec.md): defines a tag as a human-readable pointer to a manifest, notes that one digest may have many tags, and defines a digest as an identifier made from a cryptographic hash of the content.
- A. Rahman, C. Parnin and L. Williams, "The Seven Sins: Security Smells in Infrastructure as Code Scripts", Proceedings of the 41st International Conference on Software Engineering (ICSE), 2019, [doi:10.1109/ICSE.2019.00033](https://doi.org/10.1109/ICSE.2019.00033).
- A. Rahman, R. Mahdavi-Hezaveh and L. Williams, "A systematic mapping study of infrastructure as code research", Information and Software Technology 108, 2019, [doi:10.1016/j.infsof.2018.12.004](https://doi.org/10.1016/j.infsof.2018.12.004).
- T. Xu and Y. Zhou, "Systems Approaches to Tackling Configuration Errors", ACM Computing Surveys 47(4), 2015, [doi:10.1145/2791577](https://doi.org/10.1145/2791577): a survey of configuration errors, which its abstract calls one of the dominant causes of system failures, and of ways to prevent, detect and troubleshoot them.
