# Learn Java first

## The idea

cstudy problems assume you can already write a small function in the language you practise: take some input, loop over it, decide things with `if`, and return a result. This page is for you if you want to practise in Java and are not there yet. It lists what to learn first and where to learn it for free, from Java's own documentation.

**What to learn before your first problem:**

- Variables and the primitive types `int`, `long`, `double`, `boolean` and `char`, and `String`.
- `if` and `else`, `for` loops (counting and over an array), `while` loops.
- Methods: parameters, return types, `return`.
- Classes, enough to read `public class Solution { ... }` and call a method on an object.
- Arrays such as `int[]`, and from `java.util` the collections `ArrayList` and `HashMap`.
- Reading a compiler error and an exception's stack trace.

**Where to learn it:**

- [dev.java/learn](https://dev.java/learn/), Java's official learning site. Start with *Your First Steps in Java*: your first Java code, using an IDE, launching simple programs, and JShell, which lets you try a line of Java and see the result at once. Then *Getting to Know the Language*: *Language Basics*, whose tutorials cover variables, primitive types, arrays, operators and control flow, then numbers and strings, and *Object-Oriented Programming*. *Mastering the API* covers collections when you need them.

You are ready when you can write, without looking anything up, a method that takes an `int[]` and returns how many of its values are even.

## A worked example

When you start a problem, cstudy writes a file for you to fill in, a **stub**. This is the stub that `cstudy start two-sum --lang java` writes in `jvm/java/src/main/java/practice/two_sum/Solution.java`:

```java
// Two Sum.
//
// You get an integer array nums and an integer target. Exactly two
// positions in nums hold values that add up to target. Find those two
// positions and return them.
//
// Statement: .statements/two-sum.md
// Run: cstudy test two-sum

package practice.two_sum;

import java.util.*;

public class Solution {
    public int[] twoSum(int[] nums, int target) {
        throw new UnsupportedOperationException("Not implemented");
    }
}
```

Read it line by line:

1. The lines starting with `//` are comments: a short summary of the problem and the two commands you need.
2. `package practice.two_sum;` names the package the class belongs to. It matches the folder the file is in; leave it as it is.
3. `import java.util.*;` lets you use any class of the `java.util` package by its short name. That package holds the collections framework: `ArrayList`, `HashMap` and the rest.
4. `public class Solution` declares the class, and `public int[] twoSum(int[] nums, int target)` the method cstudy's tests call: it takes an array of `int` and an `int`, and returns an array of `int`. Keep the class name and the method's signature.
5. `throw new UnsupportedOperationException("Not implemented");` fails on purpose, so that the tests fail clearly on the untouched stub. You replace it with your code.

To fill it in you would loop over the indexes of `nums`, compare values and return a new array of two indexes, such as `new int[] {i, j}`. [Your first problem](../your-first-problem/guide.md) walks through starting, testing and finishing this problem.

## Check your toolchain

cstudy builds and runs Java with the JDK your shell selects, and supports JDK 21 to 26; JDK 25 is the recommended one. Install it as the [toolchains guide](https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#jdk) shows, then run:

```console
$ cstudy doctor
ok    java 21.0.2 (JAVA_HOME)
```

Look for the `java` row. `ok` shows the version and how it was selected; `FAIL` means no JDK, or one outside 21 to 26, and a `fix:` hint follows. A `WARN` on `gradle` is expected and harmless: each workspace has its own Gradle wrapper, which downloads Gradle on first use, and a system Gradle is only needed to regenerate it. Inside a workspace, `cstudy doctor --fix` runs the first Gradle build.

Rows for other languages may show `FAIL` or `WARN` when you have not installed their toolchains. That does not stop you practising in Java.

## When to use it

- **Read this page** before your first problem in Java, if writing a loop or a method in Java still needs looking up.
- **Skip it** if you can already write a method that loops over an array and returns a result: go straight to [your first problem](../your-first-problem/guide.md).
- **Choose Java** if you work with Java, or with Kotlin: both run on the same JDK, and [Kotlin's page](../learn-kotlin-first/guide.md) builds on this one.

## Common traps

- **`int` overflows silently.** An `int` holds -2,147,483,648 to 2,147,483,647, and the Java specification says "The integer operators do not indicate overflow or underflow in any way": `Integer.MAX_VALUE + 1` is `-2147483648`, with no error. Use `long` when a sum can grow past about two billion.
- **Arrays have a fixed length.** Java's tutorial: "After creation, its length is fixed." To grow a collection, use an `ArrayList`, and convert at the end if the method returns an array.
- **`==` on strings compares objects.** The specification: `==` on two `String` references tells whether they are the same object, and two different strings with the same characters compare `false`. Use `s.equals(t)`.
- **Printing an array prints its type and hash.** `System.out.println(nums)` prints something like `[I@1b6d3586`, which is what the default `toString()` returns. `Arrays.toString(nums)` prints `[1, 2]`.
- **Indexes start at 0.** The last element of `nums` is `nums[nums.length - 1]`; `nums[nums.length]` throws an `ArrayIndexOutOfBoundsException`.

## Complexity

cstudy's problems state the time and space their solutions take, in Big-O notation, and many have a large hidden input that a slow solution does not finish in time. O(n) means the work grows in step with the input's size n, and O(1) that it stays the same whatever the size; amortized means averaged over many calls, so an occasional call costs more.

| Operation | Cost | Source of the fact |
|-----------|------|--------------------|
| `list.get(i)`, `list.set(i, x)` on an `ArrayList` | Constant time | The `ArrayList` documentation |
| `list.add(x)` | Amortized constant time: adding n elements takes O(n) | The `ArrayList` documentation |
| Most other `ArrayList` operations, such as `add(0, x)` | Linear time, roughly | The `ArrayList` documentation |
| `map.get(key)`, `map.put(key, value)` on a `HashMap` | Constant time, if the hash function spreads the keys well | The `HashMap` documentation |

A loop inside a loop over the same array of n items does about n² steps. That is fine for ten items and too slow for a hundred thousand, the length of the largest input of several easy problems.

## Expert notes

- **The JDK cstudy uses.** cstudy uses the JDK that `JAVA_HOME` names, or else the first `java` on `PATH`, as the Gradle wrapper does. Your code compiles at the level of that JDK, up to 26, so a newer JDK in the range lets you use its language features.
- **How your code runs.** cstudy builds the workspace's `jvm/` project with its Gradle wrapper, and `cstudy test` shows the build's time on its `build` line before the results.
- **Trying code quickly.** `java Hello.java` runs a one-file program without a separate compile step, since JDK 11, and `jshell` evaluates lines as you type them. Both are handy for checking what an expression does before you put it in a solution.

## Practice

Start with [your first problem](../your-first-problem/guide.md), which walks through the whole loop on a real problem. Every problem it suggests has a Java reference solution.

## Further reading

- [dev.java: Learn Java](https://dev.java/learn/): the official tutorials, from your first steps to the API.
- [Your first steps in Java](https://dev.java/learn/first-steps/): your first program, IDEs, single-file programs and JShell.
- [The Java Tutorials: arrays](https://docs.oracle.com/javase/tutorial/java/nutsandbolts/arrays.html): fixed length, and indexes from 0.
- [Java Language Specification, chapter 4](https://docs.oracle.com/javase/specs/jls/se21/html/jls-4.html): the range of `int`, and silent overflow.
- [Java Language Specification, chapter 15](https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html): `==` on references and `equals` for strings (§15.21.3).
- [`ArrayList`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/ArrayList.html), [`HashMap`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html), [`Arrays`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Arrays.html) and [`Object.toString()`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Object.html#toString()): the costs and behaviour above, in Java 21's API documentation.
- [`java.util`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/package-summary.html) and [`UnsupportedOperationException`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/UnsupportedOperationException.html): the package the stub imports, and the exception it throws.
- [Install the language toolchains: JDK](https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#jdk): cstudy's install steps.
