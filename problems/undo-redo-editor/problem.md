# Undo and Redo Editor

## Statement

Build `Editor`, the part of a text editor that makes changes reversible. The editor holds one piece of text. You change it with edits, and you can take an edit back with undo and put it back again with redo. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is an undo step?** Every time the text changes, the editor writes down what changed: where it happened, what was there before and what is there now. That note is an undo step. Undo reads the newest step and puts the old text back; redo reads it again and puts the new text back. Because each step knows both directions, the editor never has to guess.

**The command pattern.** This is a classic design called the command pattern: an action is turned into an object that can be stored and run later. Here each edit becomes an object with two operations, one that applies the change and one that reverts it. For example, the edit "insert `lo` at position 3" turns `hel` into `hello` when applied and turns `hello` back into `hel` when reverted. An editor that keeps a list of such objects can walk backwards and forwards through its history without knowing what kind of edit each one was. You do not have to write a class per edit, but the idea that every step can apply and revert itself is the heart of the problem.

Aim to finish in 60 minutes. A good split: read the statement in the first 5 minutes, then finish level 1 by about minute 15, level 2 by 30, level 3 by 40 and level 4 by 55, keeping the last minutes for a final run.

## Input

- `Editor(initial)`: creates an editor whose text is `initial`, with nothing to undo and nothing to redo.
- Positions count characters from 0: position 0 is before the first character, and position `n` is after the last one in a text of `n` characters. A position past the end of the text means the end of the text.
- Each level's section describes the methods it adds and their parameters.

## Output

Edits return nothing. `undo`, `redo` and the later navigation methods return `true` when they did something and `false` when there was nothing to do; then nothing changes. `text()` returns the current text.

## Level 1: Undo and redo stacks

- `insert(position, text)`: puts `text` into the text at `position`.
- `erase(position, count)`: removes up to `count` characters, starting at `position`. Fewer are removed when the text ends sooner.
- `undo()`: takes back the newest edit that has not been taken back yet, and returns `true`, or returns `false` when there is nothing to undo.
- `redo()`: puts back the edit that was taken back most recently, and returns `true`, or returns `false` when there is nothing to redo.
- `text()`: the current text.

Rules:

- Each `insert` and `erase` that changes the text is one undo step. An edit that changes nothing, such as inserting an empty text or erasing at the end, records no step and leaves the redo history as it is.
- A new step clears everything that could be redone: after undo, an edit starts a new history, and `redo()` returns `false`.
- Undo and redo can be repeated: two undos take back the two newest steps, and two redos put them back in order.

### Example 1

<!-- case: ex1 -->

Two inserts make two steps. Undo takes back the second one, and redo puts it back.

### Example 2

<!-- case: ex2 -->

`erase(1, 2)` removes `bc`. Two undos return to the start, where a third undo has nothing left and returns `false`. After one redo, the insert of `_` is a new edit, so the insert of `XY` can no longer be redone.

## Level 2: Grouping typing

Typing a word one key at a time should not take one undo per letter. Typing is grouped: the calls of one burst of typing share one undo step.

- `typeText(timestamp, position, text)`: inserts `text` at `position`, as `insert` does, at time `timestamp` in milliseconds. `text` is never empty. Timestamps never decrease from one `typeText` call to the next.

A `typeText` call joins the step of the previous `typeText` call, instead of starting a new step, exactly when all of these hold:

1. The previous call to the editor, not counting calls to `text()`, was a `typeText` call. Any other call ends the group, whatever it does or returns: `insert`, `erase`, `undo`, `redo`, and the methods of later levels except the ones that only read.
2. The position, after a position past the end is moved to the end, is exactly where the group's text ends, so the new text continues it.
3. At most 1000 ms passed since the previous `typeText` call: `timestamp` minus the previous timestamp is at most 1000.
4. The group's text does not end with a space. A space joins the group it ends, and the next character starts a new one, so typing `hi yo` makes the steps `hi ` and `yo`.

Undo of a group takes back all of its text at once, and redo puts all of it back. A `typeText` call that starts a new step clears the redo history, as any new step does.

### Example 1

<!-- case: ex3 -->

Three keys typed 100 ms apart, each at the end of the previous one, form one step, so one undo removes the whole word.

### Example 2

<!-- case: ex4 -->

The space ends the first group, so `hi ` and `yo` are two steps.

## Level 3: Checkpoints

Sometimes you want to mark a version of the text and come back to it later, whatever happened in between. A copy of an object's state that you keep aside and can put back later is called a memento.

- `checkpoint(name)`: saves a copy of the current text under `name`. Saving under a name that exists replaces the copy. It changes neither the text nor the undo history, but it ends a typing group.
- `restore(name)`: replaces the whole text with the copy saved under `name`, and returns `true`. It returns `false`, and changes nothing, when no copy has that name.

Rules:

- A restore that changes the text is one undo step, like an edit: undo after it brings back the text from before the restore, and it clears the redo history.
- A restore to the text that is already there is not a step and leaves the redo history as it is, as for any edit that changes nothing.
- Copies are not affected by undo, redo or later edits: a copy holds the text as it was when it was saved.

### Example 1

<!-- case: ex5 -->

The restore brings back `draft` as one step, so one undo returns to `one`, and the next undoes the erase.

### Example 2

<!-- case: ex6 -->

There is no copy named `nope`. Restoring `a` gives the text it already has, so no step is recorded and there is nothing to undo.

## Level 4: A history tree

With two stacks, an edit after undo throws away everything that could be redone. Here nothing is lost: the history becomes a tree. Each state of the text is a node; the initial text is the root, and every step is a node whose parent is the state it was made from. An edit after undo starts a new branch next to the old one, and the old branch stays reachable.

**State numbers.** The initial state is `0`. Each new step gets the next number, `1`, `2`, `3` and so on, in the order the steps are created, on whatever branch. A typing group that grows (level 2) stays the same state with the same number.

- `undo()`: moves to the parent of the current state. Returns `false` at state `0`.
- `redo()`: moves to the child the current state remembers, which is its newest child unless a jump changed it, as below. Returns `false` when the state has no child.
- `state()`: the number of the current state. It only reads, so it does not end a typing group.
- `branches()`: the numbers of the children of the current state, in increasing order. It only reads.
- `jump(state)`: makes the text that of the state with this number, and returns `true`, or returns `false` and changes nothing when no state has that number. It records no step. Every state on the way from state `0` down to the target now remembers the child on that way, so undos followed by as many redos come back to the target.

Rules:

- Every state remembers one child for redo. A new step becomes the remembered child of its parent. `undo` and `redo` do not change what any state remembers; `jump` does, as above.
- The rules of the earlier levels still hold. After undo, a new edit creates a new child, so `redo()` from the new state returns `false`, while the old branch is still reachable with `jump`.

### Example 1

<!-- case: ex7 -->

`a` is state 1 and `ab` is state 2. After undo, inserting `c` makes state 3 on a new branch. From state 1 the branches are `[2, 3]`, and redo takes the newest. After the jump to 2, state 1 remembers child 2, so undo and redo return to 2.

### Example 2

<!-- case: ex8 -->

The two typing calls form one group, state 1. No state has the number 9. After jumping to the root, two redos follow the remembered children back to state 2.

## Constraints

- At most 2,000 calls per test.
- The text never holds more than 10,000 characters; all texts use printable ASCII characters (space to `~`).
- `0 <= position <= 10^4` and `0 <= count <= 10^4`.
- `0 <= timestamp <= 10^12`; `name` is 1 to 20 characters.
- `-10 <= state <= 10^4` in `jump`.

## Follow-ups

- Keeping a full copy of the text in every state makes undo a single assignment. How much memory does it cost after 10,000 one-character edits of a 10,000-character text, compared with storing commands?
- How would you limit the history to the newest 100 steps, and what should happen to a branch whose root falls off the end?
- Some editors also offer "go back in time": move to the state that was created just before the current one, across branches. What would you store to make that O(1) per move?
- Two people edit the same text at once. Why does replaying one person's undo steps on the other person's text go wrong, and what would the steps need to carry?

## Hints

### Hint 1

Store each change as a small record of where it happened, the text that was there and the text that replaced it. With that record you can go forwards (put the new text in) and backwards (put the old text back) without any other information.

### Hint 2

Keep two lists: the steps you can undo and the steps you can redo. Undo moves the last step from the first list to the second and reverts it; redo moves it back and applies it. A brand new step empties the second list.

### Hint 3

For grouping, remember whether the last call was typing, where the group's text ends, and when the last typing happened. Every other call except `text()` forgets the group. When the next typing call continues the group, add its text to the group's step instead of making a new one.

### Hint 4

A checkpoint is just a saved string. Restoring is an edit like any other: its step replaces the whole current text with the saved one, so undo can put the old text back.

### Hint 5

For the tree, give each step a parent and a list of children, plus one remembered child. Undo moves to the parent, redo to the remembered child, and a new step is added as a child of the current state and becomes the one it remembers. Number the steps as you create them, keeping them in a list so that a number finds its step at once.

### Hint 6

To jump, walk up from the target to the root and mark that path. Then revert steps from the current state upwards until you reach a state on the path, the closest common ancestor, and apply the steps on the path from there down to the target. Finally, make every state on the path remember the child on it.
