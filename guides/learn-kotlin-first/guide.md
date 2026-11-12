# Learn Kotlin first

## The idea

cstudy problems assume you can already write a small function in the language you practise: take some input, loop over it, decide things with `if`, and return a result. This page is for you if you want to practise in Kotlin and are not there yet. It lists what to learn first and where to learn it for free, from Kotlin's own documentation.

**What to learn before your first problem:**

- `val` and `var`, and the basic types `Int`, `Long`, `Double`, `Boolean`, `Char` and `String`.
- `if` and `when`, `for` loops over a range such as `0..<n` or over a collection, and `while` loops.
- Functions: `fun`, typed parameters, a return type, `return`.
- Arrays such as `IntArray`, and the collections `List` and `MutableList`, `Map` and `MutableMap`.
- Null safety: what the `?` in `Int?` means.
- Reading a compiler error.

**Where to learn it:**

- [The Kotlin tour](https://kotlinlang.org/docs/kotlin-tour-welcome.html), on kotlinlang.org. Its beginner part teaches the fundamentals, and it runs entirely in your browser, with nothing to install.
- [Basic syntax](https://kotlinlang.org/docs/basic-syntax.html): functions, variables, loops, `when`, ranges and null checks on one page, to come back to.
- [Kotlin Koans](https://kotlinlang.org/docs/koans.html): exercises, each a failing unit test that you make pass, which is how cstudy works too. They are designed mainly for Java developers, so take them after the tour.

You are ready when you can write, without looking anything up, a function that takes an `IntArray` and returns how many of its values are even.

## A worked example

When you start a problem, cstudy writes a file for you to fill in, a **stub**. `cstudy start two-sum --lang kotlin` writes it in `jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt`. Below the comments that summarise the problem, it reads like this; the function's one line of body is shown here as a comment:

```kotlin
package practice.two_sum

class Solution {
    fun twoSum(nums: IntArray, target: Int): IntArray {
        // In your file: one line that always throws NotImplementedError
    }
}
```

Read it line by line:

1. `package practice.two_sum` names the package the class belongs to. It matches the folder the file is in; leave it as it is.
2. `class Solution` declares the class whose method cstudy's tests call.
3. `fun twoSum(nums: IntArray, target: Int): IntArray` declares the function: `fun` starts a function, each parameter has its type after a colon, and the type after the parentheses, `IntArray`, is what it returns. Keep the name and the signature.
4. `IntArray` is an array of `Int` values; on the JVM it is Java's `int[]`.
5. The body, in your file, is a call to a standard-library function that always throws `NotImplementedError`, so that the tests fail clearly on the untouched stub. You replace it with your code.

To fill it in you would loop over the indexes of `nums`, compare values and return a new array of two indexes, such as `intArrayOf(i, j)`. [Your first problem](../your-first-problem/guide.md) walks through starting, testing and finishing this problem.

## Check your toolchain

cstudy builds and runs Kotlin with the same JDK as Java, and supports JDK 21 to 26; JDK 25 is the recommended one. You do not install the Kotlin compiler yourself: Gradle downloads it with the workspace's build. Install the JDK as the [toolchains guide](https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#jdk) shows, then run:

```console
$ cstudy doctor
ok    java 21.0.2 (JAVA_HOME)
```

Look for the `java` row: `ok` shows the version and how it was selected, and `FAIL` means no JDK, or one outside 21 to 26, with a `fix:` hint. A `WARN` on `gradle` is expected: the workspace's Gradle wrapper downloads its own Gradle. Inside a workspace, `cstudy doctor --fix` runs the first Gradle build, and `cstudy doctor` then shows a `runner kotlin` row that answers `hello` when Kotlin code can run.

Rows for other languages may show `FAIL` or `WARN` when you have not installed their toolchains. That does not stop you practising in Kotlin.

## When to use it

- **Read this page** before your first problem in Kotlin, if writing a loop or a function in Kotlin still needs looking up.
- **Skip it** if you can already write a function that loops over an array and returns a result: go straight to [your first problem](../your-first-problem/guide.md).
- **Choose Kotlin** if you work with Kotlin, on the JVM or for Android, or want to. If you know Java, the Koans show the differences quickly; [learn Java first](../learn-java-first/guide.md) covers the JDK both languages share.

## Common traps

- **`Int` overflows silently.** An `Int` holds -2,147,483,648 to 2,147,483,647. Kotlin's documentation: "The compiler does not automatically produce an error when integer overflow occurs", and the value wraps around, so `2147483647 + 1` prints `-2147483648`. Use `Long` when a sum can grow past about two billion.
- **Arrays have a fixed size.** An `IntArray` has no `add` or `remove`. Collect values in a `MutableList<Int>` and convert at the end with `toIntArray()` if the function returns an array.
- **`val` does not freeze an array.** `val nums = intArrayOf(1, 2)` stops you assigning another array to `nums`, but `nums[0] = 5` still works: Kotlin's documentation says elements are mutable in both `val` and `var` arrays.
- **`==` on arrays compares objects.** On two arrays, `==` checks whether both sides are the same array, not whether they hold the same values. Use `a.contentEquals(b)` to compare elements.
- **`List` is read-only.** `listOf(...)` gives a `List`, which has no `add`. Use `mutableListOf(...)` when you need to change it.
- **Null safety.** A type that may be `null` ends in `?`, such as `Int?`. Using such a value as if it could not be `null` is a compiler error; check it first, or use a safe call such as `b?.length`.

## Complexity

cstudy's problems state the time and space their solutions take, in Big-O notation, and many have a large hidden input that a slow solution does not finish in time. O(n) means the work grows in step with the input's size n, and O(1) that it stays the same whatever the size; amortized means averaged over many calls, so an occasional call costs more. On the JVM, Kotlin's `ArrayList` and `HashMap` are Java's own classes, so Java's documented costs apply:

| Operation | Cost | Source of the fact |
|-----------|------|--------------------|
| `list[i]`, `list[i] = x` on an `ArrayList` | Constant time | Java's `ArrayList` documentation |
| `list.add(x)` | Amortized constant time: adding n elements takes O(n) | Java's `ArrayList` documentation |
| `map[key]`, `map[key] = value` on a `HashMap` | Constant time, if the hash function spreads the keys well | Java's `HashMap` documentation |

A loop inside a loop over the same array of n items does about n² steps. That is fine for ten items and too slow for a hundred thousand, the length of the largest input of several easy problems.

## Expert notes

- **The Kotlin compiler cstudy uses** comes from the Kotlin Gradle plugin, which Gradle downloads with the build, so `kotlinc` is not required. Install it only if you want a Kotlin REPL.
- **Why JDK 26 at most.** The Kotlin compiler that cstudy pins targets JDK 26 at most, so `cstudy doctor` reports JDK 27 and newer as not supported yet.
- **`IntArray` and `Array<Int>`.** `IntArray` stores plain `Int` values, while an `Array<Int>` holds boxed objects. Kotlin's documentation recommends the primitive-type arrays to avoid the cost of boxing.

## Practice

Start with [your first problem](../your-first-problem/guide.md), which walks through the whole loop on a real problem. Every problem it suggests has a Kotlin reference solution.

## Further reading

- [The Kotlin tour](https://kotlinlang.org/docs/kotlin-tour-welcome.html): the fundamentals, in your browser.
- [Basic syntax](https://kotlinlang.org/docs/basic-syntax.html): functions, `val` and `var`, loops, `when`, ranges and nullable types.
- [Ranges](https://kotlinlang.org/docs/ranges.html) and [null safety](https://kotlinlang.org/docs/null-safety.html): `0..<n`, and safe calls.
- [Kotlin Koans](https://kotlinlang.org/docs/koans.html): exercises as failing tests, online or in an IDE.
- [Arrays](https://kotlinlang.org/docs/arrays.html): fixed size, `val` arrays, comparing with `contentEquals`, and primitive-type arrays.
- [Numbers](https://kotlinlang.org/docs/numbers.html): the range of `Int`, and overflow.
- [Equality](https://kotlinlang.org/docs/equality.html): `==` and `===`.
- [Collections overview](https://kotlinlang.org/docs/collections-overview.html): read-only and mutable collections.
- [`ArrayList`](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.collections/-array-list/), [`HashMap`](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.collections/-hash-map/) and [`IntArray`](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin/-int-array/): what they are on the JVM.
- [Java's `ArrayList`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/ArrayList.html) and [`HashMap`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html): their documented costs.
- [Install the language toolchains: JDK](https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#jdk): cstudy's install steps, and why Kotlin needs nothing more.
