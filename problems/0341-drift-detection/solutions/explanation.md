# Drift Detection: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| keyed-compare | optimal | O(N log N + N K log K + N P L^2) per report, for N resources, K keys, P rules and L the length of a pattern or address | O(N K) | default answer; one comparison function and one pattern matcher serve every report |

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Records versus the scan | a map from address to (id, attributes) and a map from id to (type, attributes) |
| 2 | Ignore rules and normalization | a set of ignore rules, a set of unordered keys and a map of defaults, all keyed by type and key |
| 3 | Import and the plan | a map of desired resources; import writes into the records |
| 4 | Policies | an ordered map from pattern to mode |

The choice that keeps the later levels small is to put every rule about equality into one function, `same(type, key, first, second)`, from level 2 on. The plan of level 3 and the reconcile of level 4 compare values too, and they must agree with the drift report on what counts as a difference: an unordered list that drifts in the report but not in the reconcile would be a bug that no single level shows.

## Approach: keyed-compare (Look each record up by id, compare normalized values, and filter with star patterns)

### Intuition

The tool's name for a resource (its address) and the cloud's name (its id) are different, and only the id is shared, so the records are joined to the scan through the id. After that, drift is a comparison of two small maps per resource. Everything else is a filter on top: normalization decides whether two values differ, ignore rules decide whether a difference is reported, and a policy decides what a reported difference turns into. Keeping those three apart, in that order, is what lets each level add one idea without touching the others.

### Algorithm

1. Level 1: walk the recorded addresses in sorted order. Look up the id in the scan: missing gives a `deleted` row; present gives a `changed` row for each key, in sorted order, whose values differ. Collect the recorded ids in a set; afterwards, walk the scanned ids in sorted order and give each one that is not in the set an `unmanaged` row.
2. Level 2: before comparing, fill a missing value with the default of its type and key; then compare the sorted lists of items for an unordered key and the plain texts otherwise. Skip a whole recorded resource when a rule with key `*` matches its address, skip a `changed` row when a rule for its key matches, and skip an unmanaged resource when a `*` rule matches `type.id`.
3. Match a pattern by walking it and the text together: a plain character must agree; a star is remembered with the current position in the text and first matches nothing; on a mismatch, return to the remembered star and let it take one more character. At the end, the text must be used up with only stars left in the pattern.
4. Level 3: an import checks its refusals in the given order and then records a copy of the scanned attributes. The plan walks the union of desired and recorded addresses in sorted order and compares the two attribute maps with the same comparison function, without the ignore rules.
5. Level 4: a policy removes its pattern and adds it again at the end. The mode of an address is the mode of the last pattern that matches, or `alert`. The reconcile computes the drift rows and maps each one: an unmanaged row to an alert, a deleted row by mode, and a changed row by mode, after checking whether the scanned value already equals the desired one.

### Correctness

Join: each recorded address has one id and no two addresses share one, so each record meets at most one scanned resource, and every scanned resource is either met by exactly one record or unmanaged. That partition is exactly the three kinds of rows.

Comparison: filling a default first and then comparing makes `same` an equivalence on the values of one type and key, so the drift report, the plan and the reconcile all agree on which values differ. Sorting the items of a list keeps repeats, so the comparison is on multisets, as the statement asks.

Pattern matching: the walk tries the star positions from the shortest match upward and never revisits an earlier star, because once a later star has matched, any way of making the pattern match can be rearranged so that the earlier stars keep their current spans and only the last star grows. If no extension of the last star works, no match exists.

Policies: the map keeps the patterns in the order of their last declaration, so scanning it and keeping the last match is "the newest rule wins".

Reconcile: it starts from the same rows as `drift`, so it reports nothing that the report hides and hides nothing that the report shows. A revert or an accept is left out exactly when the scanned value already equals the desired one under `same`, which is when neither side would change.

### Complexity

- Time: O(N log N + N K log K + N P L^2) per report, for N resources, K keys, P rules and L the length of a pattern or address — sorting the addresses and the ids is O(N log N); comparing a resource sorts its keys and compares values, splitting and sorting the items of unordered ones; each ignore or policy check runs the pattern walk, which is O(L^2) in the worst case.
- Space: O(N K) — the records, the scan and the desired state each hold up to N resources of K keys; a report holds at most one row per key.

### Trade-offs

- Comparing on every report is simple and fast enough for hundreds of resources. A detector that runs continuously would keep the last report and compare only the resources whose scanned attributes changed.
- The star walk is quadratic in the worst case. Compiling each pattern once, to a regular expression or a small automaton, makes each match linear; with short patterns and few rules the walk is enough and needs no library.
- An ignore rule silences real changes as well as noise. Normalization is safer when it applies, because it only merges values that mean the same thing.
- The newest rule wins, which makes a rule added for an incident override the general ones at once. Some tools prefer the most specific pattern instead, which is easier to read but needs a definition of "specific".

### Pitfalls and edge cases

- Join on the id, not the name: an address's name says nothing about the cloud's id (hidden case `h4`).
- A key on one side only is drift (`h2`), values compare exactly (`h2`), and a second `record` or `observe` replaces the attributes (`h3`).
- Sort by character code: capitals before lowercase, `web10` before `web9`, and unmanaged rows by id, never by type (`h1`).
- A star matches nothing, crosses dots, and must not turn into a prefix match; `?` and `[` are plain characters (`h5`).
- A rule for a key never hides a deleted resource, and an unmanaged resource goes by `type.id` and is hidden only by a `*` rule (`h6`).
- Unordered lists count repeats, rules belong to one type, a default fills only a missing key, and rows show raw values (`h7`, `h8`).
- Import refusals have a fixed order, and an import copies the scanned attributes (`h9`). The plan reads the records, not the scan, and keeps the ignore rules out (`h10`); an import without a desired resource plans a delete (`h11`).
- The newest matching rule wins, and a pattern given again becomes the newest (`h12`). A revert targets the desired value, and nothing happens when the scan already agrees with it under normalization (`h13`). Unmanaged resources only raise alerts (`h14`).

### Language notes

- Records and scans are maps to small records: tuples in Python, objects in TypeScript, records or small classes in Java and Kotlin, structs in Go and Rust.
- The pattern walk indexes characters: Python and TypeScript index strings, Java and Kotlin use `charAt`, and Go and Rust walk bytes, which is safe because patterns and addresses are ASCII.
- Python keeps the policies in a `dict`, which remembers insertion order, and TypeScript in a `Map`, which does too; Java uses a `LinkedHashMap`, Kotlin a `LinkedHashMap`, Go a slice of pairs and Rust a `Vec` of pairs, removing the old entry before appending.
- Sorting compares strings by code point in Python, by UTF-16 unit in TypeScript, Java and Kotlin, and by byte in Go and Rust; all agree on printable ASCII.

## Further reading

- [Controllers, Kubernetes documentation](https://kubernetes.io/docs/concepts/architecture/controller/): a control loop that moves the current state toward the desired state, the idea behind reconciliation.
- [Import, OpenTofu documentation](https://opentofu.org/docs/cli/commands/import/): bringing an existing remote object under management at an address, found by its id, and importing each object to only one address.
- [The lifecycle meta-argument, OpenTofu 1.6 documentation](https://opentofu.org/docs/v1.6/language/meta-arguments/lifecycle/): `ignore_changes`, for attributes that processes outside the tool change. That setting affects planning, so the tool proposes no update for those attributes; this problem's ignore rules differ: they filter the drift report and leave the plan unchanged.
- [Shell Command Language, section 2.14 Pattern Matching Notation, The Open Group Base Specifications Issue 8 (IEEE Std 1003.1-2024)](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html): the standard glob, where `*` matches any string including the null string and `?` and `[` are special, unlike in this problem.
