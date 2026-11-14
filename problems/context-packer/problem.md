# Context Packer

## Statement

Build `ContextPacker`, the part of an assistant that chooses which stored memories go into a model's context window. Each item is a memory with a text, a size in tokens and a relevance score, and the context has a token budget that the chosen items must fit in. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

Every method takes the current time as its first argument, `timestamp`. Nothing reads a clock, and no rule of the four levels depends on the time: the argument is there so that every call keeps the same shape as the API grows.

Aim to finish in 90 minutes. A good split: read the statement and pick the core data structure in the first 5 minutes, then finish level 1 by about minute 20, level 2 by 40, level 3 by 65 and level 4 by 88, keeping the last minutes for a final run.

## Input

- `ContextPacker()`: creates a packer with no items.
- `timestamp`: the time of the call. Within one test, timestamps never decrease from call to call.
- `itemId`: an item. Ids are unique within the packer.
- Each level's section describes the methods it adds and their other parameters.

## Output

Each method returns what its level describes. A missing item is reported with a sentinel, never with an exception: `false` for booleans and `""` for strings.

## Level 1: Packing under a budget

- `addItem(timestamp, itemId, text, tokens, score)`: stores an item with its `text` (lowercase words separated by single spaces), its size in `tokens` and its relevance `score`. Returns `false` and changes nothing when an item with that id is already stored.
- `removeItem(timestamp, itemId)`: deletes the item. Returns `true` when it existed, `false` otherwise.
- `pack(timestamp, budget)`: chooses items whose tokens add up to at most `budget` and returns their ids in the order they were chosen. It changes nothing: every item stays stored.
- The packing order is: higher score first; equal scores, fewer tokens first; then ascending string order of id. Go through the items in packing order and take each one that fits in what is left of the budget. An item that does not fit is skipped, and the next one is still tried.

### Example 1

<!-- case: ex1 -->

The packing order is `a`, `b`, `c`, `d`: `b` and `c` score the same, and `b` is smaller. With 60 tokens, `a` and `b` leave 10, too few for `c`, but exactly enough for `d`. With 100 tokens, `a`, `b` and `c` use all of it. Adding a second `a` fails, and once `b` is removed, 60 tokens take `a` and `d`.

## Level 2: Pinned items

- `pin(timestamp, itemId)`: pins the item. Returns `false` and changes nothing when it does not exist or is already pinned.
- `unpin(timestamp, itemId)`: unpins the item. Returns `false` and changes nothing when it does not exist or is not pinned.
- `pack` takes every pinned item, before any other item and in packing order among themselves, and then fills what is left of the budget with the unpinned items as in level 1.
- When the pinned items together need more tokens than `budget`, `pack` takes nothing and returns the one-element list `["OVER_BUDGET"]`, which no id can equal. Pinned items that use exactly the whole budget fit.
- Removing an item drops its pin: adding the id again stores an unpinned item.

### Example 1

<!-- case: ex2 -->

`style` is pinned, so it goes first despite its low score, and the 25 tokens left take `name` and `job`. Once `pet` is pinned too, the pins go in packing order, `pet` before `style`, and 30 tokens still fit `name`. 20 tokens cannot hold the 25 pinned tokens. After `style` is unpinned, it is too large for what `pet` and `name` leave.

## Level 3: Category caps

- `setCategory(timestamp, itemId, category)`: puts the item in `category`, a name of 1 to 10 lowercase letters or digits, taking it out of the category it was in. Returns `false` when the item does not exist. An item starts in no category, and removing it drops its category.
- `setCap(timestamp, category, cap)`: from now on, a pack takes at most `cap` items of `category`, from 0 to 1000. Setting a cap again replaces it. Items in no category, and items in a category without a cap, are not limited.
- When the items of a category have reached its cap, `pack` skips the next ones, and the next item of another category is still tried.
- Pinned items still always go in, even past their category's cap, and they count toward it: the unpinned items of that category get only the places the pinned ones left. An item skipped because it does not fit in the budget takes no place.

### Example 1

<!-- case: ex3 -->

Without a cap, all four items fit. With a cap of 2 on `taste`, `f3` is the third `taste` item, so it is skipped, while `t1`, in no category, still goes in. `zz` does not exist.

## Level 4: Near-duplicates

- The similarity of two items is the number of distinct words that both texts contain, divided by the number of distinct words that either text contains. Word order and repeated words do not matter. Two items are near-duplicates when their similarity is above 0.8; exactly 0.8 is not above it.
- Before choosing, `pack` collapses near-duplicates. It goes through the items with the pinned ones first, then the others, each group in packing order. An unpinned item that is a near-duplicate of an item kept before it is knocked out, by the first such kept item; every other item is kept. Only kept items knock items out, and pinned items are never knocked out.
- `pack` then chooses among the kept items with the rules of the earlier levels. A knocked-out item takes no budget and no place in a cap. Collapsing ignores the budget and the caps: an item knocks out its near-duplicates even when it does not fit itself.
- `duplicateOf(timestamp, itemId)`: the id of the item that knocks `itemId` out if `pack` ran now, or `""` when the item is kept or does not exist.

### Example 1

<!-- case: ex4 -->

The texts of `a` and `b` have 8 distinct words in common out of 9 in total, a similarity of about 0.89, so `b`, which comes later in packing order, is knocked out by `a`. `c` shares 4 of 9 words with `a` and is kept.

## Constraints

- At most 1000 calls per test, and at most 100 items stored at a time.
- `1 <= timestamp <= 10^9`, never decreasing within a test.
- Ids are 1 to 10 lowercase letters or digits.
- A text is 1 to 20 words, and a word is 1 to 10 lowercase letters.
- `1 <= tokens <= 10^4`, `0 <= score <= 1000` and `0 <= budget <= 10^6`.

## Follow-ups

- Greedy packing can leave tokens unused that a different choice would fill. When would you pay for an exact choice, and what would it cost?
- How would you avoid comparing every pair of items when thousands are stored?

## Hints

### Hint 1

Sort the items once per `pack` with one comparison that holds every tie-break, then walk the sorted list keeping a running count of the tokens left.

### Hint 2

Pinned items are the same walk with a different first key: sort with "pinned first" ahead of the score, and check their total against the budget before taking anything.

### Hint 3

Compare word sets in integers: `5 * shared > 4 * union` says "above 0.8" with no rounding to worry about.
