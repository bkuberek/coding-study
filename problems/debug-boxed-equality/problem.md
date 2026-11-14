# Debug: Boxed Integer Equality

## Statement

A warehouse takes a stock count of every SKU each night. SKU `i` is position `i` of the count lists. `before` is last night's count and `after` is tonight's. New SKUs are only ever appended, so `after` is at least as long as `before`. The function `changedSkus` you start from should return, in ascending order, every SKU index whose count changed: the count differs between the two nights, or the SKU did not exist last night.

It passes some tests and fails others. Find the bug and fix it.

### Bug report

> **Title:** Reconciliation report flags SKUs that did not change
>
> The overnight reconciliation report lists SKUs whose stock changed, and auditors recount each one by hand. Since the move to the main warehouse, the report flags hundreds of SKUs whose counts are identical on both nights, for example a pallet of 1,500 units that nobody touched. The test warehouse, where no shelf holds more than a hundred units, never showed the problem, and every unit test passes. The Java and Kotlin services both have it.

## Input

- `before`: last night's count for each existing SKU
- `after`: tonight's count for each SKU, including any SKUs added today at the end

## Output

The indices `i` where `i >= before.length` or `before[i] != after[i]`, in ascending order.

## Examples

### Example 1

<!-- case: ex1 -->

Only SKU 0 changed (5 to 3). This case passes as shipped.

### Example 2

<!-- case: ex2 -->

SKU 1 changed from 7 to 9, and SKU 2 is new. SKU 0 still holds 100 units on both nights. This case passes as shipped too.

## Constraints

- `0 <= before.length <= after.length <= 10^4`
- `-2^31 <= before[i], after[i] <= 2^31 - 1` (adjustments can make a count negative)

## Follow-ups

- The cache range is configurable. What would `-XX:AutoBoxCacheMax=2000` do to this bug, and why is that not a fix?
- Where else in a codebase do boxed integers show up without anyone writing `Integer`?

## Hints

### Hint 1

The test warehouse never has more than a hundred units on a shelf. Find the smallest unchanged count that the code reports as changed.

### Hint 2

Try 127 and 128, then -128 and -129. Why would equality depend on the size of the number?

### Hint 3

What are the static types of `previous` and `after.get(i)` (Java), or of `before.getOrNull(it)` (Kotlin)? What does `!=` (Java) or `!==` (Kotlin) compare for objects?

### Hint 4

`Integer.valueOf` returns a shared, cached object for values from -128 to 127 and a new object for other values.
