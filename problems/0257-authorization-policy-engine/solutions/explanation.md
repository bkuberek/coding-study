# Authorization Policy Engine: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| walk-per-check | optimal | O(r + e + k + d) per check, O(1) per other call | O(r + e + k) | default answer |

For one check, `r` and `e` are the roles and inheritance edges reached from the principal, `k` the rules of those roles, and `d` the number of segments in the resource.

## Approach: walk-per-check (Walk the roles once per check and compare each rule against the resource's ancestors)

### Intuition

Three independent questions hide inside one call. Which roles does this principal really have? That is reachability in a graph. Which rule resources cover this one? That is the set of its ancestors. Do any rules match both, and does one of them say no? That last part has no notion of priority at all: it is `any(deny)`, then `any(allow)`, then no. Keeping the three apart makes the decision independent of the order the rules were written in, which is what you need when the rules are data.

Failing closed is the other half. The last line of the function returns a refusal, so a missing rule, a typo in a role name or an empty table can only ever take access away.

### Algorithm

1. Build the set of resources that cover the request: `*`, the resource itself, and each ancestor made by dropping whole segments from the end.
2. Walk the roles from the principal's assigned roles along `inherit` edges, with one visited set.
3. For each role reached, test each of its rules: the action equals the request or is `*`, and the resource is in the covering set.
4. An applicable `deny` returns `"deny"` at once. An applicable `allow` is only remembered, because a deny may still come.
5. After the walk, return `"allow"` if one was remembered, and `"default-deny"` otherwise.

### Correctness

The walk visits exactly the roles reachable from the principal's assigned roles, and the visited set means each role is expanded once, so it ends on any graph, cycles included. The covering set holds exactly the resources the statement lets apply, since each ancestor is cut at a separator and so never ends mid-segment. Every rule of every reached role is tested unless a deny has already decided, so a deny that applies is always found, and `"allow"` is returned only after every applicable rule has been seen without a deny. Nothing is stored between checks, so each answer reflects everything added so far.

### Complexity

- Time: O(r + e + k + d) per check, O(1) per other call — the walk is linear in the reached roles and edges, each of their rules is tested once with set lookups, and the covering set has at most `d + 1` entries. The other calls only append.
- Space: O(r + e + k) — the stored edges, assignments and rules, plus one visited set and one covering set during a check.

### Trade-offs

Walking the graph on every check is simple and always current. Most checks in a real system would rather read a cached closure of each role's rules, and that is fine as long as you invalidate it, but this is exactly where stale permissions come from: a deny added a second ago that does not apply yet. Start from the uncached version, and add a cache only with a measurement and an invalidation rule in hand.

Indexing rules by resource instead of by role turns the rule scan into a few lookups, which helps when one role has thousands of rules. A trie over the segments does the same, and it helps more if segment wildcards ever arrive.

Deny-overrides is easy to reason about but blunt: you cannot carve out an exception to a deny. The usual alternatives are most-specific-wins or an explicit order. Both let one forgotten rule grant access, which is why deny-overrides is the safer default for security-sensitive rules.

### Pitfalls and edge cases

- **First match wins.** Scanning and returning on the first applicable rule makes the answer depend on the order rules were added (`h1`).
- **Most specific wins.** It feels right, and it lets an allow on a child escape a deny on its parent (`ex2`, `h9`).
- **String prefixes for paths.** `startsWith("docs/alpha")` also covers `docs/alphabet` and `docs/alpha-two` (`h3`). Compare at segment boundaries.
- **Ancestors point one way.** A rule on a child says nothing about its parent (`h2`, `h4`), and segments are ordered, so a rule on `q3/alpha` does not cover `alpha/q3` (`h11`).
- **Inheritance points one way.** The role gets the parent's rules, and not the reverse (`ex1`, `h5`).
- **A deny through inheritance is still a deny.** A role's own allow does not beat a deny from a parent, or from an unrelated role the principal also holds (`h7`, `h8`).
- **Recursion without a visited set never ends** on a cycle (`ex3`, `h12`, `h13`).
- **A visited set that only tracks the current path** ends on a cycle, but it is exponential when many paths lead to one role: 40 diamonds in a row mean 2^40 paths (`h14`).
- **Memoizing each role's rules during the walk.** On a cycle, a role that is reached while its neighbour is still being computed gets a partial answer, and it stays wrong after the walk (`h12`).
- **Caching answers.** A check must see a rule, an assignment or an edge added a moment ago (`h15`).
- **Wildcards on one side only.** `*` works for a deny as well as for an allow (`h9`, `h10`), and a deny on one action does not touch another (`h9`).
- **`deny` and `default-deny` are different answers,** although a caller treats them alike. Merging them loses the audit trail (`h16`).
- Names are case-sensitive (`h17`), duplicates change nothing (`h18`), and one principal's roles are not another's (`h19`).

### Language notes

- Python: an explicit stack avoids the recursion limit, and `rpartition` drops the last segment. Reading through `dict.get(key, ())` keeps a `check` from adding empty entries, which a `defaultdict` would do.
- TypeScript: `lastIndexOf(separator, end - 1)` walks the separators from the right without allocating the segments. `Set` iterates in insertion order, but the decision does not depend on the order.
