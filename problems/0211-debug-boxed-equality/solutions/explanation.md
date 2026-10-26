# Debug: Boxed Integer Equality: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| value-equality | optimal | O(n) | O(n) | default answer: compare boxed numbers with `equals` (`Objects.equals`, Kotlin `==`) |

## Approach: value-equality (Compare values, not references)

### Intuition

`List<Integer>` (and Kotlin's `List<Int>`, which is the same JVM type) stores `java.lang.Integer` objects, not `int` values. In Java, `previous != after.get(i)` has an `Integer` on both sides, so it compares **references**: "is this the same object?", not "is this the same number?". In Kotlin, `!==` is referential inequality, and `getOrNull` returns `Int?`, which is also a boxed `Integer`. (A developer used to TypeScript reads `!==` as "strict not equal", but in Kotlin it means "not the same object".)

The bug hides behind the integer cache. Autoboxing calls `Integer.valueOf`, which returns one shared object per value from -128 to 127 and a new object for other values. Equal small counts are the same object, so the reference comparison happens to give the right answer. Equal counts of 128 or more (or -129 or less) are two distinct objects, so the code reports them as changed. That is the 1,500-unit pallet, and why the test warehouse, with counts under a hundred, never showed it.

The fix compares values: `Objects.equals(previous, after.get(i))` in Java, which also handles the `null` of a new SKU, and `!=` in Kotlin, which calls `equals` and is null-safe.

### Debugging approach

1. **Reproduce with production-sized data.** The ticket's own example, 1,500 on both nights, fails immediately. Unit tests with small counts never will.
2. **Bisect the value.** Shrink the unchanged count until the bug disappears. It passes at 127 and fails at 128, and passes at -128 and fails at -129. A threshold at exactly 2^7 on both sides is the signature of the `Integer` cache, not of the algorithm.
3. **Check what `!=` compares.** In a debugger, the two `Integer`s of value 1,500 have different object ids. For 100 they share one id.
4. **Fix the comparison, then test both sides of both boundaries.** The cases at 127/128 and -128/-129 make sure the fix is not just moving the threshold.

### Algorithm

1. Create an empty result list.
2. For each index `i` of `after`:
   1. Let `previous` be `before[i]` if `i < before.length`, otherwise none (a new SKU).
   2. If `previous` is not *value-equal* to `after[i]` (a missing value never equals a present one), append `i`.
3. Return the result. Indices are visited in ascending order, so it is sorted.

### Correctness

`Objects.equals(a, b)` is true exactly when both are `null` or `a.equals(b)`, and `Integer.equals` compares the numeric values. Kotlin's `a != b` on `Int?` compiles to the same null-safe `equals` check. For an existing SKU, the condition is therefore true exactly when the two counts differ. For a new SKU, `previous` is `null` and `after[i]` is not, so it is always reported. Object identity no longer matters, so the result is the same for every value in the `int` range.

### Complexity

- Time: O(n) — one pass over `after`, and each `equals` is O(1).
- Space: O(n) — the result list holds up to n indices.

### Trade-offs

`Objects.equals` (or Kotlin `==`) is the minimal and idiomatic fix. Unboxing explicitly, `previous == null || previous.intValue() != after.get(i)`, also works and makes the primitive comparison visible, but it is easier to get wrong around `null`. Converting the inputs to `int[]` first removes boxing entirely and is faster for large lists, but it adds a copy and does not fix the habit. Raising the cache size with `-XX:AutoBoxCacheMax` only moves the threshold.

### Pitfalls and edge cases

- The general trap: `==` and `!=` on two boxed values (`Integer`, `Long`, `Short`, `Character`, `Boolean`) compare identity. The result depends on caching, which depends on the value and on how the object was created.
- Mixing one boxed and one primitive operand (`Integer == int`) unboxes and compares values. But if the boxed operand is `null`, unboxing throws `NullPointerException`.
- `new Integer(...)` (deprecated) always creates a new object, so equal values compare unequal even inside the cache range. `Integer.valueOf` and autoboxing use the cache. Whether two boxed values are the same object depends on how they were created, so identity is never something to rely on.
- `Long`, `Short` and `Byte` cache -128 to 127 too. `Character` caches 0 to 127. `Double` and `Float` do not cache at all.

### Prevention

- Static analysis flags it. IntelliJ's "Number comparison using `==`" inspection, Error Prone's `ReferenceEquality` and `BoxedPrimitiveEquality`, and SpotBugs' `RC_REF_COMPARISON` all catch reference comparison of boxed numbers. In Kotlin, identity comparison of numbers is deprecated, and the compiler and IntelliJ warn about it; make warnings fail the build (`allWarningsAsErrors`) so the warning cannot be ignored.
- Test with values outside -128..127. The sample data in tests should look like production data (counts in the thousands, ids in the millions).
- Prefer primitive arrays (`int[]`, `IntArray`) or primitive-specialized collections when the data is numeric.

### Language notes

- Java: `List<Integer>.get` returns `Integer`. Use `equals`, `Objects.equals` or `Integer.compare`. Never use `==` unless at least one side is a primitive and the boxed side cannot be `null`.
- Kotlin: `==` is structural equality (null-safe `equals`), and `===` is referential. On `Int?`, and on values typed as a generic `T`, numbers are boxed and `===` compares objects. Kotlin deprecates `===` on numbers for this reason. Use `==` and `!=` for values.
- Python and TypeScript are not listed. Python's `is` on integers has the same trap (CPython caches -5 to 256), but numeric code compares with `==`. TypeScript numbers are primitives, so `===` compares values.
