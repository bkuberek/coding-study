# Price After Rebate: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | the shelf is short, or as a correctness oracle |
| monotonic-stack | optimal | O(n) | O(n) | default answer |

Both approaches look for the "next smaller or equal element" of every slot. The brute force searches for it separately for each slot; the stack finds all of them in one left-to-right pass by answering a slot at the moment its rebate item arrives. The same pass, with the comparison flipped, finds the next greater element, as in Daily Temperatures.

## Approach: brute-force (Scan right for the first item that costs no more)

### Intuition

The statement is already a search: start at the slot after `i`, walk right, and stop at the first item whose price is at most `prices[i]`. That item's price is the rebate. Running off the end of the shelf means no rebate.

### Algorithm

1. Create `paid` as a copy of `prices`.
2. For each slot `i`, scan `j = i + 1, i + 2, ...` and stop at the first `j` with `prices[j] <= prices[i]`; set `paid[i] = prices[i] - prices[j]`.
3. If the scan reaches the end, leave `paid[i]` at the full price.
4. Return `paid`.

### Correctness

The scan for slot `i` visits the later slots in order and stops at the first one that costs no more than `prices[i]`, which is exactly the rebate item of the statement. When no later item qualifies, the scan never stops early and the full price is the required answer.

### Complexity

- Time: O(n^2) — when prices keep rising, no scan stops early, so slot `i` reads every later slot and the total is about n^2 / 2 comparisons.
- Space: O(1) — beyond the output array, only two loop indexes.

### Trade-offs

It is the statement in code, which makes it the oracle, and it is fast when cheap items sit close to the items they refund. A shelf of 10^4 items in a long rising run already costs about 5 * 10^7 comparisons, while the stack stays linear.

### Pitfalls and edge cases

- Use `<=`, not `<`: an item with the same price qualifies, and the rebate is then the whole price.
- Stop at the first qualifying item; a later, cheaper one is not the rebate.
- The last slot has nothing to its right and always pays its full price.

### Language notes

- Python, TypeScript, Java and Kotlin use two nested index loops with `break`; Java's `clone()`, Kotlin's `copyOf()` and TypeScript's `[...prices]` make the copy of `prices` that `paid` starts from.
- Python: `list(prices)` copies the list, and `break` leaves only the inner loop.
- Go: `make` followed by `copy` builds the output, and `break` leaves only the inner loop.
- Rust: `prices[slot + 1..].iter().position(..)` scans ahead and returns the offset of the first qualifying item as an `Option<usize>`; the item is at `slot + 1 + offset`.

## Approach: monotonic-stack (Stack of items still waiting for a rebate)

### Intuition

Walk along the shelf and keep the slots that have not found their rebate item yet. A new item answers every waiting slot that costs at least as much as it does. The waiting slots, from the leftmost to the rightmost, always get dearer: if a later waiting slot cost no more than an earlier one, it would have answered that one when it arrived. So the slots a newcomer can answer sit together at the top of a stack, and the newcomer only has to pop while the top is at least as dear as itself.

### Algorithm

1. Create `paid` as a copy of `prices`, and an empty stack of slot numbers.
2. For each slot `j` in order:
   1. While the stack is not empty and the price of the slot `i` on top is at least `prices[j]`, pop `i` and set `paid[i] = prices[i] - prices[j]`.
   2. Push `j`.
3. Slots left on the stack never meet a qualifying item; they keep their full price. Return `paid`.

### Correctness

Invariant: after processing slot `j`, the stack holds exactly the slots up to `j` that have no qualifying item up to `j`, and their prices rise strictly from bottom to top. When slot `j` arrives, every slot it pops is at least as dear as `prices[j]` and had no qualifying item before `j`, so `j` is its first qualifying item and the recorded rebate is right. The pops stop at a slot cheaper than `prices[j]`; every slot below it is cheaper still (strictly rising order), so none of them is answered by `j`, which is correct. Pushing `j` on top keeps the order strictly rising, because everything at least as dear as `j` was removed.

### Complexity

- Time: O(n) — every slot is pushed once and popped at most once, so the inner loop runs at most n times over the whole pass.
- Space: O(n) — the stack holds every slot of a rising run, up to the whole shelf.

### Trade-offs

Linear and short, and the template for every "next greater" and "next smaller" question. A right-to-left pass with a stack of candidate prices works as well: pop candidates that cost more than the current item, and the candidate left on top is its rebate. The left-to-right version reads closest to the statement, because each pop is an item finding its answer.

### Pitfalls and edge cases

- Store slot numbers, not prices: the pop needs the price of the slot, and a slot number lets the code write into `paid` at the right place.
- Pop while the top is at least as dear (`>=`); stopping at an equal price would leave that slot without the rebate the statement gives it.
- Slots still on the stack at the end need no work only because `paid` starts as a copy of `prices`.

### Language notes

- Python: a list is the stack (`append`, `pop`, `waiting[-1]`).
- TypeScript: an array with `push` and `pop`; `pop()!` asserts that the stack is not empty, which the loop condition guarantees.
- Java: a plain `int[]` with a size counter avoids boxing every slot number into an `Integer`, as `ArrayDeque<Integer>` would.
- Kotlin: `ArrayDeque<Int>` with `addLast`, `removeLast` and `last()`; `withIndex()` gives the slot and its price together.
- Go: a `[]int` is the stack: `append` pushes and reslicing pops. The loop reads the top as `waiting[len(waiting)-1]`.
- Rust: a `Vec<usize>` is the stack; `while let Some(&earlier) = waiting.last()` reads the top without popping, and the `break` inside leaves the loop when the top is cheaper than the newcomer.
