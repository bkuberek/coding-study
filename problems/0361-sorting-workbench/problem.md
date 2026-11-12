# Sorting Workbench

## Statement

Build `SortingWorkbench`, a small bench for studying sorting algorithms. You do not just sort: each sort must be the algorithm the statement describes, step by step, and the workbench keeps a **meter** that counts the work of the most recent sort, so that a different algorithm, or the right algorithm written differently, shows up in the numbers. The API grows over four levels: each level adds one sorting algorithm to the same class, and the methods of earlier levels keep working.

**What is a sorting algorithm, and what are we counting?** To sort is to put values in ascending order. An algorithm does it with two basic actions: a **comparison** (asking which of two values is larger) and a **move** (writing a value into a different position). Two algorithms that give the same sorted list can do very different amounts of work, and that is what the meter shows: the counts depend only on the input and on the steps the statement prescribes, so every correct solution reports the same numbers.

Every sort here returns a **new** list and leaves the list it was given as it was. The meter is replaced by each sort, so it always describes the latest one. Counting is part of the specification: count exactly what each level says, and nothing else.

Aim to finish in 90 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 25, level 2 by 45, level 3 by 70 and level 4 by 85.

## Input

- `SortingWorkbench()`: creates a workbench whose meter is empty.
- `values` is a list of integers, possibly empty. `rows` is a list of rows, and each row is a list of integers (its columns); every row has the same number of columns.
- Each level's section describes the methods it adds and their other parameters.

## Output

Sorting methods return the sorted result, as a new list. `report()` returns the meter: a list of integers whose meaning each level describes. It is an empty list when nothing has been sorted yet, and reading it does not change it.

## Level 1: Insertion sort and its meter

Methods to add:

- `insertionSort(values)`: returns the values in ascending order, by insertion sort as defined below.
- `report()`: returns `[comparisons, moves]` for the latest `insertionSort`, as counted below.

**Insertion sort** works like arranging playing cards in your hand. The left part of the list is always sorted. Take the next value, called the **key**, and slide it left into its place within the sorted part: while the value just left of the key is larger than the key, move that larger value one step to the right; when the value on the left is not larger, or there is no value left of it, put the key in the gap. Then the sorted part is one value longer. In steps:

```text
for i from 1 to n - 1:
    key = a[i]
    j = i - 1
    while j >= 0:
        (comparison)  is a[j] > key ?
        if not: stop
        a[j + 1] = a[j]        (move)
        j = j - 1
    a[j + 1] = key             (placing the key: not a move)
```

**What the meter counts.**

- A **comparison** is each evaluation of `a[j] > key`. The test `j >= 0` is not a comparison of values and is not counted.
- A **move** is each time a larger value is written one step to the right. Placing the key into its gap is not a move.
- The comparison is strict (`>`): a value equal to the key is not moved, so equal values keep their order.

A worked example, `[3, 1, 2]`: the key `1` is compared with `3` (1 comparison), `3` moves right (1 move), and nothing is left of the gap. The list is `[1, 3, 2]`. The key `2` is compared with `3` (2nd comparison), `3` moves right (2nd move), then `2` is compared with `1` (3rd comparison), which is not larger, so the key stops there. The result is `[1, 2, 3]` and the meter is `[3, 2]`.

Moves have a name worth knowing: an **inversion** is a pair of positions where a larger value comes before a smaller one. The number of moves insertion sort makes is exactly the number of inversions of the input, because each move fixes one inversion.

### Example 1

<!-- case: ex1 -->

The walk-through above: three comparisons and two moves, so the meter reads `[3, 2]`.

### Example 2

<!-- case: ex2 -->

A sorted list of five values needs one comparison for each key after the first, which fails at once, and no move: `[4, 0]`. A list in reverse order is the worst case: every key passes every value before it, which is 4 + 3 + 2 + 1 = 10 comparisons and 10 moves. The second `report()` shows the latest sort only.

## Level 2: Stable merge sort by a column

Methods to add:

- `mergeSortBy(rows, key)`: returns the rows in ascending order of the integer in column `key` (counted from 0), by the merge sort defined below.
- `report()` after `mergeSortBy` returns `[comparisons]`, counted below.

**Stable.** A sort is **stable** when rows with equal keys stay in the order they had in the input. For a list of plain numbers stability does not matter, since equal numbers cannot be told apart. For rows it matters a great deal. Take rows of `[team, minutes]`. Sort them by minutes, and then sort the result by team. If the second sort is stable, each team's rows are still ordered by minutes, so the result is in order by team and, inside a team, by minutes. If the second sort is not stable, rows of one team can come out in any order, and the work of the first sort is lost. This is how a sort by several columns is built from sorts by one column: sort by the least important column first and the most important one last, each time with a stable sort. Several standard sorts document this guarantee: Python's `sorted` and `list.sort`, Kotlin's `sortedBy`, Rust's `sort` and `sort_by_key`, Java's `Arrays.sort` for arrays of objects, and `Array.prototype.sort` since ECMAScript 2019. Go's `sort.Slice` does not guarantee stability, and `sort.SliceStable` is the stable one.

**Merge sort** splits, sorts the halves, and merges them:

```text
sort(rows):
    if there are 0 or 1 rows: return them
    left  = sort(the first  floor(n / 2) rows)
    right = sort(the remaining rows)
    merge(left, right)

merge(left, right):
    while both left and right have rows:
        (comparison)  compare left's first row's key with right's first row's key
        if left.key <= right.key: take left's first row
        otherwise:                take right's first row
    append what remains of the one that is not empty (no comparisons)
```

With an odd number of rows the left half has one row fewer than the right half. The `<=` is what makes the sort stable: on a tie the row from the left half, which came first in the input, goes first.

**What the meter counts.** The meter counts one comparison for each time `merge` compares two keys, summed over all merges. Rows copied after one side is empty are not compared and not counted.

### Example 1

<!-- case: ex3 -->

Six rows of `[team, minutes]`. The first sort, by minutes, keeps rows with equal minutes in their input order (`[2, 15]` before `[1, 15]`). The second call sorts that result by team, and the rows come out grouped by team and, inside each team, by minutes. The meter shows the 10 comparisons of this second sort.

### Example 2

<!-- case: ex4 -->

Four one-column rows: the halves `[5, 3]` and `[8, 1]` take 1 comparison each, and merging `[3, 5]` with `[1, 8]` takes 3 (3 against 1, 3 against 8, 5 against 8; then `8` is copied), so the meter is `[5]`.

## Level 3: Quicksort, quickselect and the three-way partition

Methods to add:

- `quickSort(values)`: returns the values in ascending order, by the quicksort defined below.
- `quickSelect(values, k)`: returns the `k`-th smallest value, where `k = 1` is the smallest. Equal values count separately: in `[7, 2, 9, 2, 5]` the sorted order is `2, 2, 5, 7, 9`, so the 2nd smallest is `2` and the 3rd is `5`.
- `report()` after either method returns `[partitions, steps]`, counted below.

**The idea.** Pick one value of the range, the **pivot**. Rearrange the range so that all values smaller than the pivot come first, then all values equal to the pivot, then all larger values. The block of values equal to the pivot is now in its final place. What remains is to sort the smaller block and the larger block, which are separate smaller problems. This rearranging is a **partition**. Putting the equal values in a block of their own is the **three-way partition**, also known as the Dutch national flag problem, after the three coloured stripes of that flag, which the items are grouped by; it keeps a list full of equal values from being split over and over.

**The partition, exactly.** For the range of positions `low .. high`, with `high > low`:

```text
pivot = a[low + (high - low) div 2]      (the value in the middle position, the lower one if the range is even)
below = low;  scan = low;  above = high
while scan <= above:
    if a[scan] < pivot:
        swap a[below] and a[scan];  below = below + 1;  scan = scan + 1
    else if a[scan] > pivot:
        swap a[scan] and a[above];  above = above - 1
    else:
        scan = scan + 1
```

Afterwards the positions `low .. below - 1` hold values smaller than the pivot, `below .. above` hold values equal to it, and `above + 1 .. high` hold larger values.

**Quicksort** partitions the whole list, then does the same to `low .. below - 1` and to `above + 1 .. high`, and so on. A range with fewer than two values is already sorted and is not partitioned.

**Quickselect** wants one value, not the whole order. It partitions the whole list, then looks at where position `k - 1` (the place of the `k`-th smallest) fell: if it is inside the block of equal values, that value is the answer and nothing else is partitioned; if it is left of the block, only `low .. below - 1` is partitioned next; if it is right of the block, only `above + 1 .. high` is. A range with fewer than two values is not partitioned.

**What the meter counts.**

- `partitions` is the number of partitions done.
- `steps` is the number of passes of the `while scan <= above` loop, summed over all partitions. Each pass handles exactly one value, so a partition of a range of `m` values adds `m` steps.

A worked example, `quickSort([5, 3, 5, 1, 4])`: the pivot is the middle value, `5`. One partition of five values gives `[3, 1, 4, 5, 5]` with the block of 5s at positions 3 and 4 (5 steps). The left part `[3, 1, 4]` has the pivot `1` and gives `[1, 4, 3]` (3 steps), and its right part `[4, 3]` has the pivot `4` and gives `[3, 4]` (2 steps). Three partitions and 10 steps in all: `[3, 10]`.

### Example 1

<!-- case: ex5 -->

The walk-through above.

### Example 2

<!-- case: ex6 -->

The 3rd smallest of `[7, 2, 9, 2, 5]` is `5`, at position 2 of the sorted list (counting from 0). The first partition has the pivot `9` and the whole list of five values (5 steps): the block of 9s is at position 4, so position 2 is left of it and only the first four values are partitioned next. The pivot of `[7, 2, 2, 5]` is `2` (4 steps): the block of 2s is at positions 0 and 1, so position 2 is right of it. The pivot of the last two values `[5, 7]` is `5` (2 steps), and position 2 is inside its block. That is 3 partitions and 5 + 4 + 2 = 11 steps: `[3, 11]`.

## Level 4: External merge sort

Methods to add:

- `externalSort(values, memory, ways)`: returns the values in ascending order, sorted as described below.
- `report()` after `externalSort` returns `[runs, passes]`, counted below.

**The situation.** Sometimes there is more data than fits in memory, say a file of a billion numbers and room for a million at a time. The data lives on disk and must be read and written in pieces. The standard answer is the **external merge sort**. This level models it with plain lists: `memory` is the number of values that fit in memory at once, and `ways` is how many sorted pieces can be merged at once.

1. **Make runs.** Read the next `memory` values from the input (the last read may bring fewer), sort them in memory with any sort you like, and write them out as one **run**: a sorted piece. Do this until the input is used up. The runs are kept in the order they were written. `n` values give `ceil(n / memory)` runs.
2. **Merge passes.** While there is more than one run, do a **pass**: take the runs in order, `ways` at a time (the last group may have fewer; a group of one run is copied unchanged), and merge each group into one longer run. The new runs, in the same order, are the runs of the next pass. To merge a group, keep a **min-heap** (a structure that always hands out its smallest entry quickly) that holds the front value of each run of the group, remove the smallest, write it out, and put the next value of the same run into the heap. This never holds more than `ways` values.
3. The last remaining run is the sorted result. With no values there are no runs and the result is empty.

**What the meter counts.** `runs` is the number of runs made in step 1, and `passes` is the number of merge passes of step 2. Making the runs is not a pass. One run, or none, needs no pass.

A worked example: 9 values, `memory = 3`, `ways = 2`. Step 1 makes 3 runs of 3 values. Pass 1 merges runs 1 and 2 and copies run 3: 2 runs remain. Pass 2 merges them: 1 run. The meter is `[3, 2]`. With `ways = 3` the three runs merge in one pass: `[3, 1]`.

### Example 1

<!-- case: ex7 -->

Nine values in runs of three, merged two at a time: 3 runs, 2 passes.

### Example 2

<!-- case: ex8 -->

The same data merged three runs at a time: 3 runs, 1 pass.

## Constraints

- `0 <= values.length <= 2000` and `0 <= rows.length <= 2000`
- every integer is between `-10^9` and `10^9`
- a row has between 1 and 5 columns, all rows of one call have the same number of columns, and `0 <= key <` the number of columns
- for `quickSelect`, `1 <= k <= values.length`
- for `externalSort`, `1 <= memory <= 2000` and `2 <= ways <= 16`
- at most 100 calls per case

## Follow-ups

- Insertion sort makes as many moves as there are inversions. What does that say about its running time on a list that is almost sorted?
- Merge sort never makes more than about `n log n` comparisons. Why? Count the levels of splitting and the comparisons per level.
- The middle value as pivot works well on sorted input. Can you build an input of 9 values on which this pivot rule makes quicksort do the most work?
- If the file needs `R` runs and a merge takes `ways` at a time, how many passes are needed? What changes if you can afford a bigger `ways`, and what does the heap cost per value written?
- Real implementations make the runs longer than memory by an idea that replaces the smallest value in memory as soon as it is written out. How would the number of runs change on random data?

## Hints

### Hint 1

Sorting is putting values in order. The simplest method works like cards in a hand: take the next card and slide it left past every card that is larger, until it fits. Do that by hand on `[3, 1, 2]` and write down each time you ask "is this card larger?" and each time you shift a card.

### Hint 2

The meter counts only what the statement defines: write the sort exactly as given, and add one to a counter at the places the statement names. Do not count the loop tests, and do not count the final placement of the key.

### Hint 3

Merging two lists that are already sorted is easy: look at the front of each list, take the smaller, and repeat. Merge sort splits the list in two halves, sorts each half the same way, and merges them. Which side you take from when the two fronts are equal decides whether the sort is stable.

### Hint 4

For stability, take from the left half whenever its front is not larger than the right front. Rows with equal keys then leave in the order they came.

### Hint 5

For the partition, keep three marks on the range: everything before `below` is smaller than the pivot, everything after `above` is larger, and `scan` walks through the part in between. A smaller value swaps to the front and both `below` and `scan` advance. A larger value swaps to the back and only `above` moves, because the value that arrived at `scan` has not been looked at yet.

### Hint 6

Quickselect uses the same partition, but after each one it follows only the side that contains the wanted position, and it stops when that position falls in the block of values equal to the pivot.

### Hint 7

To make the runs, cut the input in pieces of `memory` values and sort each piece. To merge a group of runs, put the first value of each run in a min-heap together with the run it came from; repeatedly remove the smallest, append it, and put in the next value of that run.

### Hint 8

Repeat the merge pass: cut the list of runs into consecutive groups of `ways`, merge each group into a run, and count one pass. Stop when one run remains. The number of runs you started with is the first number of the report, the number of repetitions is the second.
