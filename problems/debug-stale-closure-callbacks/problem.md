# Debug: Stale Closure Callbacks

## Statement

An order service must not tell anyone about an order until its database transaction has committed. So while the transaction runs, `notifyAfterCommit` groups the order ids into batches and queues one callback per batch. The commit then runs the callbacks, each producing one message.

For `orderIds` and `batchSize`, the batches hold `batchSize` ids each, in order, and the last one holds what is left. Batch `n` produces this message, where `<row>` is the 1-based position of the batch's last id in `orderIds`:

```text
batch <n>: <id>+<id>+<id> through row <row>
```

The function returns the messages in the order the callbacks ran, which is the order they were queued. The callbacks must keep running after the loop, as they do now, because that is the point of them. Find the bugs and fix them.

### Bug report

> **Title:** After-commit notifications all describe the same batch
>
> We split 5 orders into batches of 2, and the log shows three lines, all saying `batch 3` and all with the same row number, and with no order ids at all. A developer tested each line inside the loop with a `console.log`, and the values were right there. They only go wrong when the callbacks run.

## Input

- `orderIds`: the ids of the orders in the transaction
- `batchSize`: how many ids a batch holds

## Output

One message per batch, in order. No orders means no messages.

## Examples

### Example 1

<!-- case: ex1 -->

No orders, so no batches and no messages. This case passes as shipped.

### Example 2

<!-- case: ex2 -->

One batch of two. It is the only batch, so the batch number happens to be right as shipped, but the ids and the row are not. This is the example to fix first.

## Constraints

- `0 <= orderIds.length <= 1000`
- `1 <= batchSize <= 1000`
- Ids are 1 to 10 letters, digits or `-`.

## Follow-ups

- This code uses no `async` at all. Which real features of a backend run a callback later, the way a commit hook does here?
- A linter rejects `var`. Which of this code's bugs would it catch, and which not?

## Hints

### Hint 1

Log the values inside each callback, not inside the loop, and compare them with what you expected.

### Hint 2

A closure captures a variable, not the value it had when the closure was created. How many `row` variables does this loop create? How many `batch` variables does the whole function have?

### Hint 3

`var` in a `for` makes one variable for the whole function. `let` in a `for` makes a new one per iteration. A `let` declared outside the loop is still one variable.

### Hint 4

Inside the `if`, copy what the callback needs into `const`s of its own, declared right there.
