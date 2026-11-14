# Org Chart Outline

## Statement

Build `OrgChart`, the core of a company directory. The company's people are stored as a flat list of rows, one row per person, and each row says who that person reports to. A flat list is easy to store but hard to ask questions of: "who reports to this person?", "who is the lowest manager above both of these people?", "what does the whole company look like, indented?". Your class turns the list into something that answers these questions quickly. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is a tree?** A tree is a set of things in which every thing has at most one *parent*, and following parents upward always ends somewhere: at a thing with no parent, the *root*. A company is a tree when every person has at most one manager and the chain of managers ends at the person at the top. Here is a small company, and the rows that describe it:

```text
Ada
  Grace
    Ken
    Dennis
  Linus
    Margaret
```

Each row is `[id, parentId, name]`, for example `["dev1", "eng", "Ken"]` says that the person with id `dev1` is named Ken and reports to the person with id `eng`. The person at the top has an empty `parentId`, `""`. The row alone gives you only the upward link, from a person to their manager. Most questions go the other way, from a manager down to their reports, so the first job is to turn each parent link into a child list: for every person, the ids of the people who point at them.

Aim to finish in 75 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 25, level 2 by 45, level 3 by 55 and level 4 by 70, keeping the last minutes for a final run.

## Input

- `OrgChart()`: creates an empty chart.
- A **row** is a list of three strings: `id`, `parentId` and `name`. The `id` is not empty and no two rows share an id. The `parentId` is the id of the person's manager, or the empty string `""` for a person with no manager. The `name` is any text, empty included. Ids and names use only printable ASCII characters (codes 32 to 126), and text is compared exactly as given, with no case folding.
- Ids are case sensitive and are compared as text: `"10"` is smaller than `"9"`.
- Each level's section describes the methods it adds and their parameters.

## Output

Methods that build something return nothing. Lists of ids come back in the order the level states. A question about an id that is not in the chart gets the empty answer: `[]` for a list, `""` for a string, `0` for a number.

## Level 1: Reports of each person

At this level the rows describe one tree, or nothing at all: at most one row has an empty `parentId`, and every other row names a manager whose own row comes earlier in the list.

- `load(rows)`: replaces the whole chart with the given rows, which may be empty. Nothing of an earlier chart is kept.
- `roots()`: the ids of the rows whose `parentId` is `""`, in the order of the rows. At this level that is one id, or none for an empty chart.
- `nameOf(employee)`: the name in the row with that id.
- `children(employee)`: the ids of the rows whose `parentId` is `employee`, in the order of the rows. A person with no reports gets `[]`.

The order matters: the children of a person come in the order their rows appear, not sorted by id or by name.

### Example 1

<!-- case: ex1 -->

The company drawn above. `ceo` has two reports, `eng` and `ops`, in the order of the rows, and `dev1` has none. The last call asks for an id that is not in the chart.

### Example 2

<!-- case: ex2 -->

The children of `r` are `c`, `a` and `b` because that is the order of their rows, even though `a`, `b`, `c` would be alphabetical. The same goes for `a2` and `a1`.

## Level 2: Rows in any order

Real data is messy. From this level, rows may come in any order, a manager's row may come after the rows of their reports, and the rows do not have to form one tree. Ids are still unique. Three kinds of row need a rule:

- A **root** is a row with `parentId` `""`. There may be any number of them.
- An **orphan** is a row whose `parentId` is not empty and is not the id of any row: its manager was never listed. An orphan is *not* attached to some made-up manager and it is not thrown away: it is treated as the top of its own tree, with its reports below it, and it is reported by `orphans()`.
- A **cycle** is a group of rows whose parent links go round in a circle, for example `a` reports to `c`, `c` to `b` and `b` to `a`. A row that reports to itself is a cycle of one. A cycle has no top, so none of its rows belongs to a tree, and neither do the rows that hang below it. Cycles are reported as an error by `cycles()`.

A row is **attached** when following its parent links, upward, ends at a root or an orphan. The tops of the chart are its roots and its orphans. A row on a cycle, or below one, is not attached.

- `orphans()`: the ids of the orphans, in the order of the rows. The reports of an orphan are not orphans.
- `cycles()`: a list with one entry for each cycle, and `[]` when there is none. An entry lists the ids of the cycle by following the parent links: it starts with the member whose row comes first in the input, then its manager, then that person's manager, and so on until the next one would be the first again. The entries are ordered by the position of their first member in the input.
- `children`, `nameOf` and `roots` behave as before for every row, attached or not: a row on a cycle still has the rows that report to it as its children.

Whatever the order of the rows, the same rows give the same roots, orphans and cycles as sets; the order of the rows only decides the order of the lists.

### Example 1

<!-- case: ex3 -->

The rows arrive deepest first. `ceo` is the one root. `tmp` reports to `hr`, who has no row, so `tmp` is an orphan, and `intern` below it is not. `cycles` is empty.

### Example 2

<!-- case: ex4 -->

`a` reports to `c`, `c` to `b` and `b` to `a`, so they form a cycle. `a` comes first in the input, so the entry is `[a, c, b]`: `a`, then its manager `c`, then that person's manager `b`. The row `s` reports to itself and is a cycle of one. Neither is a root or an orphan, and `children("a")` still lists `b`, whose row says `a`.

## Level 3: Managers and chains

- `chain(employee)`: the reporting chain of a person: their own id first, then their manager, then that manager's manager, and so on up to the top of their tree, the root or the orphan. A root's chain is just its own id. The chain is `[]` for an id that is not in the chart, and for a row that is not attached.
- `lowestCommonManager(first, second)`: the lowest person who is on the chain of both. A person is on their own chain, so if `first` manages `second` the answer is `first`, and for the same id twice the answer is that id. The answer is `""` when either id has an empty chain, and when the two chains share no one: for example two people in different trees.

### Example 1

<!-- case: ex5 -->

`dev2` reports to `eng`, who reports to `ceo`. `dev1` and `dev2` meet at `eng`, `dev1` and `sre` meet at `ceo`, and a manager and their report meet at the manager. The last call names someone who is not in the chart.

## Level 4: Indented outline

- `subtreeSize(employee)`: the number of people in the subtree of an attached row: the person and all the people below them, directly or not. A person with no reports has size 1. It is `0` for an id that is not in the chart and for a row that is not attached.
- `outline(order)`: the whole chart as a list of lines, one for each attached row, parents before their reports (depth first: a person, then the whole subtree of their first report, then the next report, and so on). A line is the indent, then the name, then a space, then the id in parentheses: `Ken (dev1)`. The indent is two spaces for each level below the top, so a top has none, its reports have two, and so on. The `order` decides in what order the siblings are listed, and also the order of the tops among themselves:
  - `"input"`: in the order of the rows.
  - `"name"`: by name, then by id. Texts are compared by the numeric value of their characters, so capital letters come before lowercase ones, digits before letters and a space before everything else.
  - `"size"`: the larger subtree first, then by name, then by id, as above.

Rows that are not attached do not appear. An empty chart has an empty outline.

An outline of a big chart is where a solution that calls itself once per level of the chart runs out of stack: a chain of 100,000 managers is 100,000 calls deep. Build the lines with an explicit stack of your own, and compute the subtree sizes without recursion too.

### Example 1

<!-- case: ex6 -->

The first outline lists the siblings in the order of the rows, the second by name, so `Dennis` comes before `Ken`. The sizes count the person: `ceo` is 6 people, `eng` is 3, `dev1` is 1, and an unknown id is 0.

### Example 2

<!-- case: ex7 -->

`Bob` has the largest subtree (3 people), then `Cy` (2), then `Ann` (1), so the size outline puts them in that order. Inside `Bob`'s subtree, `Bao` and `Bea` have the same size and `Bao` is first by name. The name and input outlines show the other two orders on the same chart.

## Constraints

- At most 5,000 calls per test, and at most 10^5 rows in each `load`.
- `id` and `parentId` are at most 20 characters; a `name` is at most 30 characters.
- `order` is one of `"input"`, `"name"` and `"size"`.
- The outline of a chart has at most 5 million characters in total, so a very deep chart is explored with `chain`, `lowestCommonManager` and `subtreeSize` instead.

## Follow-ups

- A chain of 100,000 managers has an outline of about 10^10 characters. How would you print it without building it all in memory?
- `lowestCommonManager` takes time proportional to the depth. How would you answer it in O(log n) after O(n log n) preparation (binary lifting), or in O(1) after O(n) preparation (an Euler tour and a range minimum)?
- A person changes manager. Which of the answers of every level change, and how much of the index can you keep?
- The rows arrive one at a time and a person may be mentioned as a manager long before their own row. How would you keep the orphans and the sizes up to date?

## Hints

### Hint 1

Each row says "this person reports to that person". To list a person's reports you need the opposite: for each person, the people who point at them. Make a dictionary (a map) whose keys are person ids and whose values are lists of ids. Go through the rows once, in order, and for each row add its `id` to the list of its `parentId`. Because you go in order, each list ends up in the order of the rows.

### Hint 2

A root is a row whose `parentId` is `""`, so the key `""` of the same dictionary holds the roots. Keep a second dictionary from id to name, and answer `nameOf` and `children` by looking things up. A missing key is the empty answer.

### Hint 3

Do not assume the manager's row comes before the report's row. Make one pass to remember every id, and only then decide what each row is: a root if its parent is empty, an orphan if its parent is not empty and is not a known id. A cycle never shows up in this pass, because every row on it has a known parent.

### Hint 4

To find what is attached, start from the tops and go down through the child lists, level by level, with a queue. Every row you reach is attached. A row you never reach is on a cycle or below one. Then follow the parent links from each unreached row: you either walk into a row you have already seen, or you come back to a row of the current walk, and that is a cycle.

### Hint 5

For the chain, climb with `parent = parents[parent]` until the parent is not a known id. For the common manager, put one chain in a set and walk up the other until you find a member of the set.

### Hint 6

For the outline, keep a stack of `(id, depth)` pairs. Pop one, write its line, then push its children in *reverse* order, so that the first child is the next one popped. Sort the children as the `order` says before you push them.

### Hint 7

Subtree sizes need the children before the parents. The queue of hint 4 lists every parent before its reports, so go through it backwards and add each row's size to its parent's size. That is a loop, not a recursion, and it takes O(n).
