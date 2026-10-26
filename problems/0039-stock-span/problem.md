# Stock Span

## Statement

A trading desk receives the closing price of one stock once per day and wants to know, every day, how strong the run-up has been. The span of today's price is the number of consecutive days, ending with today and counting backwards, on which the closing price was at most today's price. Today always counts, so a span is at least 1.

Implement the class `StockSpanner`:

- `StockSpanner()` starts with no recorded prices.
- `span(price)` records `price` as the closing price of the next day and returns the span of that day.

The calls arrive one day at a time, so each answer must be given before the next price is known.

Reference: this is our own wording of LeetCode problem 901, [Online Stock Span](https://leetcode.com/problems/online-stock-span/).

## Input

- Constructor: no arguments.
- `span(price)`: `price` is today's closing price.

Each test is a sequence of calls: the constructor first, then `span` once per day.

## Output

- `span` returns the span of the day just recorded.

The expected output of a test lists one result per call, with `null` for the constructor.

## Examples

### Example 1

<!-- case: ex1 -->

On the third day the price 27 beats the day before (25) but not the first day (31), so its span is 2. The fourth day repeats 27; equal prices count, so its span is 3. The price 40 is the highest so far and covers all five days. The last day (35) covers itself and the 22 before it, and stops at 40.

### Example 2

<!-- case: ex2 -->

While the price falls, every span is 1. The final price 60 is higher than all earlier ones, so its span covers all four days.

## Constraints

- `1 <= price <= 10^5`
- At most `10^5` calls to `span`.

## Follow-ups

- Walking back over every earlier day costs O(n) per call during a long rally. Which earlier days can never stop a future walk, so that you can forget them?
- Can you make every call O(1) amortized?
- How would you answer the same question for the number of days with a strictly lower price?

## Hints

### Hint 1

Once a price is followed by a day with a higher or equal price, any later walk that reaches it also passes that later day first. What does that tell you about which days you need to keep?

### Hint 2

Keep only the days that are still higher than everything after them. They form a stack whose prices strictly decrease from bottom to top.

### Hint 3

Store each kept price together with the span it had. When a new price pops an entry, the new span absorbs that entry's whole span at once.
