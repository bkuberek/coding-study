# Undo and Redo Editor: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| history-tree | optimal | O(n) per edit, undo or redo; O(n * d) per jump | O(n + e) | default answer: commands that apply and revert, kept in a tree |

`n` is the length of the text, `d` the number of steps between the current state and the target of a jump, and `e` the total number of characters held by all recorded steps.

## How the design grows level by level

| Level | What changes | Design move |
|-------|--------------|-------------|
| 1 | Edits can be taken back and put back | Each edit becomes a command object that knows its position, the text it removed and the text it inserted, so it can apply and revert itself. Two stacks hold them |
| 2 | Typing is grouped | A grouping rule decides whether a typing call extends the newest command or creates a new one. Only the newest command can grow, and only while nothing else happened |
| 3 | Named checkpoints | A checkpoint is a memento: a copy of the text kept aside. A restore is one more command, whose removed text is the whole current text |
| 4 | Branches survive | The two stacks become a tree. Undo moves to the parent, redo to a remembered child, and a new edit adds a child instead of emptying the redo stack |

The reference starts from level 4's shape, since it contains the other three: a linear history is a tree in which every state has at most one child that matters.

## Approach: history-tree (Edits as commands in a history tree)

### Intuition

An undo system has to answer one question: how do I get from this text to the previous one? There are two ways. One keeps a full copy of the text before every change; undo then puts the copy back. The other keeps a description of the change, the command, and reverts it. A command `(position, removed, inserted)` is enough for both directions: applying it replaces `removed` with `inserted` at `position`, and reverting it does the opposite. Insert, erase and restore are the same command with different fields (`removed` empty for an insert, `inserted` empty for an erase, the whole text for a restore), so the history never needs to know which kind of edit a step was.

Two stacks describe a linear history: the undo stack holds the steps that are in effect, the redo stack the ones that were taken back. Level 4 only asks to keep what level 1 throws away. Store each step as a node with a parent (the state it was made from) and children (the steps made from it). The undo stack is then the path from the root to the current node, and the redo stack is the chain of remembered children below it. A new edit adds a child instead of emptying anything.

### Algorithm

1. Keep the text, a list of steps indexed by number (step 0 is the root, the initial state), the current step, a map of checkpoints, and the typing group: whether it is open and when the last typing happened.
2. To record an edit: if `removed` equals `inserted`, do nothing. Otherwise create step `k` = the next number, with the current step as parent, add it to the parent's children, make it the parent's remembered child, apply it to the text and make it current.
3. `insert` and `erase` clamp the position to the text and record `("", text)` or `(text[start:end], "")`. `restore` records `(whole text, saved copy)`. Each of them, and `undo`, `redo`, `checkpoint` and `jump`, first closes the typing group.
4. `undo`: if the current step has a parent, revert it and move to the parent. `redo`: if the current step remembers a child, apply that child and move to it.
5. `typeText`: clamp the position. If the group is open, the position is where the current step's inserted text ends, the pause since the last typing is at most 1000 ms and the inserted text does not end with a space, insert the text and append it to the current step's `inserted`. Otherwise record a new step. Either way, open the group and remember the timestamp.
6. `jump(k)`: if `k` names no step, return `false`. Otherwise list the path from step `k` up to the root. Revert and climb from the current step until it is on that path; that step is the closest common ancestor. Apply the steps of the path below it, from the top down. Make every step on the path remember its child on the path, and make `k` current.

### Correctness

Invariant: the text always equals the initial text with the steps on the path from the root to the current step applied in order. Recording applies the new step and makes it current, which extends the path by that step. Undo reverts the current step, which is the last one on the path, and drops it; redo applies a child and appends it. A jump reverts steps from the bottom of the path up to the common ancestor and then applies the steps of the target's path below it, so the path ends at the target. Reverting a step restores exactly the text before it was applied, because the step stored the removed text and the inserted text at that position.

Grouping keeps the invariant: an open group means the last call was `typeText`, so the current step is the group's step and a leaf, and the text after it is exactly what the step inserted followed by what was after it. Appending to `inserted` and inserting the same text at the end of the group's text changes the step and the text together.

The redo rules hold because a new step becomes its parent's remembered child, undo and redo never change what a step remembers, and only a jump rewrites the remembered children, along the target's path. After undo and a new edit, the new state is a leaf, so redo returns `false`, which is level 1's "redo is cleared".

### Complexity

- Time: O(n) per edit, undo or redo; O(n * d) per jump — applying or reverting a step rebuilds the text around one position, and a jump applies or reverts each of the `d` steps between the two states once.
- Space: O(n + e) — the text, plus every step's removed and inserted text, which the tree keeps forever.

### Trade-offs

- **Snapshots instead of commands.** Storing the whole text in every state makes undo, redo and jump O(1) moves plus a copy, and the code shorter, at O(n) memory per step: 10,000 one-letter edits of a 10,000-character text keep 100 million characters. Commands store only what changed. Real editors often mix the two: commands, plus a snapshot every so many steps so that a long jump does not replay thousands of commands.
- **Two stacks.** For levels 1 to 3 two stacks are enough and are the textbook answer. They lose the redo branch on every new edit, which the tree keeps at the cost of a parent pointer and a child list per step.
- **A rope or gap buffer.** Rebuilding a string per edit is O(n). An editor for large files keeps the text in a structure whose edits cost O(log n) or O(1) near the cursor; the commands stay the same.

### Pitfalls and edge cases

- Recording an edit that changes nothing: inserting an empty text, erasing at the end, or restoring the text that is already there. Such a step would make one undo do nothing visible, and it would clear the redo history (hidden cases with no-op edits between undo and redo).
- Clamping: a position past the end means the end, both for an edit and when comparing a typing position with the end of the group.
- Grouping must stop on anything but a read: an undo, a redo that returns `false`, an edit that changes nothing, a checkpoint and a jump all end the group. Reading the text must not.
- The pause is measured from the previous typing call, not from the start of the group, and exactly 1000 ms still joins.
- A space ends the group after it: `hi ` is one step. Splitting before the space instead gives `hi` and ` yo`.
- Undo must not change what a state remembers for redo; otherwise undo then redo after a jump goes down the wrong branch.
- A growing typing group is the same state with the same number.

### Language notes

- Python, TypeScript, Java, Kotlin and Go keep steps as objects with a parent pointer, and compare them by identity in the set of the target's path (`HashSet` in Java and Kotlin uses identity because `Step` does not override `equals`).
- Rust keeps the steps in one `Vec` and links them by index, which avoids `Rc<RefCell<...>>` for a tree with parent links. Strings are sliced by byte, which is safe here because the text is ASCII.
- Java appends to the group's text with a `StringBuilder`, so a long burst of typing does not copy the step's text on every key; the other languages append to a string, which is fine for the sizes here.

## Further reading

- Gamma, Helm, Johnson and Vlissides, *Design Patterns: Elements of Reusable Object-Oriented Software*, Addison-Wesley, 1994 (ISBN 0-201-63361-2). It lists Command and Memento among its behavioral patterns. In this problem, the steps are commands, edits turned into objects that can apply and revert themselves, and the checkpoints are mementos, copies of the editor's state kept aside to be put back later.
