# Debug: Append Aliasing

## Statement

The bundle builder of an online shop offers every combination of exactly `size` products from a catalog `items`. The function `bundleCombos` you start from should return every way to choose `size` different positions of `items`. Each bundle lists its items in catalog order, and the bundles come in lexicographic order of their positions: all bundles that contain the first item come first, and so on, which is the order the recursion produces them.

The code passes every small test. It fails others. Find out why and fix it.

### Bug report

> **Title:** Four-item bundles show duplicates and miss combinations
>
> Merchandising set up four-item bundles from a five-product catalog `1, 2, 3, 4, 5`. The page listed `1, 2, 3, 5` twice and never offered `1, 2, 3, 4`. Two- and three-item bundles have always looked right, and a five-item check from the same catalog passed. A developer added a print statement next to `bundles = append(bundles, bundle)`, and every bundle printed correctly at the moment it was stored.

## Input

- `items`: the product ids of the catalog, in catalog order
- `size`: the number of products in each bundle

## Output

Every bundle of `size` items, each in catalog order, in lexicographic order of the chosen positions.

## Examples

### Example 1

<!-- case: ex1 -->

The three ways to pick two of three products. This case passes as shipped.

### Example 2

<!-- case: ex2 -->

Each bundle leaves out one of the four products: first `8`, then `7`, `6` and `5`. This case passes too.

## Constraints

- `1 <= items.length <= 12`
- `1 <= size <= items.length`
- `1 <= items[i] <= 10^6`, and the ids are distinct

## Follow-ups

- Rewrite the function with one buffer that grows and shrinks (`bundle = bundle[:len(bundle)-1]` after each recursive call). Where must the copy happen then, and what goes wrong without it?
- The full slice expression `bundle[:len(bundle):len(bundle)]` makes the next `append` allocate. Would it fix this code? Is it a good fix?

## Hints

### Hint 1

Print `bundles` at the end of the function, next to the prints taken while storing. Which bundles changed after they were stored?

### Hint 2

Sizes 4, 6, 7 and 8 go wrong; sizes 1, 2, 3, 5 and 9 are right. Print `len(bundle)` and `cap(bundle)` before each recursive call.

### Hint 3

The loop passes `append(bundle, items[i])` to one call per `i`. When `bundle` has spare capacity, `append` does not allocate. Where do the writes of two sibling calls go?

### Hint 4

A slice you keep must own its backing array. `slices.Clone(bundle)` makes a copy.
