# Referral Rewards

## Statement

Build `ReferralProgram`, the bookkeeping behind a "bring a friend" scheme. A person joins because somebody referred them, and the person who referred them earns a bonus. The program records who referred whom, pays the bonuses, and answers questions about the whole network of referrals: how many people did somebody bring in, directly or through the people they brought in, and who is the top referrer? The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is a graph?** A graph is a set of things (here people) and links between them (here referrals). Draw each person as a dot and each referral as an arrow from the person who referred to the person who was referred: `ann -> bob` means "ann referred bob". Here a person can join only once, so every person has at most one arrow pointing at them, and the arrows form chains and branches:

```text
ann -> bob -> dee -> eve
  \
   -> cy -> fay
```

`ann` referred `bob` and `cy` *directly*. `ann` also brought in `dee`, `eve` and `fay` *indirectly*, through the people she referred. Bonuses are paid for direct referrals only, but the counts of the later levels include both kinds. The picture is also where the trouble comes from: input is not always tidy, and the later levels deal with repeated referrals, with referrals that go round in a circle, and with networks too big to walk by calling a function once per person.

Aim to finish in 90 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 25, level 2 by 45, level 3 by 65 and level 4 by 85, keeping the last minutes for a final run.

## Input

- `ReferralProgram(bonus)`: creates an empty program in which every counted referral earns its referrer `bonus` points.
- A person is a name: 1 to 20 printable ASCII characters (codes 32 to 126). Names are case sensitive, so `Ann` and `ann` are two people, and they are compared by the numeric value of their characters, so capital letters come before lowercase ones, digits before letters and a space before everything else.
- Each level's section describes the methods it adds and their parameters.

## Output

Methods that record a referral return the points it earned. Questions return a number, a name or a list of names. A person who is not in the program has no points, no referrals and a total of 0.

## Level 1: Bonus for each referral

At this level the referrals you receive are tidy: a referral never names the same person on both sides, and none closes a loop (it never names a person who is, directly or through other people, the one who referred the referrer).

- `refer(referrer, referred)`: records that `referrer` referred `referred`, and returns the points this earns. **The first referral that names a person is the one that counts.** If `referred` has not been referred before, the referral counts: `referrer` earns `bonus` points, and the call returns `bonus`. If `referred` has already been referred, by the same person or by anybody else, the call earns nothing, returns `0` and changes nothing: nobody is paid twice for the same person.
- `points(person)`: the points the person has earned in all, `bonus` for each referral of theirs that counted.
- `referralsOf(person)`: the people whose referral by this person counted, in the order the referrals were counted.

### Example 1

<!-- case: ex1 -->

`ann` refers `bob` and `cy` and is paid twice. Her second referral of `bob` pays nothing, and neither does `dan`'s referral of `bob`, because `bob` was already referred. `dan` ends with no points and no referrals.

### Example 2

<!-- case: ex2 -->

With a bonus of 25, a chain of three referrals pays 25 to each of the three referrers. Being referred does not stop `bob` from referring `cy`, and it earns him nothing. A name nobody has used has no points and no referrals.

## Level 2: Chains of referrals

The referrals are still tidy. A person's **total** is the number of people they brought in, directly or not: their direct referrals, the people those referred, and so on down. It never counts the person themself.

- `totalReferrals(person)`: the total of that person.
- `topReferrer()`: the name of the person with the largest total. Ties are settled in this order: the person with more direct referrals comes first; if those are equal too, the smaller name by character value. Only people with a total of at least 1 can be the top referrer, and the answer is `""` when nobody has one.

The answers always follow the referrals counted so far, however the calls are mixed.

### Example 1

<!-- case: ex3 -->

`ann` brought in `bob` and `cy` directly, `dee` through `bob`, `eve` through `dee`, and `fay` through `cy`: a total of 5. `bob` brought in `dee` and `eve`, so 2, and `eve` brought in nobody. `ann` has the largest total.

### Example 2

<!-- case: ex4 -->

`q` and `p` both have a total of 2. `p` referred two people directly and `q` only one, so `p` is the top referrer. When `a` also reaches 2 with two direct referrals, the tie is on the name, and `a` is the smaller one.

## Level 3: Repeats and loops

From this level, referrals may be repeated, may contradict one another, and may go round in a circle. Every referral is checked against these rules, **in this order**, and the first rule that applies decides:

1. **Loop.** `referrer` and `referred` are the same name. Not counted.
2. **Repeat.** `referred` has already been referred by this same `referrer`. Not counted.
3. **Rival.** `referred` has already been referred by somebody else. Not counted: the first referral stays.
4. **Loop.** Following the referrals backwards from `referrer`, from person to the person who referred them, reaches `referred`. Counting this referral would make `referred` their own referrer through a circle. Not counted.
5. Otherwise the referral counts, exactly as before.

A referral that does not count earns nothing, returns `0` and changes nothing: it does not add a person to the program, and it does not change a total or a list. Everything else is as in the earlier levels.

- `referAll(rows)`: takes a list of referrals, each a list `[referrer, referred]`, and applies them one after another, as if `refer` had been called for each. It returns four numbers `[counted, repeats, rivals, loops]`: how many referrals counted, and how many were rejected as a repeat (rule 2), as a rival (rule 3) and as a loop (rules 1 and 4). `refer` and `referAll` can be mixed.

### Example 1

<!-- case: ex5 -->

`referAll` counts `a -> b` and `b -> c`. The second `a -> b` is a repeat, `d -> c` is a rival (`c` was referred by `b`), `c -> a` would close the circle `a -> b -> c -> a`, and `e -> e` names the same person twice. The last row, `c -> b`, is a rival and not a loop: `b` already has a referrer, so rule 3 decides before rule 4 is asked. The summary is `[2, 1, 2, 2]`.

### Example 2

<!-- case: ex6 -->

`y -> x` closes a loop, because `x` referred `y`. The same goes for `z -> x` once `y -> z` counted: the chain is `x -> y -> z`, and a referral back to the top of a chain from anywhere in it is a loop. Rejected referrals pay nothing and leave no trace.

## Level 4: A million people

- `leaderboard(k)`: the names of the first `k` people of the ranking by total, best first, using the ordering of `topReferrer`: larger total, then more direct referrals, then the smaller name. Only people with a total of at least 1 are ranked, so the list is shorter than `k` when fewer of them exist, and empty for `k = 0`. `topReferrer()` is the first name of `leaderboard(1)`.

The new demand is size. A single `referAll` can hold a million referrals, and a chain of a million people is possible. A solution that recurses once per person runs out of stack long before that, so walk the network with an explicit queue or stack of your own, and decide a loop in near-constant time instead of walking up the chain for every referral: climbing ten times a million steps is the time of a coffee break. A case with more than 10,000 people never adds a referral after it has asked its first question about totals or the board, so totals can be counted once for each batch of referrals.

### Example 1

<!-- case: ex7 -->

`ann` has a total of 6 and three direct referrals, `bob` a total of 2, and `cy` a total of 1; everybody else has none and is not ranked. A board of 2 holds the first two, a board of 10 holds the three that exist, and a board of 0 is empty.

### Example 2

<!-- case: ex8 -->

Four people have a total of 2. `k` and `t` have two direct referrals each, and `j` and `u` one: so `k`, `t`, then `j`, `u`, and inside each pair the smaller name comes first.

## Constraints

- `1 <= bonus <= 1000`.
- At most 5,000 calls per test, and at most 10^6 referrals in all, counting the rows of every `referAll`.
- A name is 1 to 20 printable ASCII characters.
- `0 <= k <= 10^6`.
- A case with more than 10,000 people never adds a referral after it has asked its first question about totals or the board.

## Follow-ups

- Pay indirect bonuses too: half a bonus to the referrer's referrer, a quarter to the next one, and so on. What would you keep per person, and how does a referral that attaches a whole tree below a new referrer change the points of everybody above?
- A person leaves the program and their referrals are re-attached to their own referrer. Which totals change, and how would you update them without a full recount?
- Allow a person to be referred by several people, and count each person once however many ways lead to them. Why is a total no longer the sum of the totals below, and why does it get so much harder?
- Return the top `k` without sorting everyone: a heap of size `k` takes O(n log k).

## Hints

### Hint 1

Keep two lookups. The first answers "who referred this person?": a dictionary (map) from the referred person to their referrer. Before you pay for a referral, ask it: if the referred person is already in it, nothing is paid. The second answers "whom did this person refer?": a dictionary from a referrer to a list of names, appended to in the order the referrals count.

### Hint 2

Points need no extra bookkeeping: a person's points are `bonus` times the length of their list of counted referrals.

### Hint 3

A person's total is the sum, over their direct referrals, of 1 plus that person's own total. For the top referrer, compute every total, then pick the best with a sort key that is a tuple: the negative total, the negative number of direct referrals, and the name. Python and most languages compare tuples one field at a time.

### Hint 4

Do not recount on every call if nothing has changed: keep the totals, and throw them away only when a referral counts. For a case with many referrals followed by a few questions, you then count once.

### Hint 5

For the rules of level 3, write the checks in the order of the statement, and let each return early. For a loop, climb from `referrer` through the dictionary of "who referred this person", and stop at the top of the chain: if you meet `referred` on the way, it is a loop.

### Hint 6

Climbing is fine for 1,000 people and fatal for 10^6, since a chain a million long makes each check a million steps. Use a union-find: every person starts in a group of their own, and a counted referral merges two groups. When `referred` has no referrer, it is the top of its group, so the referral would close a loop exactly when `referrer` is already in the same group.

### Hint 7

To count totals without recursion, list the people so that everyone comes after their referrer: start with the people who have no referrer, then add the people they referred, and so on, with a queue. Then walk that list *backwards* and add each person's total plus one to their referrer's total. When you reach a person, everyone below them has already been added.
