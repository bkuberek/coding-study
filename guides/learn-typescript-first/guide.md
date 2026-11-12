# Learn TypeScript first

## The idea

cstudy problems assume you can already write a small function in the language you practise: take some input, loop over it, decide things with `if`, and return a result. This page is for you if you want to practise in TypeScript and are not there yet.

TypeScript is JavaScript with types added. Its own documentation is direct about the order: "you can't learn TypeScript without learning JavaScript!" The types are checked before the code runs; when it runs, it is JavaScript. So you learn the JavaScript first, then the types on top.

**What to learn before your first problem:**

- JavaScript: `let` and `const`, numbers, strings and booleans, `if` and `else`, `for` and `for...of` loops, functions, arrays and their methods (`push`, `length`, `sort`), objects, and `Map` and `Set`.
- TypeScript: annotating a function's parameters and its return type, array types such as `number[]`, and reading a type error.

**Where to learn it:**

- If JavaScript is new to you, the TypeScript documentation recommends the [JavaScript guide on MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide) or Microsoft's JavaScript resources first.
- Then [TypeScript for the New Programmer](https://www.typescriptlang.org/docs/handbook/typescript-from-scratch.html), followed by the [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html): its chapters *The Basics*, *Everyday Types* and *More on Functions* cover what cstudy problems use.

You are ready when you can write, without looking anything up, a function that takes an array of numbers and returns how many of them are even, with its parameter and return types annotated.

## A worked example

When you start a problem, cstudy writes a file for you to fill in, a **stub**. This is the stub that `cstudy start two-sum --lang typescript` writes in `typescript/practice/two-sum.ts`:

```typescript
// Two Sum.
//
// You get an integer array nums and an integer target. Exactly two
// positions in nums hold values that add up to target. Find those two
// positions and return them.
//
// Statement: .statements/two-sum.md
// Run: cstudy test two-sum
export function twoSum(nums: number[], target: number): number[] {
  throw new Error("Not implemented");
}
```

Read it line by line:

1. The lines starting with `//` are comments: a short summary of the problem and the two commands you need.
2. `export function twoSum(...)` defines the function and **exports** it, which lets other files import it. That is how cstudy's tests reach it, so keep the name and the `export`.
3. `nums: number[]` is an array of numbers, `target: number` is a number, and `: number[]` after the parentheses is the return type. TypeScript has one type, `number`, for integers and decimals alike: the Handbook notes that JavaScript has no separate integer type.
4. `throw new Error("Not implemented")` fails on purpose, so that the tests fail clearly on the untouched stub. You replace it with your code.

To fill it in you would loop over the positions of `nums`, compare values and return an array of two positions such as `[i, j]`. [Your first problem](../your-first-problem/guide.md) walks through starting, testing and finishing this problem.

## Check your toolchain

cstudy runs TypeScript with Node.js 24 or newer, and installs the workspace's TypeScript project with pnpm. Install both as the [toolchains guide](https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#nodejs-and-pnpm) shows, then run:

```console
$ cstudy doctor
ok    node v24.21.0 (type stripping)
ok    pnpm 12.8.1
```

Look for the `node` and `pnpm` rows. `ok` means the tool was found, with its version; `FAIL` means it is missing or too old, and a `fix:` hint follows when there is one. Inside a workspace, `cstudy doctor --fix` then runs `pnpm install` in the TypeScript project.

Rows for other languages may show `FAIL` or `WARN` when you have not installed their toolchains. That does not stop you practising in TypeScript.

## When to use it

- **Read this page** before your first problem in TypeScript, if writing a loop or a function in it still needs looking up.
- **Skip it** if you can already write a typed function that loops over an array and returns a result: go straight to [your first problem](../your-first-problem/guide.md).
- **Choose TypeScript** if you write JavaScript or TypeScript for the web or for Node.js, or want to.

## Common traps

- **`sort()` compares text by default.** MDN: the default order is "built upon converting the elements into strings". So `[10, 9, 1].sort()` gives `[1, 10, 9]`. Pass a comparison, `nums.sort((a, b) => a - b)`, to sort numbers. `sort` also changes the array in place.
- **`||` replaces every falsy value.** `count || 42` gives 42 when `count` is `0` or `""`, not only when it is missing. `??` replaces only `null` and `undefined`: `count ?? 42` keeps a `0`.
- **Large integers lose precision.** A `number` represents integers exactly only up to `Number.MAX_SAFE_INTEGER`, 9,007,199,254,740,991 (2⁵³ − 1). Past it, `2 ** 53 + 1` prints `9007199254740992`.
- **Types are not checked when the tests run.** Node.js runs your `.ts` file by replacing the type annotations with whitespace, and "no type checking is performed". A type error does not stop `cstudy test`; `cstudy test --typecheck` also runs the TypeScript compiler, `tsc`, to report them.
- **`console.log` is not `return`.** cstudy's tests check what the function returns.

## Complexity

cstudy's problems state the time and space their solutions take, in Big-O notation, and many have a large hidden input that a slow solution does not finish in time. O(n) means the work grows in step with the input's size n, and O(1) that it stays the same whatever the size.

| Operation | Cost | Source of the fact |
|-----------|------|--------------------|
| `map.get(key)`, `set.has(value)` | Sublinear on average in the number of entries | The ECMAScript specification requires it for `Map` and `Set`, as MDN quotes; `set.has` is on average faster than `includes` on an array of the same length |
| `nums.sort(compare)` | Sorts in place; no copy is made | MDN |
| Integer arithmetic | Exact up to 2⁵³ − 1 | MDN, `Number.MAX_SAFE_INTEGER` |

A loop inside a loop over the same array of n items does about n² steps. That is fine for ten items and too slow for a hundred thousand, the length of the largest input of several easy problems. [Hash maps and sets](../hash-maps-and-sets/guide.md) shows how a map or a set can turn such a loop into one pass; in TypeScript they are `Map` and `Set`.

## Expert notes

- **How cstudy runs TypeScript.** The runner runs your `.ts` file directly with Node.js's type stripping, on by default since 22.18.0 and 23.6.0. cstudy itself needs Node 24 or newer.
- **Only erasable syntax.** Node.js runs only TypeScript whose types can be removed without generating code. Features that need code generated, such as `enum` declarations, namespaces with runtime code and parameter properties, stop with an error. Plain functions, arrays and type annotations, which is all a cstudy stub uses, are fine.
- **`--typecheck`** runs `pnpm exec tsc --noEmit` in the workspace's TypeScript project, which reports type errors without writing any JavaScript.

## Practice

Start with [your first problem](../your-first-problem/guide.md), which walks through the whole loop on a real problem.

After that, one problem is built on a JavaScript trap from this page:

- `debug-falsy-plan-update`: code that fills in default values for a saved plan, and gets some of them wrong. Find out why and fix it.

## Further reading

- [TypeScript for the New Programmer](https://www.typescriptlang.org/docs/handbook/typescript-from-scratch.html): why you learn JavaScript first, and where.
- [The TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html) and [Everyday Types](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html): annotations, `number`, and array types.
- [JavaScript guide on MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide): the JavaScript the Handbook assumes.
- [MDN: `Array.prototype.sort()`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/sort): the default string order, and sorting in place.
- [MDN: nullish coalescing `??`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Nullish_coalescing): how it differs from `||`.
- [MDN: `Number.MAX_SAFE_INTEGER`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/MAX_SAFE_INTEGER): the largest exact integer.
- [MDN: `Map`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Map) and [`Set`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Set): sublinear access, as the specification requires.
- [TSConfig: `noEmit`](https://www.typescriptlang.org/tsconfig/#noEmit): type-checking without writing JavaScript.
- [MDN: `export`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/export): exporting a function from a module.
- [Node.js: modules, TypeScript](https://nodejs.org/api/typescript.html): type stripping, and which syntax it supports.
- [Install the language toolchains: Node.js and pnpm](https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#nodejs-and-pnpm): cstudy's install steps.
