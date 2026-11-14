# Price After Rebate

## Statement

A shop lines its goods up on one long shelf. `prices[i]` is the price of the item in slot `i`, counting from the left, starting at slot 0.

The shop runs a loyalty rule. When you buy the item in slot `i`, look at the slots to its right, from the nearest one to the farthest, and find the first item whose price is less than or equal to `prices[i]`. The price of that item is your rebate on the item you are buying. If no item to the right is that cheap, you get no rebate.

Return an array `paid` of the same length as `prices`, where `paid[i]` is `prices[i]` minus the rebate for slot `i`.

Reference: this is our own wording of LeetCode problem 1475, [Final Prices With a Special Discount in a Shop](https://leetcode.com/problems/final-prices-with-a-special-discount-in-a-shop/).

## Background

You can solve this by checking every slot to the right of every item, but a shelf of 100,000 items makes that slow. There is a classic shortcut, and this problem is a good first place to meet it.

A **stack** is a list that you only change at one end, called the top. To *push* is to add an item on top, and to *pop* is to remove the item on top. The last item pushed is the first one popped, like a pile of plates.

A **monotonic stack** is a stack whose items always stay in order from bottom to top: for example, no item taller than the one beneath it, as in the line of people below. The rule that keeps it in order is simple. Before you push a new item, you first pop every item on top that would break the order.

Here is a different small question, so you can see the shape of the idea. People stand in a line with the heights `150, 160, 155, 170, 165`, and for each person we want the height of the first person standing behind them who is taller (or "none"). Walk along the line from the front and keep a stack of the people who have not found anyone taller yet. When a new person arrives, they are the answer for every waiting person who is shorter than them, so those people are popped and answered. Then the new person joins the stack to wait.

| Person arrives | Stack before | Popped and answered | Stack after |
|----------------|--------------|---------------------|-------------|
| 150 | empty | none | 150 |
| 160 | 150 | 150 gets 160 | 160 |
| 155 | 160 | none, 155 is not taller than 160 | 160, 155 |
| 170 | 160, 155 | 155 gets 170, then 160 gets 170 | 170 |
| 165 | 170 | none | 170, 165 |

The people left on the stack at the end (170 and 165) never meet anyone taller. Notice two things. The stack never has a person taller than the one beneath it (otherwise the taller one would already have answered the one beneath), so the people who can be answered next are always at the top. And every person is pushed once and popped at most once, so the whole walk does a small, fixed amount of work per person, however long the line is.

Your question is a close cousin of this one: you want the first *no more expensive* item rather than the first taller person, and you want the price paid rather than the neighbour's value. Work out what changes in the stack before you code.

## Input

- `prices`: the price of the item in each slot, from the left end of the shelf

## Output

An array of the same length as `prices`: the price paid for each slot, after taking off its rebate (or the full price when it has none).

## Examples

### Example 1

<!-- case: ex1 -->

Slot 0 costs 8, and the first item to its right that costs 8 or less is the 4 in slot 1, so the rebate is 4 and slot 0 pays 4. Slot 1 costs 4; the 6 in slot 2 is too dear, but the 2 in slot 3 qualifies, so it pays 4 - 2 = 2. Slot 2 (6) also finds the 2 and pays 4. Slot 3 (2) finds only a 3 to its right, which is dearer, so it gets no rebate and pays 2. The last slot never has anything to its right, so it pays its full price of 3.

### Example 2

<!-- case: ex2 -->

An equal price qualifies. Slot 0 (7) is followed at once by another 7, so its rebate is the whole 7 and it pays 0. Slot 1 (7) skips the 9 and takes the 3 in slot 3, paying 4. Slot 2 (9) also takes the 3 and pays 6. Slot 3 (3) is followed by another 3 and pays 0, and the last slot pays its full 3.

## Constraints

- `1 <= prices.length <= 10^5`
- `1 <= prices[i] <= 10^6`

## Follow-ups

- Checking every slot to the right of every item costs O(n^2) when prices keep rising. Can you answer all items in one pass over the shelf?
- Can you solve it walking from the right end of the shelf to the left instead?
- What changes if the rebate must come from an item that is strictly cheaper, so that an equal price does not qualify?

## Hints

### Hint 1

Take Example 1 by hand. For the item in slot 0, walk to the right one slot at a time until you meet an item that costs no more than it does. Which slots did you walk past, and could any of them have used the same item you stopped at?

### Hint 2

An item that has not found its cheaper neighbour yet is "waiting". When a new item arrives from the right, it may be the answer for several waiting items at once. Which waiting items does it answer: the dear ones, the cheap ones, or all of them?

### Hint 3

The waiting items, from the leftmost to the rightmost, always cost strictly more as you go: if a waiting item cost no more than the one before it, it would already have answered that one. So a newcomer can only answer a run of waiting slots at the top of the pile, and never one buried beneath a slot it cannot answer. Keep the waiting slots on a stack and look only at its top.

### Hint 4

Walk the shelf from left to right with a stack of waiting slots. For each slot `j`, while the top slot `i` of the stack has `prices[i] >= prices[j]`, pop it and set `paid[i] = prices[i] - prices[j]`. Then push `j`. Start with `paid` equal to `prices`, so slots that are never popped keep their full price.
