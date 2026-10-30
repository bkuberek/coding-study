# Debug: Shadowed Variable: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| assign-outer | optimal | O(n + c) | O(1) | default answer: declare `err` first and assign `discount` with `=` |

## Approach: assign-outer (Assign the outer variable instead of declaring a new one)

### Intuition

`discount, err := couponDiscount(coupon, subtotal)` sits inside the `if` block, and a block is a new scope. `:=` declares every name on its left that is not already declared *in that scope*. Neither `discount` nor `err` exists in the block yet, so the statement declares two new variables. The new `discount` shadows the outer one until the closing brace. The block clamps and then forgets it, and the function subtracts the outer `discount`, which is still 0.

The code compiles because the inner `discount` is used: `if discount > subtotal` reads it. Go reports a local variable that is declared and never used, but not one that is assigned and never read afterwards, and it never reports shadowing. Invalid coupons are still rejected, because the `return -1` happens inside the block, which is why the refactor looked fine to everyone who only tested the error path.

The confusing part is that `:=` *does* reuse existing variables, but only those declared in the same scope. Written at function level, next to `discount := 0`, the same line would assign `discount` and declare only `err`.

### Debugging approach

1. **Narrow the symptom.** Valid coupons give no discount; invalid coupons are rejected correctly. So the parsing is right (and its unit tests pass), and the result is lost between `couponDiscount` and `return`.
2. **Print on both sides of the block.** `discount` is 274 inside the `if` block and 0 at the `return`. A variable that changes value across a closing brace with no assignment in between is two variables.
3. **Confirm in the editor or debugger.** "Go to definition" on the `discount` in `return subtotal - discount` jumps to `discount := 0`, not to the `:=` in the block. A debugger shows two `discount` entries in the locals view while paused inside the block.
4. **Fix the declaration, not the symptom.** Moving the `return` into the block would also make the tests pass, but leaves a shadowed variable for the next change to trip over.

### Algorithm

1. Add up `prices` into `subtotal`.
2. Set `discount` to 0.
3. If `coupon` is not empty: declare `var err error`, then assign `discount, err = couponDiscount(coupon, subtotal)`. If `err` is not nil, return `-1`. Clamp `discount` to at most `subtotal`.
4. Return `subtotal - discount`.

`couponDiscount` reads the number after the `PCT` or `OFF` prefix with `strconv.Atoi`, checks its range, and returns the discount in cents (`subtotal * percent / 100` rounds down) or an error.

### Correctness

With `=`, the call assigns the `discount` declared at function level, so the clamped value is the one subtracted. For an empty coupon the block is skipped and the discount is 0. For an invalid coupon `couponDiscount` returns an error and the function returns `-1`. Otherwise the discount is `n` percent of the subtotal rounded down, or `n` cents, and the clamp keeps the total at or above 0. The coupon has at most 12 characters, so the number has at most 9 digits and `Atoi` cannot overflow; the input contains no signs, which `Atoi` would otherwise accept. `subtotal * percent` is at most 10^11, well inside Go's 64-bit `int`.

### Complexity

- Time: O(n + c) — one pass over the n prices and one parse of the c characters of the coupon.
- Space: O(1) — a few integers.

### Trade-offs

`var err error` plus `=` is the smallest fix and keeps the shape of the code. Other fixes that avoid the trap altogether are often clearer:

- Compute the discount in a helper that returns it, so `checkoutTotal` reads `discount, err := discountFor(coupon, subtotal)` at function level, where `:=` assigns as intended.
- Return early: `if coupon == "" { return subtotal }`, then `discount, err := couponDiscount(...)` at function level.

Both remove the nested `:=` that caused the bug, which is worth more than the one-line fix in code that will keep changing.

### Pitfalls and edge cases

- The general trap: `:=` in an inner block (`if`, `for`, `switch`, `select`, a closure) declares new variables, even when a variable with the same name exists outside. It reuses a variable only when that variable was declared in the same block.
- `discount, err = ...` without `var err error` does not compile, because `err` is undeclared. The compiler error is easy to "fix" by switching back to `:=`, reintroducing the bug.
- Removing `discount := 0` and declaring it inside the block makes `discount` undefined at the `return`, so the compiler catches that version.
- The same trap with `err` is more common: `result, err := f()` inside a block shadows an outer `err`, and the error checked after the block is a different, still nil, `err`.

### Prevention

- Enable a shadowing linter: `go vet` does not run the `shadow` analyzer by default, but `golangci-lint` can (`govet` with `enable: [shadow]`), and gopls has an opt-in `shadow` analysis.
- `ineffassign` (part of `golangci-lint`'s standard set) reports `discount = subtotal` as an ineffectual assignment, a value that is never read, which points straight at the shadowed variable.
- Test the success paths of every branch, not only the error paths. Here a single test with a valid coupon fails.
- Prefer short functions and early returns, which keep `:=` at function level.

### Language notes

- Go only. Java rejects declaring a local variable that shadows another local variable in an enclosing block, so the same code does not compile. Kotlin allows it with a "Name shadowed" warning. Python has no block scope: an assignment inside an `if` assigns the function's variable. TypeScript allows shadowing with `let` and `const`, but a destructuring declaration (`const [discount, err] = ...`) always declares; there is no operator that declares some names and assigns others, which is what makes Go's `:=` easy to misread.
- Go 1.22 changed `for` loop variables to be per-iteration, which removed a different scoping trap (closures capturing a shared loop variable); `:=` shadowing is unchanged.
