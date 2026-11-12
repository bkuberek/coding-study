# Semver Resolver: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| depth-first-resolve | optimal | O(L) per version or range of length L; O(V^P) per search in the worst case; O(C) searches per explanation | O(R + P) for R published releases and P packages | default answer; one parser and one search serve all four levels |

Here `V` is the most releases a package has, `P` the number of packages the search touches, `R` the number of published releases and `C` the number of constraints.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Parse versions into numbers and identifiers; compare by a key | no state: a parser and a comparison |
| 2 | Expand each range into comparator sets; test membership with the pre-release rule | still no state: a range parser that builds on the version parser |
| 3 | A registry and a depth-first search with backtracking | the releases of each package, newest first, each with its expanded dependency ranges |
| 4 | Explanations by leaving constraints out; a preferred version per package | every dependency gets a number in publish order, and the search takes the constraints to leave out and the preferred versions as inputs |

The choice that keeps the later levels small is to write the search once, as a function of what is in force (the root requirements and dependencies not left out) and what is preferred (the lock). Resolving, explaining, locked resolving and updating are then the same search with different inputs.

## Approach: depth-first-resolve (Precedence keys, expanded ranges and a depth-first search)

### Intuition

Precedence is a lexicographic order once each version is turned into the right key: the three numbers, then a flag that puts a release after its pre-releases, then the pre-release identifiers, each turned into a pair that sorts numbers before words. A range is a disjunction of conjunctions of simple comparisons, so after expanding the shorthand operators (`^`, `~`, wildcards) into plain comparators, membership is two loops and the pre-release rule. Resolving is a constraint search: choose a version for one package at a time, and when a later package cannot be satisfied, undo the latest choice and try the next version. A fixed order of packages (smallest name first) and of versions (highest first) makes the first solution found the answer.

### Algorithm

1. Level 1: split off the build metadata at the first `+` and the pre-release at the first `-`, then check the three numbers and each identifier. The key of a version is `(major, minor, patch, has-no-pre-release, identifiers)`, where each identifier becomes `(0, number)` when it is numeric and `(1, text)` otherwise; comparing keys gives the precedence. `sortVersions` sorts the valid versions by `(key, text)`. `changeKind` compares the keys, then the three numbers in turn.
2. Level 2: split the range at `||`, split each piece at spaces, and expand each term. A term whose pattern parses as a full version takes any operator; otherwise the pattern must be a partial version with no operator, `=`, `^` or `~`, and the number of leading numbers (0, 1 or 2) chooses the row of the expansion table. Upper bounds carry the pre-release `0`. A version is in a set when every comparator holds and, if the version has a pre-release, some comparator has a pre-release on the same core.
3. Level 3: `publish` checks the statuses in order and keeps each package's releases sorted from the highest precedence down, with every dependency range already expanded. The search is recursive: compute the needed packages from the root requirements and the chosen releases; if all are chosen, succeed; otherwise take the smallest open name, collect the ranges required of it, and try each release that is in all of them and whose own dependencies agree with the chosen releases. Recurse after each choice, and remove the choice when the recursion fails.
4. Level 4: number the root requirements and the dependencies in publish order. `explain` keeps two sets, the root requirements and the dependencies left out, and for each constraint in order adds it to its set, runs the search, and takes it back out if the search now succeeds. `lockedResolve` passes the lock as preferred versions; the search tries the preferred release first. `update` removes the unlocked names from the preferences, resolves, and compares the result with the old lock by name.

### Correctness

Precedence: the key reproduces each rule of the specification in order. The three numbers come first and compare as integers. With an equal core, the flag `has-no-pre-release` is 0 for a pre-release and 1 for a release, so a pre-release is lower. Two pre-release lists compare element by element; `(0, n)` against `(1, s)` puts numbers first, two numbers compare as integers and two words by their character codes; and when one list is a prefix of the other, lexicographic comparison of sequences makes the shorter one lower. Build metadata is not part of the key, so it never changes the order.

Ranges: each row of the expansion table is a direct translation of the statement, and the upper bounds `<X.Y.Z-0` exclude exactly the versions of core `X.Y.Z` and above, because no pre-release is below the single identifier `0`. The pre-release rule is checked per set, as the statement requires, so a pre-release invited by one set is not invited by another.

Search: the search is complete. Suppose a resolution `S` exists, and follow the search along `S`: while the chosen releases are a part of `S`, every requirement on an open package comes from the root or from a release in `S`, so the release of `S` for the package taken next is in every required range, and its dependencies on chosen packages are met because those releases are in `S` too. So the release of `S` is acceptable and will be tried, unless an earlier one leads to a solution first. Every step chooses one package, and each choice is undone only after all its continuations failed, so the search ends, and it fails only when no resolution exists. Because the order of packages and of releases is fixed, the first solution it finds is the same in every implementation.

Explanation: leaving constraints out can only make a resolution easier to find. A resolution of a set of constraints, cut down to the packages that a smaller set still needs, is a resolution of the smaller set, since every requirement of the smaller set is also one of the larger. So when the pass keeps a constraint `c`, the constraints in force without `c` could be resolved at that moment, and the constraints left at the end are a subset of those, so they can be resolved without `c` as well. Every kept constraint is necessary, and the set as a whole still cannot be resolved, because the pass only ever leaves out constraints whose absence keeps it unsatisfiable.

### Complexity

- Time: O(L) per version or range of length L; O(V^P) per search in the worst case; O(C) searches per explanation — parsing reads each character a constant number of times; the search can, in the worst case, try every combination of the releases of the packages it touches, which is exponential; `explain` runs one search per constraint, plus the first one.
- Space: O(R + P) for R published releases and P packages — the registry holds every release with its expanded ranges, and the search holds one chosen release and one stack frame per package.

### Trade-offs

- The exponential worst case is not an accident of this search. Choosing versions is hard in general: given a formula in conjunctive normal form, make a package for each variable with the releases 1.0.0 (true) and 2.0.0 (false), and a package for each clause with one release per literal, each depending on its variable with `=1.0.0` or `=2.0.0`; the root requires every clause package. A resolution exists exactly when the formula can be satisfied. Real registries are rarely that adversarial, and the search is fast on them.
- A resolver that learns from conflicts (it keeps, for every failure, the combination of choices that caused it, and refuses that combination from then on) would not try the same dead end twice, and its learned rules could serve as the explanation. It is much harder to write and to specify exactly, which is why this problem uses a plain search and a separate explanation pass.
- The deletion pass in `explain` finds a set where every member is necessary, which is not always the smallest such set: two independent conflicts give two different answers depending on the order. Finding the smallest is far more expensive, and a necessary set is what a reader needs.
- Expanding ranges once, at publish time, and comparing parsed keys keeps every search step to integer comparisons. Parsing on every comparison would be simpler and much slower inside the search.

### Pitfalls and edge cases

- Precedence is not string order (`1.10.0 > 1.9.0`, `beta.11 > beta.2`), and build metadata never breaks a tie: `sortVersions` breaks it by text instead.
- `01a` is a valid alphanumeric identifier, `01` is not a valid numeric one, and digits in build metadata may start with `0`. Empty identifiers (`1.0.0-alpha..1`, a trailing `-` or `+`) are invalid.
- `^0.2.3` stops before `0.3.0` and `^0.0.3` before `0.0.4`, while `^0.0` (a partial version) stops before `0.1.0`. `~1` allows every 1.x, not only patches of 1.0.
- Upper bounds are written `<2.0.0-0`; `expandRange` must print the `-0`.
- The pre-release rule looks at the same core in the same set: `1.3.0-beta` is not in `>=1.2.0-alpha <1.4.0`, although `1.2.0-beta` is, and `*` admits no pre-release.
- In the search, compute the requirements from the current choices every time. A list of requirements that only grows keeps the ranges of a release after the search has undone it, and blocks valid answers. A result built from every release ever chosen lists packages that nothing needs any more.
- An acceptable release also has to agree with the packages that are already chosen; without that check the search accepts a release whose dependency contradicts an earlier choice, and no later step looks at it again.
- The order of packages is by name, not by the order in which they are first required, and the two give different answers on the hidden cases.
- Lock entries are matched by the version text as published, and they only reorder the releases tried; a locked version that is no longer acceptable is skipped like any other.

### Language notes

- Python compares tuples element by element, so the key `(major, minor, patch, flag, ((kind, number, text), ...))` sorts correctly with no comparison function. The other languages write a `compare` function that walks the same fields.
- TypeScript, Java and Kotlin compare strings by UTF-16 code units, Go and Rust by bytes, and Python by code points; on printable ASCII all of them agree, which is the order the statement asks for.
- Every number in the tests fits a 32-bit integer even after adding one, so Java and Kotlin `int`, Go `int`, Rust `u32` and TypeScript `number` are all exact.
- Java and Kotlin sort with a `Comparator` built from the version comparison and then the text; Go uses `sort.SliceStable`; Rust's `sort_by` takes a closure that returns an `Ordering`, and its tuples and vectors compare lexicographically like Python's.
- The search is recursive; its depth is the number of packages it touches, at most a few dozen in the tests, so no language needs an explicit stack. Go and Rust pass the set of chosen releases by reference and remove an entry when a choice is undone, instead of copying the map.

## Further reading

- [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html): the meaning of major, minor and patch numbers (items 4 and 6 to 8), pre-releases (item 9), build metadata (item 10), precedence (item 11, with the example list used in level 1), and the grammar of valid versions.
- [node-semver: Ranges](https://github.com/npm/node-semver#ranges): documentation of a widely used range grammar, with comparators, `||` sets, X-ranges, tilde and caret ranges, and the rule that lets a pre-release into a comparator set only when a comparator on the same `[major, minor, patch]` names one. Level 2 follows its expansions of `^`, `~` and wildcards, but its grammar is a subset of the README's and stricter in places: the README reads an empty range as `*`, which this problem rejects, and it has hyphen ranges such as `1.2.3 - 2.3.4`, which this problem leaves out.
