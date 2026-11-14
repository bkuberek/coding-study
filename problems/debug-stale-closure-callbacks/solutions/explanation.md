# Debug: Stale Closure Callbacks: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| capture-per-batch | optimal | O(n) | O(n) | default answer: each callback closes over constants made for its own batch |

## Approach: capture-per-batch (Capture each batch in constants of its own)

### Intuition

A closure captures variables, not values. The callback doesn't remember what `batchNumber` was when it was created: it remembers where `batchNumber` lives, and reads it when it runs. These callbacks all run after the loop, so they all read the final state:

1. **`var row`** is one variable for the whole function. After the loop it holds `orderIds.length + 1`, so every message says the same row, and it is one past the end.
2. **`let batchNumber`**, declared outside the loop, is also one variable, and it holds the last batch's number by the time any callback runs.
3. **`let batch`**, also outside the loop, is reassigned to a new empty array after each flush, so every callback reads that last empty array.

A `console.log` inside the loop shows the right values, because at that moment they are right. That is what makes this bug confusing: nothing is wrong until later, somewhere else.

### Say it out loud

"This is a closure over a mutable variable: the callback captures the variable, not its current value, and it runs after the loop has moved on. `var` is function-scoped, so there's one `row` for all of them; `let` in the `for` head gives a new binding per iteration, but only for the loop variable. Anything declared outside the loop is still shared, so I copy what each callback needs into a `const` inside the block."

### Debugging approach

1. **Log inside the callback.** A log in the loop shows good values, and a log in the callback shows the final ones. That difference is the diagnosis.
2. **Count the variables.** For each name the callback uses, ask how many of it exist: `row` (one, because of `var`), `batchNumber` (one) and `batch` (one, pointing at a new array each time).
3. **Check the half-fixes.** Changing `var` to `let` fixes only the row (`ex2` still has no ids). Capturing `batchNumber` alone leaves the ids. Capturing the array and then clearing it with `batch.length = 0` empties the one array everyone holds (`h1`). Using `const ids = [...batch]` works, and so does `const ids = batch` here, because `batch` is reassigned rather than changed.

### Algorithm

1. Loop over the rows with `let row`, which gives each iteration a binding of its own.
2. Add the id to the current batch. When the batch is full, or this is the last row, make the callback.
3. Before making it, copy the batch number and the batch into `const`s inside the block, and let the callback use those.
4. Start a new array for the next batch.
5. After the loop, run the callbacks in order.

### Correctness

Each pass through the `if` creates new `const`s `number` and `ids`, and a new binding of `row` exists for that iteration, so each callback reads its own three values, which nothing later changes. `ids` refers to the array as filled for this batch, and `batch = []` points the shared variable at a new array without touching it. So each message describes the batch it was created for. A batch closes when it is full or when the ids run out, so every id appears in exactly one batch, in order.

### Complexity

- Time: O(n) — one pass over the ids, then each id is joined into one message.
- Space: O(n) — the callbacks and the batches they hold.

### Trade-offs

Building the message string up front and pushing a value, `const message = ...; afterCommit.push(() => message)`, removes the closure problem entirely, and it's what you'd do if the message depended on nothing that happens later. A callback that does real work at commit time can't always do that. Splitting the input into batches first, then calling `batches.map((ids, index) => () => ...)`, gives each callback its own parameters and needs no mutable variables at all: often the cleanest shape, and it costs a helper.

### Pitfalls and edge cases

- The general trap: a callback that runs later sees variables as they are later. It happens with timers, promise callbacks, event handlers, retries and commit hooks alike.
- `let` in a `for` head is a special case: it makes a new binding per iteration. A `let` outside the loop, or a `while` loop's counter declared before it, gets no such thing.
- `var` in a `for` also leaks past the loop, which is why `row` still exists when the callbacks run. Under `let`, the same code wouldn't reach the final value.
- Clearing with `batch.length = 0` changes the array that earlier callbacks hold; reassigning `batch = []` doesn't. This is why the reference may hold `batch` itself.
- `orderIds.indexOf(id)` can't replace the row, since the same id may appear twice (`h8`).

### Prevention

- The lint rules `no-var` and `no-loop-func` flag the `var` and functions created in a loop that use outer variables. `prefer-const` nudges you away from reassigning.
- Prefer functions that take their data as parameters over closures that read shared state.
- When testing code that defers work, assert on what the deferred work produced, not on what was true when it was scheduled.

### Language notes

TypeScript accepts all of this: `var` is legal, and a closure's capture isn't part of a function's type. TypeScript does narrow a `let` differently inside a callback, because it knows that the value may have changed by the time the callback runs, which is the compiler's small nod to this same trap.
