# Stock Span: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| scan-back | brute | O(n) per call | O(n) | few calls, or as a correctness oracle |
| monotonic-stack | optimal | O(1) amortized per call | O(n) | default answer |

The span of a day is the distance back to the previous day with a strictly higher price (or to before the first day). This is the "previous greater element" question, asked online: each answer is due before the next price arrives. The time classes describe a whole sequence of n calls: walking back is quadratic during a rally, the stack is linear.

## Approach: scan-back (Keep every price and walk back on each call)

### Intuition

Store every price. For a new price, walk backwards over the stored prices while they are at most the new one; the number of days covered is the span.

### Algorithm

1. Append `price` to the list of prices.
2. Start at the new day and step back while the previous day's price is at most `price`.
3. Return the number of days from where the walk stopped to the new day, inclusive.

### Correctness

The walk covers exactly the maximal run of consecutive days ending today whose prices are at most today's price: it moves back one day at a time and stops at the first day with a higher price, or at the first day of the series. That run's length is the span by definition.

### Complexity

- Time: O(n) per call — the walk can cover every earlier day; during a rally of k days the calls cost 1 + 2 + ... + k, about k^2 / 2 steps.
- Space: O(n) — every price is kept.

### Trade-offs

The definition turned into code, which makes it the oracle. It is fine when prices are noisy, since walks stop quickly, but a long rally makes it quadratic. It also keeps prices that can never stop a future walk.

### Pitfalls and edge cases

- The comparison is `<=`: equal prices extend the span.
- Count today: a price lower than yesterday's has span 1, not 0.

### Language notes

- Python and TypeScript keep a plain list or array of prices; Java's `ArrayList<Integer>` boxes each price, and `prices.get(day - 1) <= price` unboxes it for the comparison (comparing two boxed `Integer`s with `==` would compare references instead); Kotlin's `mutableListOf<Int>()` hides the same boxing.
- Go: a `[]int` of prices holds plain values, so `s.prices[day-1] <= price` is a value comparison with no boxing.
- Rust: a `Vec<i32>` of prices compares by value too. Days are `usize` indexes, so the span converts with `as i32` on return, and `day - 1` is safe because the loop tests `day > 0` first.

## Approach: monotonic-stack (Stack of prices with the spans they absorbed)

### Intuition

Once a day is followed by a day with a price at least as high, it can never stop a future walk: any walk that reaches it passes that later day first, which is at least as high. So only days that are strictly higher than everything after them matter. Their prices strictly decrease from oldest to newest, which is a stack. When a new price pops such a day, it also covers every day that day had covered, so store each kept price together with its span and add the popped spans.

### Algorithm

1. Set `span = 1` for today.
2. While the stack is not empty and the price on top is at most `price`, pop the top entry and add its span to `span`.
3. Push `(price, span)` and return `span`.

### Correctness

Invariant: the stack holds, from bottom to top, the days that are strictly higher than every later day, with strictly decreasing prices; each entry's span counts its own day plus the days between it and the entry below it (or the start of the series), and all those days have prices at most its price. A new price covers the top entry exactly when the top price is at most the new price, and then it also covers all days that entry covered. It stops at the first entry with a strictly higher price, which is the previous strictly higher day. The days it popped are now followed by a day at least as high, so removing them keeps the invariant, and the new entry's span covers exactly the days between it and the entry below it.

### Complexity

- Time: O(1) amortized per call — each day is pushed once and popped at most once, so n calls do at most 2n stack operations in total; one call can still pop many entries.
- Space: O(n) — a falling series keeps every day on the stack.

### Trade-offs

Linear over the whole sequence and the expected answer. A single call can take O(n) (a new all-time high after a long fall), so it does not bound the worst case per call, only the total. Storing the spans (instead of day indexes and a running day counter) keeps the stack self-contained.

### Pitfalls and edge cases

- Pop on `<=`, not `<`: equal prices are covered.
- Add the popped spans, not just 1 per popped entry: a popped entry stands for all the days it absorbed earlier.
- The answer depends on all earlier calls, so the stack lives in the object, not in the method.

### Language notes

- Python: a list of `(price, span)` tuples; `self.stack.pop()[1]` takes the span of the popped entry.
- TypeScript: two parallel arrays avoid allocating a small object per day.
- Java: an `ArrayDeque<int[]>` of two-element arrays, used as a stack through `push`, `pop` and `peek`.
- Kotlin: a private `data class Entry` on an `ArrayDeque`, which reads better than a pair.
- Go: a small struct `entry{price, span}` in a slice is the stack; the loop pops while the top price is not higher and adds each popped span.
- Rust: a `Vec<(i32, i32)>` of tuples is the stack. `while let Some(&(top_price, top_span)) = self.stack.last()` copies the top out of the borrow, so `pop()` can run inside the loop body.
