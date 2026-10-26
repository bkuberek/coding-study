# All Possible Recipes

## Statement

A kitchen knows `n` recipes. Recipe `recipes[i]` can be prepared once every item in `ingredients[i]` is available. The items in `supplies` are available from the start, in unlimited quantity. An ingredient may also be another recipe: once that recipe has been prepared, it is available as an ingredient too, as often as needed.

Some ingredients are neither supplies nor recipes, and some recipes depend on each other in a loop; such recipes can never be prepared. Return every recipe that can be prepared.

Reference: this is our own wording of LeetCode problem 2115, [Find All Possible Recipes from Given Supplies](https://leetcode.com/problems/find-all-possible-recipes-from-given-supplies/).

## Input

- `recipes`: the recipe names
- `ingredients`: `ingredients[i]` lists the items recipe `recipes[i]` needs
- `supplies`: the items available from the start

## Output

The names of all recipes that can be prepared, in any order. Return an empty list when none can.

## Examples

### Example 1

<!-- case: ex1 -->

`toast` needs only `bread`, which is a supply. Once toast exists, `sandwich` has both of its ingredients. A recipe may be listed before the recipes it depends on.

### Example 2

<!-- case: ex2 -->

`crust` uses two supplies, and `tart` uses the crust plus a supply. Nobody supplies `sugar` and no recipe makes it, so `glaze` can never be prepared.

## Constraints

- `n == recipes.length == ingredients.length`
- `1 <= n <= 1000`
- `1 <= ingredients[i].length <= 10`, and `ingredients[i]` has no repeated item
- `1 <= supplies.length <= 1000`
- Every name has 1 to 10 lowercase English letters.
- The names in `recipes` and `supplies` are all distinct from each other.

## Follow-ups

- If you think of every recipe as a node waiting on its ingredients, what familiar algorithm decides which nodes are ever freed?
- How does a recipe that lists itself, or two recipes that list each other, behave in your solution?

## Hints

### Hint 1

The simplest method: keep a set of available items and keep sweeping over the recipes, adding every recipe whose ingredients are all available, until a sweep adds nothing.

### Hint 2

Instead of sweeping, count for each recipe how many of its ingredients are still missing. Whenever an item becomes available, only the recipes that use it need updating.

### Hint 3

Start a queue with the supplies. Each item taken from the queue decrements the missing count of the recipes that use it; a recipe whose count reaches zero is prepared and joins the queue. Recipes in a loop, or behind an item nobody provides, never reach zero.
