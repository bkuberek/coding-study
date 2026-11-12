# Learn Rust first

## The idea

cstudy problems assume you can already write a small function in the language you practise: take some input, loop over it, decide things with `if`, and return a result. This page is for you if you want to practise in Rust and are not there yet. It lists what to learn first and where to learn it for free, from Rust's own documentation.

Rust asks for more up front than the other languages here, because of **ownership**: the rules for which part of the program owns each value, which the Rust book calls "Rust's most unique feature". Expect your first problems to take longer than in a language you already know.

**What to learn before your first problem:**

- `let` and `let mut`, the integer types `i32`, `i64` and `usize`, `bool`, `char`, `String` and `&str`.
- `if`, `loop`, `while`, and `for` over a range such as `0..n` or over a vector.
- Functions: `fn`, typed parameters, the return type after `->`, and returning the last expression.
- Ownership, borrowing with `&` and `&mut`, and why a value can be moved.
- `Vec`, `HashMap`, `Option` and `match`.
- Reading a compiler error. Each error has a code, such as `E0277`, that the Compiler Error Index explains.

**Where to learn it:**

- [The Rust Programming Language](https://doc.rust-lang.org/book/), "the book", which teaches the language from first principles. Chapter 3, *Common Programming Concepts* (variables, types, functions, control flow), chapter 4, *Understanding Ownership*, and chapter 8, *Common Collections* (vectors, strings, hash maps), cover what cstudy problems use; chapters 5 and 6 add structs, enums and `match`.
- [Rustlings](https://github.com/rust-lang/rustlings/): small exercises that get you used to reading and writing Rust, recommended alongside the book.
- [Rust By Example](https://doc.rust-lang.org/rust-by-example/): the same ground with more code and fewer words.

All three are listed on [rust-lang.org/learn](https://www.rust-lang.org/learn).

You are ready when you can write, without looking anything up, a function that takes a `Vec<i32>` and returns how many of its values are even.

## A worked example

When you start a problem, cstudy writes a file for you to fill in, a **stub**. This is the stub that `cstudy start two-sum --lang rust` writes in `rust/practice/two_sum.rs`:

```rust
// Two Sum.
//
// You get an integer array nums and an integer target. Exactly two
// positions in nums hold values that add up to target. Find those two
// positions and return them.
//
// Statement: .statements/two-sum.md
// Run: cstudy test two-sum

pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {
    todo!()
}
```

Read it line by line:

1. The lines starting with `//` are comments: a short summary of the problem and the two commands you need.
2. `pub fn two_sum(...)` declares a public function, which cstudy's tests call. Keep the name and the signature.
3. `nums: Vec<i32>` is a vector of 32-bit integers, and the function takes ownership of it. `target: i32` is one integer. `-> Vec<i32>` says the function returns a vector.
4. `todo!()` marks unfinished code: it panics with "not yet implemented", so that the tests fail clearly on the untouched stub. You replace it with your code.

To fill it in you would loop over the indexes of `nums`, compare values and return a vector of two indexes, such as `vec![i as i32, j as i32]`: indexes are `usize` and the result holds `i32`, and Rust converts between number types only when you ask with `as`. [Your first problem](../your-first-problem/guide.md) walks through starting, testing and finishing this problem.

## Check your toolchain

cstudy needs `rustc` 1.80 or newer and `cargo`, installed through rustup, for Rust problems. Rust is optional: without it, every other language still works. Install it as the [toolchains guide](https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#rust) shows, then run `cstudy doctor` and look for the `rustc` and `cargo` rows.

```console
$ cstudy doctor
WARN  rustc not found on PATH    fix: needed for --lang rust, install Rust 1.80 or newer with rustup: https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#rust
WARN  cargo not found on PATH    fix: needed for --lang rust, install Rust 1.80 or newer with rustup: https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#rust
```

Those are the rows before Rust is installed: `WARN`, not `FAIL`, because Rust is optional. Once rustup has put them on your `PATH`, open a new terminal, and they read `ok` with their versions; a `rustc` older than 1.80 keeps the `WARN`. The `lldb-server` row on Linux, or `debugserver` on macOS, is about the debugger that only `cstudy test --debug` needs.

## When to use it

- **Read this page** before your first problem in Rust, if writing a loop or a function in Rust still needs looking up.
- **Skip it** if you can already write a function that loops over a vector and returns a result: go straight to [your first problem](../your-first-problem/guide.md).
- **Choose Rust** if you work with Rust or want to learn it. If it is your first language, give the ownership chapter time: the rest of the language builds on it.

## Common traps

- **Overflow panics in cstudy.** The book: in a debug build, integer overflow makes the program panic, and in a `--release` build it wraps around instead. cstudy builds your code optimized but keeps the overflow checks on, so an `i32` that overflows panics, as in a debug build. Use `i64` when a sum can grow past about two billion.
- **`usize` cannot go below zero.** Indexes are `usize`, an unsigned type, and `0 - 1` on a `usize` is an overflow, so `i - 1` panics when `i` is 0. Check before you subtract, or loop in a way that never needs to.
- **Indexing past the end panics.** The book: `&v[100]` on a five-element vector panics, while `v.get(100)` returns `None`.
- **A value can be moved.** Passing a `Vec` or a `String` to a function moves it, and the old name can no longer be used. Pass a reference, `&v`, when the function only reads it, or `.clone()` when you need two copies.
- **Strings cannot be indexed.** `s[0]` on a `String` does not compile: the book's words are "Rust strings don't support indexing", because a character can take more than one byte. Iterate with `s.chars()` for characters or `s.bytes()` for bytes. A literal such as `"abc"` is a `&str`; `"abc".to_string()` or `String::from("abc")` makes a `String`.

## Complexity

cstudy's problems state the time and space their solutions take, in Big-O notation, and many have a large hidden input that a slow solution does not finish in time. O(n) means the work grows in step with the input's size n, and O(1) that it stays the same whatever the size; amortized means averaged over many calls, so an occasional call costs more; expected means on average, since with hashing a much slower case is possible but very unlikely. Rust's standard library documents the costs of its collections in one table, marking some costs as amortized and some as expected.

| Operation | Cost | Source |
|-----------|------|--------|
| `v[i]`, `v.get(i)` on a `Vec` | O(1) | The `std::collections` performance table |
| `v.insert(i, x)` on a `Vec` | O(n − i), amortized: cheap at the end, slow at the front | The same table |
| `v.remove(i)` on a `Vec` | O(n − i) | The same table |
| `map.get(&k)`, `map.insert(k, v)`, `map.remove(&k)` on a `HashMap` | O(1) expected; `insert` also amortized | The same table |

A loop inside a loop over the same vector of n items does about n² steps. That is fine for ten items and too slow for a hundred thousand, the length of the largest input of several easy problems.

## Expert notes

- **cstudy's build profile.** Your code builds with Cargo's release profile, optimized so that `--perf` numbers are real, with `overflow-checks = true`, so an overflow panics instead of wrapping, and with line numbers in traces. `cstudy test --debug` builds with the dev profile instead, with the same overflow checks.
- **Offline builds.** The runner's few dependencies ship with cstudy as vendored crates, so builds run with `cargo --offline` and never contact crates.io. Your own Cargo settings, such as `RUSTFLAGS`, do not reach cstudy's builds.
- **rustup, not Homebrew's Rust.** The toolchains guide recommends rustup: Homebrew's `rust` formula has no `rust-src`, which rust-analyzer needs to show the standard library, and no way to pick a version.
- **Your editor.** `rustup component add rust-src` lets rust-analyzer show the standard library. The workspace's `rust/Cargo.toml` lists each problem you start, so rust-analyzer checks every file.

## Practice

Start with [your first problem](../your-first-problem/guide.md), which walks through the whole loop on a real problem.

After that, one problem is built on a Rust trap from this page:

- `debug-unsigned-underflow`: a binary search ported line by line from Java, which passes many tests and fails others. Find out why and fix it.

## Further reading

- [rust-lang.org/learn](https://www.rust-lang.org/learn): the official learning resources.
- [The Rust Programming Language](https://doc.rust-lang.org/book/): the book. See [data types](https://doc.rust-lang.org/book/ch03-02-data-types.html) for integer overflow and `usize`, [what is ownership](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html) for the ownership rules, and [vectors](https://doc.rust-lang.org/book/ch08-01-vectors.html) for indexing and `get`.
- [Rustlings](https://github.com/rust-lang/rustlings/) and [Rust By Example](https://doc.rust-lang.org/rust-by-example/): exercises and examples.
- [`std::collections`](https://doc.rust-lang.org/std/collections/index.html): the performance table, and when to use each collection.
- [`todo!`](https://doc.rust-lang.org/std/macro.todo.html): the macro the stub calls.
- [Strings](https://doc.rust-lang.org/book/ch08-02-strings.html): why strings cannot be indexed, and `chars` and `bytes`.
- [Rust By Example: casting](https://doc.rust-lang.org/rust-by-example/types/cast.html): converting between number types with `as`.
- [Compiler Error Index](https://doc.rust-lang.org/error-index.html): an explanation of each error code.
- [Install the language toolchains: Rust](https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#rust): cstudy's install steps, editor setup and build settings.
