# Village Paths: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| relabel-group | brute | O(n) per addPath, O(1) for the other calls | O(n) | there are few villages, or paths are rare compared with questions |
| disjoint-set-forest | optimal | O(α(n)) amortized per call | O(n) | default answer; paths and questions come in any mix |

`n` is the number of villages and α is the inverse Ackermann function, which grows so slowly that it is at most 4 for every `n` below 2^65536. Over a generated sequence with `n` villages and 3n calls, relabelling costs about n^2 steps and the forest costs about n steps.

## Approach: relabel-group (Give each group a label and relabel one whole group on every merge)

### Intuition

Give every group a name and write the name of its group next to each village. Then "are these two together?" is "do their names match?", and the size of a group is a count kept per name. The price is paid when two groups merge: every village that carried one name has to be rewritten with the other.

### Algorithm

1. `label[v]` starts as `v`, `members[g]` as 1 and the group count as `villages`.
2. `addPath(a, b)`: if `label[a] == label[b]`, return `false`. Otherwise rewrite every village whose label is `label[b]` to `label[a]`, add the dropped group's member count to the kept one, decrease the group count and return `true`.
3. `canReach(a, b)` compares the two labels.
4. `groupSize(v)` reads `members[label[v]]`, and `groupCount()` returns the counter.

### Correctness

Invariant: two villages have the same label exactly when they are in the same group, `members[g]` is the number of villages with label `g`, and the counter is the number of different labels in use. A merge rewrites one whole label to the other, which turns two groups into one, adds their member counts and lowers the counter by one, so the invariant holds again. The queries read the invariant directly.

### Complexity

- Time: O(n) per addPath, O(1) for the other calls — a merge scans all `n` villages to find the ones to rewrite; the other calls read an array. A sequence with about `n` merges costs about n^2.
- Space: O(n) — two arrays of length `n`.

### Trade-offs

It is the simplest correct design, and it makes questions as cheap as they can be. Its weakness is the merge, which touches every village even when the groups are tiny; keeping a list of members per group and relabelling only the smaller one is a known improvement that the forest makes unnecessary.

### Pitfalls and edge cases

- `addPath(a, a)` and a path between two villages that are already together must return `false` and change nothing; checking this before the rewrite also keeps the member counts right.
- Update `members` for the kept label as well as the counter, or `groupSize` goes stale.
- Read both labels before rewriting: after the rewrite `label[b]` has changed.

### Language notes

- Python: `enumerate(self.label)` visits the list while assigning into it by index, which is safe because the list length does not change.
- TypeScript: the constructor uses `Array.from({ length: villages }, ...)` for the identity labels and `new Array<number>(villages).fill(1)` for the counts.
- Java: plain `int[]` arrays filled in a loop.
- Kotlin: `IntArray(villages) { it }` is the identity array, and the class takes `villages` as a constructor parameter that the property initializers use.
- Go: `for village, label := range m.label` may assign `m.label[village]` while ranging, because the slice is not resized.
- Rust: `iter_mut()` rewrites the labels in place through `&mut` references; the labels are `usize` so they can index `members` directly, and every method takes `&mut self` as in the other Rust designs of the catalog.

## Approach: disjoint-set-forest (Trees of villages with union by size and path compression)

### Intuition

Writing a name next to every village is more than is needed. It is enough that every village can find one agreed village of its group, a leader. Let each village point at another village of its group, and let the leader point at itself: following the pointers from any village then ends at the group's leader, and two villages are together exactly when they end at the same leader. Merging two groups is then a single pointer change, from one leader to the other.

Two small rules keep the chains of pointers short. Pointing the smaller group's leader at the larger group's leader (union by size) means a village's chain can only double in length when its group at least doubles, so no chain is longer than about log2(n). Redirecting every village passed during a search straight to the leader (path compression) makes later searches from those villages one step long. Together they give an amortized cost per call that grows like the inverse Ackermann function.

This is the structure of the tree-based method for identifying equivalence classes that Galler and Fischer published in 1964 (Communications of the ACM 7(5):301-303, doi 10.1145/364099.364331). Tarjan analysed a known set-union algorithm of this kind in 1975 and showed that the worst-case time of `m` finds mixed with `n - 1` unions is bounded by constant multiples of `m * α(m, n)`, where α is related to a functional inverse of Ackermann's function (Journal of the ACM 22(2):215-225, doi 10.1145/321879.321884). Tarjan and van Leeuwen gave a worst-case analysis of set union algorithms and their variants in 1984 (Journal of the ACM 31(2):245-281, doi 10.1145/62.2160).

### Algorithm

1. `parent[v]` starts as `v` (every village is its own leader), `size[v]` as 1 and the group count as `villages`.
2. `leader(v)`: follow `parent` from `v` until a village points at itself; then walk the same path again and set `parent` of each village on it to that leader. Return the leader.
3. `addPath(a, b)`: find both leaders. If they are equal, return `false`. Otherwise make the leader of the smaller group point at the other, add the sizes, decrease the group count and return `true`.
4. `canReach(a, b)` compares `leader(a)` and `leader(b)`; `groupSize(v)` returns `size[leader(v)]`; `groupCount()` returns the counter.

### Correctness

Invariant: following `parent` from any village ends at a leader (a village that points at itself) without a cycle, the villages that lead to the same leader are exactly one group, and `size[r]` of a leader `r` is the number of villages in its group. Compression only changes a village's pointer to the leader it already leads to, which keeps every group the same. A merge happens only between two different leaders, makes one point at the other and adds the sizes, so two groups become one and nothing else changes. Queries compare leaders or read `size` at the leader, so they follow from the invariant.

### Complexity

- Time: O(α(n)) amortized per call — with both rules, any sequence of `m` calls on `n` villages takes O(m * α(n)) (Tarjan's analysis cited above), and α(n) is at most 4 for every `n` below 2^65536.
- Space: O(n) — the `parent` and `size` arrays.

### Trade-offs

It makes merges as cheap as questions at the price of slightly more work per question than a plain array read, and it is the standard answer whenever groups only merge. It cannot split a group or list a group's members cheaply: both need extra structure. Either rule alone is already a large improvement over the relabelling approach; both together are what the almost-constant bound needs.

### Pitfalls and edge cases

- Compare leaders, not the villages themselves, and not their `parent` entries: a village's parent may be an inner village of the group.
- Keep `size` meaningful only at leaders; after a merge the dropped leader's size is stale and must not be read.
- Do the swap for union by size before changing any pointer, or the pointer ends up on the wrong side.
- `addPath(a, a)` finds the same leader twice and returns `false`.
- Do the compression after the leader is known, in a second pass, or with a recursive call; a single pass that rewrites pointers while still searching sends villages to the wrong place.

### Language notes

- Python: `self.parent[village], village = leader, self.parent[village]` assigns both sides at once, so the old parent is read before the pointer changes.
- TypeScript: destructuring swap `[leaderA, leaderB] = [leaderB, leaderA]`.
- Java: no tuple swap, so a temporary variable does it.
- Kotlin: `leaderA = leaderB.also { leaderB = leaderA }` swaps in one expression.
- Go: `m.parent[village], village = root, m.parent[village]` is a tuple assignment, and the swap is `leaderA, leaderB = leaderB, leaderA`; the unexported `leader` method is the only one that mutates on a read.
- Rust: `leader` takes `&mut self` because it compresses paths, which is why `canReach` and `groupSize` take `&mut self` too; `std::mem::swap` swaps the two leaders.
