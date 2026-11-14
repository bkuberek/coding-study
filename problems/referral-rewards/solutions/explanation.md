# Referral Rewards: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| forest-counts | optimal | O(1) amortized per referral; O(n) per recount after a change; O(n log n) per leaderboard | O(n) | default answer; one structure serves all four levels |

Here `n` is the number of people who appear in a counted referral.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Pay once for each referred person | `index` (name to number), and per person a `referrer`, a list of referrals kept as `first`, `last` and `next`, and a `direct` count |
| 2 | Totals and the top referrer | `totals`, rebuilt by one breadth-first pass and thrown away (`None`) whenever a referral counts |
| 3 | Repeats, rivals and loops | a union-find (`parentSet`, `setSize`) over the people, and one function, `apply`, that classifies a row and records it |
| 4 | Ranking and size | `leaderboard`, a sort of the people with a total above zero; nothing new is stored, but every walk is iterative |

The early choice that makes the later levels cheap is the single `apply` function. `refer` and `referAll` both call it, so the first rule of the statement ("the first referral that names a person counts") is written once and level 3 only adds two checks in front of the part that records. A solution that pays inside `refer` and bolts the loop check on later has to find every place that records a referral.

## Approach: forest-counts (Forest in arrays with a union-find for loops and one breadth-first recount)

### Intuition

Because only the first referral that names a person counts, the counted referrals give every person at most one referrer, so they form a forest of trees. A tree is the right shape for everything the levels ask: a total is the size of a subtree minus one, a loop is a referral that joins a tree to itself, and the ranking is a sort over the subtree sizes. The only hard part is doing this for a million people, which rules out recursion and rules out climbing the tree for every loop check.

### Algorithm

1. Number the people in the order they first appear in a counted referral, with a map from name to number. Per person keep `referrer` (none at first), `first`, `last` and `next` (a linked list of the people they referred, in the order counted), `direct` (the length of that list) and a union-find entry.
2. `apply(referrer, referred)` classifies a row, in the order of the statement. The same name twice is a loop. If `referred` is known and has a referrer, it is a repeat when that referrer is the same name and a rival otherwise. Otherwise find the groups of the two people: if they are the same group, `referred` is the top of its group and `referrer` is below it, so the row would close a loop. If not, the row counts: merge the groups (by size), set `referrer[referred]`, append `referred` to the list of `referrer`, add one to `direct`, and forget the totals.
3. `refer` returns `bonus` when `apply` says the row counted and `0` otherwise. `points` is `direct * bonus`, and `referralsOf` walks the linked list. `referAll` calls `apply` for each row and counts the outcomes.
4. The totals come from one pass. List the people with no referrer, then extend the list with the people they referred, level by level, so every person comes after their referrer. Go through the list backwards and add `total + 1` of each person to their referrer's total.
5. `leaderboard(k)` sorts the people with a total above zero by the negative total, the negative `direct` and the name, and returns the first `k` names. `topReferrer` is `leaderboard(1)`.

### Correctness

Invariant of `apply`: every counted referral goes to a person who had no referrer, so each person has at most one referrer; and the groups of the union-find are exactly the trees of the forest, because a group changes only when a counted referral joins two trees. For a row whose `referred` has no referrer, `referred` is the root of its tree. Following the referrals backwards from `referrer` reaches `referred` exactly when `referrer` is in that tree, that is, when the two are in the same group. So the group test is the loop test of the statement, and rejecting such a row keeps the forest free of loops, which is why the climb of the totals ends.

Totals: the list built in step 4 contains every person once (each has one referrer or none, so each tree is reached from its root), with every referrer before the people they referred. Going through it backwards, a person is processed after everyone below them, so their total is final when it is added to the referrer. A total of a person is therefore the number of people below them, and the tie-break of the statement is a total order, since names are unique.

### Complexity

- Time: O(1) amortized per referral; O(n) per recount after a change; O(n log n) per leaderboard — `apply` does a map lookup, two union-find searches that cost O(α(n)) with path halving and union by size, and a few array writes; a recount visits each person twice; the leaderboard sorts up to n people.
- Space: O(n) — the map, the arrays of the forest, the union-find and the totals each hold a constant number of entries per person.

### Trade-offs

- Climbing the referrers from `referrer` to look for `referred` is simpler and is O(depth) per row. It passes level 3 and fails level 4: a chain of 100,000 people makes the whole input quadratic.
- Keeping the totals up to date on every referral (adding one to every ancestor) makes a total O(1) to read but a referral O(depth), which is worse than a recount for a batch of referrals followed by a few questions. The recount is paid only when a question follows a change.
- Sorting everyone for `leaderboard` is O(n log n) even for `k = 1`. A heap of size `k` gives O(n log k); `topReferrer` alone is a single O(n) scan for the best person.
- Linked lists in arrays use less memory than a list per person, which matters at a million people, and keep the order of the referrals.

### Pitfalls and edge cases

- Paying for a repeat: the same referral twice, or a second referrer for the same person, must not pay again. The first referral that names a person is the only one that counts.
- Summing only direct referrals for a total, or adding the person to their own total.
- A cache that is not thrown away: the top referrer after another referral is the case that finds it. A cache that is thrown away on every call is too slow at level 4.
- Checking the loop before the rival: `c -> b` where `b` was referred by `a`, who is above `c`, is a rival and not a loop, and the summary counts it that way.
- Creating a person for a row that does not count: a rejected row leaves no trace, so `points` and `referralsOf` of a name seen only in rejected rows are empty.
- Breaking a tie on the name by locale or by case: the name is compared by character value, so `B` comes before `a`.
- Recursion depth: the hidden case with a chain of 1,500 referrals fails a recursive solution in Python, and the generated case with a chain of 100,000 fails the recursive solutions of every language.
- Climbing for the loop check: correct, and quadratic on a long chain.

### Language notes

- Python sorts with a key tuple, `(-total, -direct, name)`, and its strings compare by code point, as the statement says. TypeScript compares strings with `<` and `>` by UTF-16 unit, Java and Kotlin `String.compareTo` does the same, and Go and Rust compare by bytes; all four agree for ASCII.
- Java and Kotlin keep the arrays of the forest in a small growable array of `int` rather than in `ArrayList<Integer>`, which would box a million integers eight times over. Go and Rust grow ordinary slices and vectors.
- Rust takes its parameters by value, so `refer` and `referAll` borrow the names for `apply` and clone a name only when a new person is stored.
- The result of `referAll` is a list of four numbers; Go returns `[]int`, Rust `Vec<i32>`, and the others the language's list of integers.
