# Spec: Problem Format

Every autograded problem is a directory of data plus reference code. Tests are language-neutral JSON, signatures are declared once in a type DSL, and correctness is judged by executing the user's code and comparing its output.

## Correctness model

Correctness is behavioral, never textual.

1. The CLI sends the case inputs (never the expected values) to the language runner.
2. The runner executes the user's function or class and serializes what it returns.
3. The CLI core compares that output with the expected value using the problem's comparator.

Reference solutions are never diffed, parsed or otherwise compared with user code. Any output the comparator accepts passes; problems with several valid answers use a `checker` comparator, which validates the answer itself. Concurrent problems add stress cases, judged by invariants over the recorded results of many concurrent runs ([Concurrent problems](#concurrent-problems)).

## Directory layout

```text
problems/0001-two-sum/
  problem.md          # full description (required sections: authoring.md)
  meta.yaml           # metadata, signature, comparator, approaches, perf
  tests.json          # cases
  generator.py        # seeded input generator (required for `ready` dsa problems)
  checker.py          # only when comparator.type == checker
  stress_checker.py   # only when a concurrent stress case has a checker invariant
  buggy/              # only when stub == buggy (debugging track): solution.<ext> per language
  rubric.md           # required for track lld: design criteria and reference design (authoring.md)
  solutions/
    explanation.md    # one section per approach (format: authoring.md)
    broken/           # concurrent only: <broken-id>.<ext>, deliberately wrong references
    brute-force.py    # <approach-id>.<ext>
    hash-map.py
    hash-map.ts
    hash-map.java
    hash-map.kt
```

| Rule | Detail |
|------|--------|
| Directory name | `<id>-<slug>` |
| `id` | 4-digit zero-padded string, unique, assigned by `cstudy new` (max + 1); display and ordering only |
| `slug` | `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, unique; the stable key in `progress.db`; immutable once merged |
| `snake_slug` | `slug` with `-` replaced by `_`; used for Python modules and JVM packages |
| Reference files | `solutions/<approach-id>.<ext>`, ext in `py`, `ts`, `java`, `kt`, `go`, `rs`; every file maps to a declared approach. A [project problem](#project-problems) has a directory `solutions/<approach-id>/` instead, and a `starter/` tree |

## meta.yaml

Validated against `schemas/meta.schema.json`. The first line may carry `# yaml-language-server: $schema=../../schemas/meta.schema.json` for editor completion.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | Matches directory prefix |
| `slug` | string | yes | Matches directory suffix |
| `title` | string | yes | Original title (common names such as "Two Sum" are allowed) |
| `status` | `draft` or `ready` | yes | `ready` requirements: [authoring](authoring.md#ready-criteria) |
| `difficulty` | `easy`, `medium`, `hard` | yes | |
| `track` | `dsa`, `practical`, `lld`, `concurrency`, `debugging` | yes | Non-autograded tracks live in `tracks/` ([content](content.md)) |
| `kind` | `function`, `design`, `progressive`, `concurrent`, `project` | yes | `project`: [Project problems](#project-problems) |
| `patterns` | list of pattern ids | yes for `dsa` | First entry is the primary pattern; ids from [content](content.md#pattern-taxonomy) |
| `languages` | list of `python`, `typescript`, `java`, `kotlin`, `go`, `rust` | no | Default all six, which every problem lists, except a language that cannot express the problem: Rust where an `Option<Box<ListNode>>` cannot ([S13](authoring.md#static)), so `0055-linked-list-cycle` lists the other five. `concurrency` and `debugging` problems are the exception: they may list any subset of the six languages, so a Go- or Rust-native bug lists just `go` or `rust`, and the original debugging problems list the languages their bugs exist in ([ADR 0012](../decisions/0012-go-and-rust.md)). A `project` problem lists exactly one language, `python` or `typescript` ([Project problems](#project-problems), [ADR 0014](../decisions/0014-project-problems.md)). A problem you write in your own workspace is the exception to the catalog's rule: it lists any non-empty subset, and without a `languages` line it lists the four core languages (`python`, `typescript`, `java`, `kotlin`), what every problem listed before Go and Rust, so a problem written with an older `cstudy` keeps working. `cstudy new` writes the line explicitly. List `languages` in the catalog only where it differs from the default |
| `signature` | object | yes | See [Signatures](#signatures) |
| `comparator` | object | yes | See [Comparators](#comparators) |
| `stub` | `generated` or `buggy` | no | Default `generated`; `buggy` copies `buggy/solution.<ext>` instead of codegen. Buggy files follow the reference file conventions (no JVM `package` line) ([authoring](authoring.md#debugging-problems)) |
| `levels` | list | `progressive` and `project` only | See [Progressive problems](#progressive-problems) |
| `project` | object | `project` only | `entry` (required) and `tests`; see [Project problems](#project-problems) |
| `approaches` | list | yes, at least 1; exactly 1 for `project` | See [Approaches](#approaches-and-complexity) |
| `perf` | object | no | See [Performance block](#performance-block) |
| `limits.hang_guard_ms` | int | no | Overrides the per-case hang guard (default 10000) |
| `concurrency` | object | `concurrent` only | See [Concurrent problems](#concurrent-problems) |
| `references` | object | no | `leetcode: {number, url}`, `links: [url]` |
| `related` | list of slugs | no | |
| `order` | int | no | Curriculum order within the primary pattern (default 1000) |
| `estimate_minutes` | int | no | Expected interview solve time |

Hints are not in `meta.yaml`; they are the `## Hints` section of `problem.md`, so there is one source.

## Signatures

### Function

```yaml
signature:
  function:
    name: twoSum                 # lowerCamelCase canonical name
    params:
      - {name: nums, type: "int[]"}
      - {name: target, type: int}
    returns: {type: "int[]"}
```

### Class (design, progressive, concurrent, project)

```yaml
signature:
  class:
    name: LRUCache               # PascalCase
    constructor:
      params: [{name: capacity, type: int}]
    methods:
      - name: get
        params: [{name: key, type: int}]
        returns: {type: int}
      - name: put
        params: [{name: key, type: int}, {name: value, type: int}]
        returns: {type: void}
```

### Modifiers

| Modifier | On | Meaning |
|----------|----|---------|
| `output_from: <param>` | `returns` with `type: void` | In-place problems: the runner serializes that parameter after the call |
| `ref_of: <param>` | a node-typed param | The JSON value is a node value; the runner passes the first node (traversal order) in `<param>` whose `val` equals it. Values must be unique in `<param>` |
| `as: value` | node-typed `returns` | Serialize only the returned node's `val` (`null` when null) |
| `as: index`, `of: <param>` | node-typed `returns` | Serialize the returned node's position in `<param>` traversal order (`-1` when null; a node outside `<param>` is `invalid_output`); for duplicate-valued structures. Traversal order: [runners](runners.md#node-modifiers) |
| `no_alias_with: <param>` | node-typed `returns` | Fail with `invalid_output` if any returned node object is also reachable from `<param>` (deep-copy problems) |
| `level: <n>` | method | `progressive` and `project` only: the level that introduces the method |
| `blocking: true` | method | `concurrent` only: the method may wait for another worker. Async model: generated as an async method; threads model: Java adds `throws InterruptedException` ([Concurrent problems](#stubs-for-concurrent-problems)) |

Loading a problem rejects (content error) a modifier that names a parameter missing from its own function, constructor or method, or that sits on the wrong type: `ref_of` and `of` must name a parameter of the same node type, `output_from` needs a `void` return, `as` a node-typed return, and `blocking` a method of a `concurrent` problem.

### Naming rules

| Item | Canonical form | Python | TypeScript | Java | Kotlin | Go | Rust |
|------|----------------|--------|------------|------|--------|----|------|
| Function | `twoSum` | `two_sum` (module-level) | `twoSum` (named export) | `Solution.twoSum` | `Solution.twoSum` | `twoSum` | `two_sum` |
| Class | `LRUCache` | `LRUCache` | `LRUCache` (named export) | `LRUCache` | `LRUCache` | `LRUCache` | `LRUCache` |
| Constructor | `LRUCache` | `LRUCache(...)` | `new LRUCache(...)` | `new LRUCache(...)` | `LRUCache(...)` | `NewLRUCache` | `new` |
| Method | `getRandom` | `get_random` | `getRandom` | `getRandom` | `getRandom` | `GetRandom` | `get_random` |
| Param | `maxValue` | `max_value` | `maxValue` | `maxValue` | `maxValue` | `maxValue` | `max_value` |

Go and Rust follow these names in their stubs and runners ([ADR 0012](../decisions/0012-go-and-rust.md)). Go methods are exported because reflection only finds exported ones, and Go and Rust build an instance by calling a function, so the request names it in `names.constructor` ([runners](runners.md#request-file)).

- Canonical names match `^[a-z][A-Za-z0-9]*$` (classes `^[A-Z][A-Za-z0-9]*$`).
- snake_case conversion: insert `_` before an uppercase letter that follows a lowercase letter or digit, or that precedes a lowercase letter after another uppercase letter; then lowercase (`getHTTPCode` becomes `get_http_code`).
- After conversion, no name may equal a reserved word in any language the problem lists: Python `keyword.kwlist`, Java reserved keywords and literals, Kotlin hard keywords, TypeScript reserved words, Go keywords, and the Rust keywords `self`, `Self`, `super` and `crate`. Every other Rust keyword (strict, reserved and `async`/`await`/`dyn`/`try`) is a valid name: the Rust stub and the bridge write it as a raw identifier, so a method `move` is `pub fn r#move(&mut self, ...)` and is called as `instance.r#move(...)`. A language the problem does not list is not checked, so a parameter named `crate` conflicts only in a problem that lists `rust`. `cstudy verify` errors on a match and warns on shadowed Python builtins (`list`, `sum`, `id`, ...), and on a Python name equal to a type the stub imports: `date` in a signature that uses `date`, `Decimal` in one that uses `decimal`. A parameter `date: date` hides the type from the body, and a method named `date` hides it from the annotations after it. Go and Rust stubs import names too, Go the packages `time` and `decimal` and Rust the types `NaiveDate` and `Decimal`, where the signature uses `date` or `decimal`. A Go function or a Rust class with such a name does not compile (an error); a Go parameter with one hides the package from the body (a warning). Go methods are exported and Rust names are snake_case, so neither can collide.
- Python uses module-level functions (idiomatic) rather than LeetCode's `class Solution`; Java and Kotlin use `class Solution` (Java requires a class; Kotlin matches so both share one JVM runner).

## Type DSL

### Grammar

```text
type     := scalar | array | list | node | node "[]"
scalar   := "int" | "long" | "double" | "bool" | "string" | "char" | "decimal" | "date"
array    := scalar "[]" | scalar "[][]"
list     := "list<" elem ">"
elem     := scalar | scalar "[]" | list | node
node     := "ListNode" | "TreeNode" | "GraphNode"
return   := type | "void"
```

Maximum nesting depth is 3 (`list<list<list<int>>>`). Maps, sets, tuples and user-defined records are not in v1; problems use arrays or lists instead (for example `int[][]` for pairs). Money and calendar days are the scalars `decimal` and `date` ([Decimal and date](#decimal-and-date)).

### Type mapping

This table is normative for stub generation, runner deserialization and output serialization.

| DSL | JSON encoding | Python | TypeScript | Java | Kotlin |
|-----|---------------|--------|------------|------|--------|
| `int` | integer in [-2^31, 2^31-1] | `int` | `number` | `int` | `Int` |
| `long` | integer, abs value at most 2^53-1 | `int` | `number` | `long` | `Long` |
| `double` | finite number | `float` | `number` | `double` | `Double` |
| `bool` | `true` / `false` | `bool` | `boolean` | `boolean` | `Boolean` |
| `string` | string | `str` | `string` | `String` | `String` |
| `char` | string of length 1 (BMP) | `str` | `string` | `char` | `Char` |
| `decimal` | string, canonical when expected ([Decimal and date](#decimal-and-date)) | `Decimal` | `Decimal` | `BigDecimal` | `BigDecimal` |
| `date` | string `YYYY-MM-DD` | `date` | `IsoDate` (a `string`) | `LocalDate` | `LocalDate` |
| `int[]` | array | `list[int]` | `number[]` | `int[]` | `IntArray` |
| `long[]` | array | `list[int]` | `number[]` | `long[]` | `LongArray` |
| `double[]` | array | `list[float]` | `number[]` | `double[]` | `DoubleArray` |
| `bool[]` | array | `list[bool]` | `boolean[]` | `boolean[]` | `BooleanArray` |
| `char[]` | array of 1-char strings | `list[str]` | `string[]` | `char[]` | `CharArray` |
| `string[]` | array | `list[str]` | `string[]` | `String[]` | `Array<String>` |
| `decimal[]` | array of decimal strings | `list[Decimal]` | `Decimal[]` | `BigDecimal[]` | `Array<BigDecimal>` |
| `date[]` | array of date strings | `list[date]` | `IsoDate[]` | `LocalDate[]` | `Array<LocalDate>` |
| `int[][]` | array of arrays | `list[list[int]]` | `number[][]` | `int[][]` | `Array<IntArray>` |
| `long[][]` | array of arrays | `list[list[int]]` | `number[][]` | `long[][]` | `Array<LongArray>` |
| `double[][]` | array of arrays | `list[list[float]]` | `number[][]` | `double[][]` | `Array<DoubleArray>` |
| `bool[][]` | array of arrays | `list[list[bool]]` | `boolean[][]` | `boolean[][]` | `Array<BooleanArray>` |
| `char[][]` | array of arrays of 1-char strings | `list[list[str]]` | `string[][]` | `char[][]` | `Array<CharArray>` |
| `string[][]` | array of arrays | `list[list[str]]` | `string[][]` | `String[][]` | `Array<Array<String>>` |
| `decimal[][]` | array of arrays of decimal strings | `list[list[Decimal]]` | `Decimal[][]` | `BigDecimal[][]` | `Array<Array<BigDecimal>>` |
| `date[][]` | array of arrays of date strings | `list[list[date]]` | `IsoDate[][]` | `LocalDate[][]` | `Array<Array<LocalDate>>` |
| `list<int>` | array | `list[int]` | `number[]` | `List<Integer>` | `List<Int>` |
| `list<long>` | array | `list[int]` | `number[]` | `List<Long>` | `List<Long>` |
| `list<double>` | array | `list[float]` | `number[]` | `List<Double>` | `List<Double>` |
| `list<bool>` | array | `list[bool]` | `boolean[]` | `List<Boolean>` | `List<Boolean>` |
| `list<char>` | array of 1-char strings | `list[str]` | `string[]` | `List<Character>` | `List<Char>` |
| `list<string>` | array | `list[str]` | `string[]` | `List<String>` | `List<String>` |
| `list<decimal>` | array of decimal strings | `list[Decimal]` | `Decimal[]` | `List<BigDecimal>` | `List<BigDecimal>` |
| `list<date>` | array of date strings | `list[date]` | `IsoDate[]` | `List<LocalDate>` | `List<LocalDate>` |
| `list<int[]>` | array of arrays | `list[list[int]]` | `number[][]` | `List<int[]>` | `List<IntArray>` |
| `list<list<int>>` | array of arrays | `list[list[int]]` | `number[][]` | `List<List<Integer>>` | `List<List<Int>>` |
| `list<list<string>>` | array of arrays | `list[list[str]]` | `string[][]` | `List<List<String>>` | `List<List<String>>` |
| `ListNode` | [ListNode encoding](#listnode) | `ListNode \| None` | `ListNode \| null` | `ListNode` | `ListNode?` |
| `TreeNode` | [TreeNode encoding](#treenode) | `TreeNode \| None` | `TreeNode \| null` | `TreeNode` | `TreeNode?` |
| `GraphNode` | [GraphNode encoding](#graphnode) | `GraphNode \| None` | `GraphNode \| null` | `GraphNode` | `GraphNode?` |
| `ListNode[]` | array of ListNode encodings | `list[ListNode \| None]` | `(ListNode \| null)[]` | `ListNode[]` | `Array<ListNode?>` |
| `list<TreeNode>` | array of TreeNode encodings | `list[TreeNode \| None]` | `(TreeNode \| null)[]` | `List<TreeNode>` | `List<TreeNode?>` |
| `void` (return) | `null` unless `output_from` | `None` | `void` | `void` | `Unit` |

General rules for rows not listed: `list<X>` maps element-wise using the `X` row; nested `list<list<X>>` nests the element mapping. Node types are always nullable.

**JVM erasure property.** Every Kotlin type in the table erases to the same JVM type as the Java column (`IntArray` is `int[]`, `Array<IntArray>` is `int[][]`, non-null `Int` parameters are `int`, `List<Int>` is `java.util.List`, `Unit` returns are `void`). One JVM runner therefore serves both languages through Java reflection. Any future mapping must preserve this property or extend the JVM runner.

### Go and Rust mapping

The Go and Rust columns ([ADR 0012](../decisions/0012-go-and-rust.md)). The Go column is normative, like the table above, for its stub generator and runner. The Rust column is normative too, for the Rust stub generator and the generated bridge: the bridge spells every type, so a solution with another type (`&[i32]` for `int[]`, `usize` for `int`) is a `load_error` `SignatureMismatch`. The JSON encoding is the one of the table above. A Go runner requires the exact types: a named slice type or `[]int64` for `int[]` is a `load_error` `SignatureMismatch`.

| DSL | Go | Rust |
|-----|----|------|
| `int` | `int` (the encoder range-checks to 32 bits, otherwise `invalid_output`) | `i32` |
| `long` | `int64` | `i64` |
| `double` | `float64` (non-finite is `invalid_output`) | `f64` |
| `bool` / `string` | `bool` / `string` | `bool` / `String` (owned parameters, as on LeetCode) |
| `char` | `rune` | `char` |
| `T[]`, `list<T>` | `[]T`; a nil slice encodes as `[]` | `Vec<T>` |
| `T[][]`, `list<list<T>>` | `[][]T` | `Vec<Vec<T>>` |
| `decimal` | `decimal.Decimal` from `github.com/shopspring/decimal` v1.5.0, vendored ([runners](runners.md#go-build-details)) | `rust_decimal::Decimal` 1.43.0, vendored ([runners](runners.md#rust-build-details)); an input must fit its 96-bit mantissa and 28 digits after the point |
| `date` | `time.Time` at midnight in `time.UTC`; the encoder rejects another location, a time of day and years outside 0001 to 9999 | `chrono::NaiveDate` 0.4.45, vendored; the encoder rejects years outside 0001 to 9999 |
| `ListNode` | `*ListNode` with `Val`, `Next` | `Option<Box<ListNode>>` |
| `TreeNode` | `*TreeNode` | `Option<Rc<RefCell<TreeNode>>>` |
| `GraphNode` | `*GraphNode` with `Neighbors []*GraphNode` | `Option<Rc<RefCell<GraphNode>>>` with `neighbors: Vec<Rc<RefCell<GraphNode>>>` |
| `ListNode[]` | `[]*ListNode` | `Vec<Option<Box<ListNode>>>` |
| `void` (return) | no result | `()` |
| `output_from` | the slice shares its backing array, so in-place changes are visible | the parameter becomes `&mut Vec<T>` |
| `ref_of`, `as: index` | pointer identity | node addresses: the `Rc` of a tree or graph node ([runners](runners.md#node-modifiers)). A `Box` list cannot be cyclic and `ref_of` or `as: index` cannot name its nodes, so a problem with cyclic list inputs or list identity omits `rust` from `languages` ([S13](authoring.md#static)); `no_alias_with` on a list works |
| Design class | `type LRUCache struct{}`, `func NewLRUCache(capacity int) *LRUCache`, `func (c *LRUCache) Get(key int) int` | `pub struct LRUCache`, `pub fn new(capacity: i32) -> Self`, `&mut self` methods |

**Content rules that keep languages equivalent.** Test values must fit the declared type; expected outputs must not depend on integer overflow; `long` values stay within 2^53-1 (TypeScript `number`); `decimal` results state their scale and rounding mode ([Decimal and date](#decimal-and-date)); recursion depth implied by inputs stays at or under 3000 (Node's default stack).

### Decimal and date

`decimal` is exact base-10 arithmetic for money and rates; `date` is a calendar day. Both travel as JSON strings, never as numbers: a JSON number loses precision as a JavaScript number or a Python float.

| Type | JSON encoding | Rules |
|------|---------------|-------|
| `decimal` | String matching `^-?(0\|[1-9][0-9]*)(\.[0-9]+)?$` | At most 28 significant digits (Python's default context precision) and at most 28 digits after the point (`rust_decimal`'s scale, trailing zeros included), which `verify --static` enforces for every problem. An input keeps its scale: `"2500.00"` reaches the solution with scale 2. An expected value is canonical: no trailing fractional zeros, no bare `.`, and no `-0` (`"2500"`, never `"2500.00"`) |
| `date` | String `YYYY-MM-DD` matching `^[0-9]{4}-[0-9]{2}-[0-9]{2}$` | A real calendar day in years 0001 to 9999; `20240101`, `2024-1-1` and timestamps are rejected |

**Equality is numeric.** Each runner writes a returned `decimal` in canonical form (it strips trailing fractional zeros and the dot, and writes `-0` as `0`), so `2500.00` and `2500` come back as the same text, the comparators stay type-blind, and a rounding mistake still fails because it changes the number. `cstudy verify --static` rejects a non-canonical expected value and suggests the canonical form. A problem states the scale and rounding mode of every decimal result, because the scale is not compared.

**Generators** return `decimal` and `date` values as strings, because Python's `Decimal` and `date` objects are not JSON.

**Statements** (`cstudy show`, `.statements/`) print `decimal` and `date` values without quotes, typed by the signature, in arguments, operation arguments and outputs alike: `premium = 2500.50, start = 2026-01-01` and `Output: [1250.25, 0]`. A `string` stays quoted. Failure reports still show the JSON text.

### Support classes

| Language | Import in stubs | Definitions |
|----------|-----------------|-------------|
| Python | `from cs_support import ListNode, TreeNode, GraphNode` | dataclass-like classes with `val`, `next` / `left`, `right` / `neighbors` |
| TypeScript | `import { ListNode } from "#support";` | classes with `val`, `next` / `left`, `right` / `neighbors`; constructors with default args, no parameter properties |
| Java | `import cs.support.*;` | public mutable fields `val`, `next`, `left`, `right`, `neighbors` (`List<GraphNode>`); constructors `()`, `(val)`, `(val, ...)` |
| Kotlin | `import cs.support.*` | Same Java classes (platform types); field `val` is accessed as `` node.`val` ``, as on LeetCode |
| Go | `import "cstudy/support"`, then `type ListNode = support.ListNode` per node type used | structs with exported fields `Val`, `Next` / `Left`, `Right` / `Neighbors` (`[]*GraphNode`), in the runner module `cstudy`; build values with composite literals, `&ListNode{Val: 1}` |

Stubs import support classes only when the signature uses them. Java stubs always add `import java.util.*;`.

`decimal` and `date` need no support class except in TypeScript, where `Decimal` is a class of `#support` and a `date` is an `IsoDate`: the `#support` alias `type IsoDate = string` for a plain `YYYY-MM-DD` string, which names the format in signatures. Because the workspace compiles with `verbatimModuleSyntax`, a stub imports it as a type: `import type { IsoDate } from "#support";` on its own, or `import { Decimal, type IsoDate } from "#support";` after the classes. A stub imports the standard library types it uses: Python `from datetime import date` and `from decimal import Decimal`, Java and Kotlin `java.math.BigDecimal` and `java.time.LocalDate`, Go `github.com/shopspring/decimal` and `time`, Rust `rust_decimal::Decimal` and `chrono::NaiveDate`.

**TypeScript `Decimal`** is immutable and exact (a `bigint` unscaled value with a non-negative `scale`, both public and read-only), with no dependency to install:

| Member | Meaning |
|--------|---------|
| `new Decimal("2500.50")`, `new Decimal(42)`, `new Decimal(250050n, 2)` | From text (the scale is kept), from a safe integer, or from the unscaled value and scale; a non-integer `number` throws `RangeError` and malformed text `SyntaxError` |
| `plus`, `minus`, `times` | Exact; the result scale is the larger scale for `plus` and `minus`, the sum of the scales for `times` |
| `div(other, scale, mode)`, `round(scale, mode)` | The result has exactly `scale` digits after the point, like Java's `setScale` and Python's `quantize`. `mode` is a `RoundingMode` with Java's names: `"DOWN"` (toward zero), `"UP"` (away from zero), `"FLOOR"`, `"CEILING"`, and the nearest neighbor with ties `"HALF_UP"` (away from zero), `"HALF_DOWN"` (toward zero) or `"HALF_EVEN"` (to the even digit). `div` by zero throws `RangeError` |
| `movePointLeft(n)`, `movePointRight(n)` | Exact division or multiplication by `10^n`, never rounded: `new Decimal("2500.50").movePointLeft(3)` is `2.50050`. Left adds `n` to the scale; right subtracts it, but not below 0. A negative `n` moves the other way. big.js has no such method, so the names are Java's (Python's is `scaleb(-n)`): unlike `shiftLeft`, they say which way the point moves |
| `cmp`, `eq`, `lt`, `lte`, `gt`, `gte` | By value: `1.50` equals `1.5` |
| `abs`, `neg` | |
| `toFixed(scale?, mode?)`, `toString()` | Plain notation, never an exponent; `toString` keeps the scale (`"2500.50"`) and `toFixed` rounds first (`HALF_UP` by default) |

**Go and Rust** use their libraries' own APIs. Go's has no rounding-mode type: each mode is a method. Rust's `round_dp_with_strategy` takes a `RoundingStrategy`. In both, `places` is the number of digits after the point, like `scale`.

| TypeScript `Decimal`, Java `RoundingMode` | Go (`github.com/shopspring/decimal`) | Rust (`rust_decimal`) |
|---|---|---|
| `new Decimal("2500.50")`, `new Decimal(42)`, `new Decimal(250050n, 2)` | `decimal.RequireFromString("2500.50")` (or `NewFromString`, which returns an error), `decimal.NewFromInt(42)`, `decimal.New(250050, -2)` (an exponent, the negated scale) | `Decimal::from_str_exact("2500.50")` (`Decimal::from_str` rounds what does not fit), `Decimal::from(42)`, `Decimal::new(250050, 2)`; no `dec!` macro, which needs a proc-macro crate |
| `plus`, `minus`, `times`, `abs`, `neg` | `Add`, `Sub`, `Mul`, `Abs`, `Neg` | `+`, `-`, `*` (they panic on overflow; `checked_add` and the like return an `Option`), `abs()`, unary `-` |
| `cmp`, `eq`, `lt`, `lte`, `gt`, `gte` | `Cmp`, `Equal`, `LessThan`, `LessThanOrEqual`, `GreaterThan`, `GreaterThanOrEqual`; never `==`, which compares the representation | `cmp`, `==`, `<`, `<=`, `>`, `>=`: by value, `1.50 == 1.5` |
| `round(places, "HALF_UP")` | `Round(places)`: ties away from zero | `round_dp_with_strategy(places, RoundingStrategy::MidpointAwayFromZero)` |
| `"HALF_EVEN"` | `RoundBank(places)` | `MidpointNearestEven`, also `round_dp(places)` |
| `"HALF_DOWN"` | No method: `RoundDown(places)` when the dropped part is exactly half (`d.Sub(d.RoundDown(places)).Abs().Equal(decimal.New(5, -places-1))`), otherwise `Round(places)` | `MidpointTowardZero` |
| `"DOWN"`, `"UP"`, `"FLOOR"`, `"CEILING"` | `RoundDown` (or `Truncate`), `RoundUp`, `RoundFloor`, `RoundCeil` | `ToZero` (or `trunc_with_scale`), `AwayFromZero`, `ToNegativeInfinity`, `ToPositiveInfinity` |
| `div(other, places, "HALF_UP")` | `DivRound(other, places)`: the exact quotient, rounded once. `Div(other)` rounds to `DivisionPrecision` (16) places, so a following `Round` rounds twice; `QuoRem(other, places)` gives the remainder too | `/` keeps 28 significant digits and rounds the last, so `round_dp_with_strategy` after it rounds a second time. That changes a result only when the digits between the two roundings are all 9s, which a quotient by a small whole number, such as a count of days, never has |
| `movePointLeft(n)`, `movePointRight(n)` | `Shift(-n)`, `Shift(n)` | `set_scale(x.scale() + n)` (an error past 28 places) and `x * Decimal::from(10_i64.pow(n))` |
| `toFixed(places)` | `StringFixed(places)` (`HALF_UP`), `StringFixedBank(places)` | Round first, then `to_string()`: `format!("{:.2}", x)` truncates |

A Go `date` is a `time.Time` at midnight in `time.UTC`: build one with `time.Date(year, month, day, 0, 0, 0, 0, time.UTC)`. `AddDate(0, 0, n)` moves by days, but `AddDate(0, n, 0)` normalizes an overflow (31 January plus one month is 3 March), so month arithmetic clamps the day itself. Count days as `(end.Unix() - start.Unix()) / 86400`: `end.Sub(start)` is a `time.Duration`, which stops at about 292 years.

A Rust `date` is a `chrono::NaiveDate`, with no time or zone. `NaiveDate::from_ymd_opt(year, month, day)` returns `None` for a day that does not exist; `date + TimeDelta::days(n)` and `checked_add_days(Days::new(n))` move by days, and `checked_add_months(Months::new(n))` clamps the day to the month's last (31 January plus one month is 28 or 29 February); `(end - start).num_days()` counts days; `weekday()`, `year()`, `month()` and `day()` need `use chrono::Datelike;`. `Utc::now()` and `Local` are not available: the `clock` feature is off, and a case must not depend on the day it runs.

## Serialization of linked structures

### ListNode

| Value | JSON |
|-------|------|
| null | `[]` |
| 1 -> 2 -> 3 | `[1, 2, 3]` |
| Cycle (input only): tail links to index 1 | `{"values": [3, 2, 0, -4], "cycle_at": 1}` |

Output serialization walks `next` and stops at 100,000 nodes with `invalid_output` ("list too long or cyclic").

### TreeNode

Level order with `null` for missing children; trailing `null`s trimmed; `[]` is null.

```text
    3
   / \          [3, 9, 20, null, null, 15, 7]
  9  20
     / \
    15  7
```

### GraphNode

1-indexed adjacency list where node `i` has `val == i`. `[]` is null; `[[]]` is one node with no neighbors.

```json
[[2, 4], [1, 3], [2, 4], [1, 3]]
```

Output serialization: BFS from the returned node, collect reachable nodes, require vals to be exactly `1..k` (else `invalid_output`), emit neighbor lists in each node's `neighbors` order.

## tests.json

Validated against `schemas/tests.schema.json`.

```json
{
  "$schema": "../../schemas/tests.schema.json",
  "version": 1,
  "cases": []
}
```

| Case field | Type | Required | Notes |
|------------|------|----------|-------|
| `id` | string `^[a-z0-9-]+$` | yes | Unique; convention `ex1` (visible), `h1` (hidden), `g1` (generated) |
| `visible` | bool | no | Default `false`; visible cases are the statement's examples |
| `input` | object | `function` kind | Keys are canonical param names; values use the JSON encoding of the param type |
| `ops`, `args` | arrays | class kinds | [Operation sequences](#operation-sequences-design-problems) |
| `stress` | object | `concurrent` only | A concurrent scenario instead of `ops`/`args` ([Stress cases](#stress-cases)); always hidden |
| `expected` | any | yes, except `generate`, `stress` and `checker` cases | Checker problems may include one valid answer for display |
| `generate` | `{n, seed}` | no | Input from `generator.py`; expected computed by `perf.expected_from`; always hidden |
| `level` | int | `progressive` and `project` only | |
| `hang_guard_ms` | int | no | Per-case override |
| `note` | string | no | Author note shown on failure |

`cstudy verify --static` type-checks every input and expected value against the signature (ranges, char length, `decimal` and `date` strings, node encodings, op names and arities).

## Comparators

All comparison happens in the CLI core on canonical JSON values. Equality is type-strict for booleans (`true` never equals `1`); integers and floats compare by numeric value.

| `comparator.type` | Passes when | Typical use |
|-------------------|-------------|-------------|
| `exact` | Deep equality | Most problems |
| `unordered` | Top-level arrays are equal as multisets; elements compared with `exact` | Two Sum indices, permutations |
| `unordered-nested` | Top level is a multiset of inner arrays, each inner array also compared as a multiset (depth 2) | 3Sum, Group Anagrams, Subsets |
| `float` | Every number satisfies `abs(a - e) <= tol * max(1, abs(e))`; structure otherwise exact | Averages, probabilities, geometry; `tolerance` default `1e-6` |
| `checker` | `checker.py` returns `None` | Any valid topological order, any valid path, any valid partition |
| `ops` | Per-operation outputs equal; `per_method` overrides a method's comparator (`exact`, `unordered`, `unordered-nested`, `float`) | Design, progressive and project problems |

```yaml
comparator: {type: float, tolerance: 1.0e-5}
comparator: {type: ops, per_method: {topK: unordered}}
```

`checker.py` contract (stdlib only):

```python
def check(case_input: dict, output: object, expected: object | None) -> str | None:
    """Return None when output is a valid answer, else a one-line reason."""
```

Failure reports show input, expected and actual (each truncated to 200 characters) and, for arrays, the first differing index.

`decimal` and `date` values are strings to every comparator. Runners write decimals in canonical form, so `exact` is numeric equality for them, and `unordered` keys work because equal numbers have equal text. `float` tolerance applies to JSON numbers only, so a decimal is never compared with a tolerance; `cstudy verify --static` (S8) rejects `float`, as the comparator or a `per_method` entry, where the outputs it compares hold `decimal` and no `double`. A `checker.py` receives decimals and dates as strings and parses them itself (`Decimal(text)`, `date.fromisoformat(text)`).

## Operation sequences (design problems)

LeetCode-compatible. `ops[0]` is the class name (constructor) and `args[i]` are the arguments of `ops[i]`. `expected[i]` is the return value of `ops[i]`; constructors and `void` methods expect `null`.

```json
{
  "id": "ex1",
  "visible": true,
  "ops": ["LRUCache", "put", "put", "get", "put", "get", "get"],
  "args": [[2], [1, 1], [2, 2], [1], [3, 3], [2], [3]],
  "expected": [null, null, null, 1, null, -1, 3]
}
```

Content rules: design APIs report absence with sentinel values (for example `-1`), not exceptions; time-dependent behavior takes timestamps as explicit arguments and never reads a clock.

If op `k` throws, the case fails at op `k`; the report shows the ops prefix and the partial outputs.

## Progressive problems

A progressive problem is one class whose API grows across levels, as in multi-level practical assessments (for example an in-memory database: records, then scans, then TTL, then history).

```yaml
kind: progressive
levels:
  - {level: 1, title: Set and get}
  - {level: 2, title: Prefix scans}
  - {level: 3, title: TTL}
  - {level: 4, title: Point-in-time history}
signature:
  class:
    name: InMemoryDb
    constructor: {params: []}
    methods:
      - {name: set, level: 1, params: [{name: timestamp, type: long}, {name: key, type: string}, {name: field, type: string}, {name: value, type: string}], returns: {type: void}}
      - {name: get, level: 1, params: [{name: timestamp, type: long}, {name: key, type: string}, {name: field, type: string}], returns: {type: string}}
comparator: {type: ops}
```

| Rule | Detail |
|------|--------|
| Cases | Each case has `level`; a level-`L` case uses only methods with `level <= L`. Every level has cases; a `generate` case sits at the last level, because `generator.py` may call every method |
| Stub | Contains every method, each marked with a `Level <n>` comment and throwing "not implemented". Method names of later levels are therefore visible in the stub; their rules are not |
| Statement | `problem.md` has one `## Level <n>: <title>` section per level, in order, holding that level's operations, rules and `### Example` subsections; the example marker of a level-`L` visible case sits in the `## Level L` section. `## Statement`, `## Input`, `## Output` and `## Constraints` show at every level, so they describe only what holds for all levels (the class, absence values, timestamps) |
| Rendering | The rendered statement shows levels 1 to the unlocked level; one notice line replaces the locked levels, whose titles stay hidden; the metadata line ends with `level <unlocked> of <last>` |
| Unlock | `cstudy start` opens level 1 on a new attempt (`attempts.level_unlocked`); a resumed attempt keeps its level, a `--fresh` or review attempt starts again at level 1. `cstudy test` runs the cases of levels 1 to the unlocked level. A run of every one of those cases (no `--case`, no lower `--level`) that passes them all unlocks the next level and rewrites the statement; one run unlocks at most one level |
| Full pass | Only a run that passes the cases of every level is a full pass (`first_pass_at`, `cstudy done --rating`) |
| Missing values | Methods return `""` (string) or `-1` (number) for absence, stated in the level text |

Project problems share these rules, except the stub, the unlock and the language of the rendered names: [Project problems](#project-problems).

## Project problems

A project problem (`kind: project`, `track: practical`) is a folder of seeded files in one language. `cstudy start` copies the folder into the workspace, you edit its files or add new ones, and the problem opens in levels that build on the same code. Levels, level cases and the `ops` comparator work as for [progressive problems](#progressive-problems); what differs is the code (a folder, not a generated stub), the language (exactly one), the visible tests (native test files generated from `tests.json`) and what opens a level (`cstudy submit`, not `cstudy test`). Decision record: [ADR 0014](../decisions/0014-project-problems.md).

| Language | Project problems |
|----------|------------------|
| Python | Supported; native tests run with pytest |
| TypeScript | Supported; native tests run with `node:test` |
| Go | Supported; native tests run with `go test` ([Go project jobs](runners.md#go-project-jobs)) |
| Java | Supported; native tests run with JUnit 5 (Jupiter) on the JUnit Platform |
| Kotlin | Supported; native tests run with kotlin.test on JUnit 5 |
| Rust | Supported; native tests are libtest's `#[test]` functions, one process per test ([Rust projects](#rust-projects)) |

### Content tree

```text
problems/0249-bank-project-python/
  meta.yaml             # kind: project, languages: [python], levels, the graded API, the project block
  problem.md            # ## Project, then one "## Level <n>: <title>" section per level
  tests.json            # every case with its level
  starter/              # the seeded tree; cstudy start copies it to <workspace>/projects/<slug>/
    README.md           # the contract (entry class and module) and how to run the tests
    pyproject.toml      # tool settings only (Python)
    bank/bank.py        # the entry class Bank, with level 1's methods
    bank/models.py      # seeded model types
    tests/conftest.py   # optional test files from the author
  solutions/
    explanation.md      # one approach section, with "### Design"
    reference/          # the one approach: an overlay on starter/, changed and added files only
      bank/bank.py
      bank/ledger.py
```

The TypeScript pilot has the same shape, with `package.json`, `tsconfig.json`, `src/bank.ts`, `src/models.ts` and `tests/`. A Go project has `go.mod` at its root, the entry type in a `.go` file such as `bank.go`, and `tests/`. A Java project is a Gradle project of its own:

```text
problems/<id>-bank-project-java/
  meta.yaml                                  # project: {entry: bank.Bank, tests: src/test/java/bank}
  starter/
    README.md
    settings.gradle.kts, build.gradle.kts, gradle.properties
    gradle/wrapper/gradle-wrapper.properties
    src/main/java/bank/Bank.java             # the entry class Bank, with level 1's methods
    src/main/java/bank/Account.java          # seeded model types
    src/test/java/bank/AccountTest.java      # optional test files from the author
  solutions/reference/src/main/java/bank/Bank.java
```

A Kotlin project has `src/main/kotlin/` and `src/test/kotlin/` instead. A Rust project has `Cargo.toml`, `.cargo/config.toml`, `src/lib.rs` and its modules, and `tests/` ([Rust projects](#rust-projects)).

### meta.yaml

```yaml
# yaml-language-server: $schema=../../schemas/meta.schema.json
id: "0249"
slug: bank-project-python
title: Bank Project (Python)
status: draft
difficulty: hard
track: practical
kind: project
languages: [python]
levels:
  - {level: 1, title: Accounts and transfers}
  - {level: 2, title: Top spenders}
  - {level: 3, title: Scheduled transfers}
  - {level: 4, title: Merges and balance history}
signature:
  class:
    name: Bank
    constructor: {params: []}
    methods:
      - {name: createAccount, level: 1, params: [{name: timestamp, type: long}, {name: accountId, type: string}], returns: {type: bool}}
comparator: {type: ops}
project:
  entry: bank.bank      # Python: dotted module; TypeScript: src/bank.ts; Java and Kotlin: bank.Bank
  tests: tests          # where cstudy writes the generated level tests; default "tests" (Java: src/test/java/bank)
approaches:
  - {id: reference, name: Accounts with balance histories and a due-time heap, role: optimal, time: "...", space: "...", time_class: "n log n", space_class: "n"}
related: [bank-project-typescript, scheduled-transfers-bank]
estimate_minutes: 90
```

| Field | Rule |
|-------|------|
| `track` | `practical` |
| `languages` | Exactly one: `python`, `typescript`, `go`, `java`, `kotlin` or `rust` |
| `slug` | Ends in the language (`bank-project-python`): a version in another language is another problem, and slugs are unique |
| `levels` | Required, as for progressive problems |
| `signature` | A class signature: the entry class the grader constructs, canonical names, a `level` on every method |
| `comparator` | `ops`. Every method's comparator, the default `exact` or a `per_method` entry, is `exact`, `unordered` or `float`, because generated tests express only these. Java and Kotlin: on a method that returns an array or a list, `unordered` needs elements of `int`, `long`, `double`, `string` or `date`, which sort naturally, and `float` is not allowed |
| Types | Scalars, arrays and lists. No node types; no `decimal` in TypeScript, whose `Decimal` class comes from the runner's support module, which a project folder does not reach. Go takes `decimal` (the vendored `decimal.Decimal`, which the starter's `go.mod` reaches) and `date` (`time.Time`) Java and Kotlin: a method's result holds no array inside an array or a list, and no `decimal` inside either, since a generated test compares `BigDecimal` by its canonical text and arrays only through `assertArrayEquals` or `assertContentEquals`; parameters may take any of these types |
| `project.entry` | Python: the dotted module that defines the entry class (`bank.bank`), a file `bank/bank.py` or `bank/bank/__init__.py` under the project root. TypeScript: the path, relative to the root, of the file that exports the entry class by name (`src/bank.ts`). Go: the path, relative to the root, of the `.go` file that declares the entry type and its constructor `New<Class>` (`bank.go`, `bank/bank.go`), not a `_test.go` file; its directory is the package that `cstudy submit` grades Java and Kotlin: the fully qualified name of the entry class (`bank.Bank`), in a named package, whose simple name is the signature's class; the file is `src/main/java/bank/Bank.java` (Kotlin: `src/main/kotlin/bank/Bank.kt`). Rust: the crate, the starter's package name (`bank`), whose root `src/lib.rs` makes the entry class public at the crate root |
| `project.tests` | The directory, relative to the root, where `cstudy` writes the generated test files; default `tests`. Go: its last directory name is a Go identifier, because the generated files declare `package <name>_test` Java and Kotlin: a package directory under `src/test/java/` (Kotlin: `src/test/kotlin/`), such as `src/test/java/bank`; the default does not apply. Rust: `tests`, the directory Cargo takes integration tests from |
| `approaches` | Exactly one, with role `optimal` |
| Not allowed | `generator.py`, `checker.py`, `stress_checker.py`, `buggy/`, `stub`, `perf`, `concurrency`, `oracle`, and `generate` or `stress` cases |
| `related` | Lists every sibling in another language, and may list the problems it builds on |

A version in another language is built from scratch: its own id, slug, starter, `tests.json`, reference and explanation. Only the statement wording may be reused, with that language's names. Nothing is shared or inherited between siblings.

### Starter

| Item | Rule |
|------|------|
| Content | Every file the user starts with, in the project's own layout: the entry file, the build files, `README.md`, and any seeded modules and test files. UTF-8 text files only, at most 50 files and 256 KiB in all |
| Never | Build output and caches (`__pycache__`, `.pytest_cache`, `.ruff_cache`, `node_modules`, `.venv`; on the JVM `build`, `.gradle`, `.kotlin` and `.class` or `.jar` files), lock files (`uv.lock`, `pnpm-lock.yaml`, `package-lock.json`), symbolic links, and a file under `project.tests` with the name of a generated test file |
| Entry class | Defined at `project.entry` with level 1's methods only, each with a body that raises or throws "not implemented". Methods of later levels appear nowhere in the starter: each unlock names the methods to add. A starter may declare the API as an interface the entry class implements (an `abc.ABC` subclass, a TypeScript, Java or Kotlin `interface`), which also holds level 1's methods only. Java and Kotlin: the entry class is public, with a public constructor that takes the signature's constructor parameters |
| `README.md` | States the contract: the module or file and the class that must stay where they are, and how to run the tests with the language's own command |
| Python build file | `pyproject.toml` with exactly the tool tables below and nothing else: no `[project]` table, no `requires-python`, no `[tool.uv]`. A `requires-python` above the workspace venv's Python makes `uv run` delete the shared venv through the project's `.venv` link ([project folders](installation-and-workspaces.md#project-folders)). No `__init__.py` is needed for packages, and no `pyrightconfig.json` |
| TypeScript build files | `package.json` with `"type": "module"` and no dependencies; `tsconfig.json` as the workspace's (`module` `nodenext`, `noEmit`, `allowImportingTsExtensions`, `erasableSyntaxOnly`, `verbatimModuleSyntax`, `strict`) with `"types": ["node"]` and `"typeRoots": ["../../typescript/node_modules/@types"]`, so `node:test` and `node:assert` have types (TypeScript 6 loads no `@types` package that `types` does not list). Imports name files with their extension (`../src/bank.ts`); code uses erasable syntax only, since Node strips types and refuses the rest (a parameter property fails with `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX`) |
| Java and Kotlin build files | `settings.gradle.kts`, `build.gradle.kts`, `gradle.properties` and `gradle/wrapper/gradle-wrapper.properties`, byte for byte as `cstudy new --from-template project-java` (`project-kotlin`) writes them, with the slug as `rootProject.name`: every project builds the same way, offline, with what `cstudy doctor --fix` cached ([project folders](installation-and-workspaces.md#project-folders)). No `gradlew` of its own: the workspace's runs the build |
| Module names | Python: no top-level module or package named after a standard-library module (`random.py`, `types.py`, `typing.py`) or `pytest` |
| Go build files | `go.mod` at the root with `module <slug>`, the `go 1.24` directive, and no requirement but the vendored modules: `require github.com/shopspring/decimal v1.5.0` with `replace github.com/shopspring/decimal => ../../.cs/runtime/runners/go/third_party/github.com/shopspring/decimal`, which reaches the [runner runtime](installation-and-workspaces.md#runner-runtime)'s copy from `projects/<slug>/`, so no build needs the network or a `go.sum`. No `go.sum`, `go.work` or `go.work.sum`: `cstudy start` writes the folder's `go.work` ([project folders](installation-and-workspaces.md#project-folders)) |
| Go entry | The entry file declares a package other than `main`, since the grader imports it, and the entry type `<Class>` with its constructor `func New<Class>(...) *<Class>`, the [Go mapping](#go-and-rust-mapping) of a design class; level 1's methods panic with `not implemented` |

The Python starter's `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "--import-mode=importlib -p no:cacheprovider"

[tool.pyright]
venvPath = "."
venv = ".venv"
pythonVersion = "3.13"

[tool.ruff]
target-version = "py313"
```

`pythonpath` lets the tests import the project's modules without `__init__.py` files, `--import-mode=importlib` allows test files with the same base name in different directories, and `-p no:cacheprovider` keeps `.pytest_cache` out of the folder. pyright needs `venvPath` and `venv` to resolve `pytest` and `cs_support` through the `.venv` link. `testpaths` names `project.tests`.

The Java and Kotlin starters' `settings.gradle.kts`, here for the slug `bank-project-java`:

```kotlin
// This project's own Gradle build; open this folder in your IDE as a Gradle project.
// It finds the coding-study workspace by walking up to .cs/workspace.toml and builds with the
// workspace's version catalog and runner runtime, so keep this file as it is.
pluginManagement {
    var directory: File? = settingsDir
    while (directory != null && !directory.resolve(".cs/workspace.toml").isFile) {
        directory = directory.parentFile
    }
    val workspace = directory
        ?: throw GradleException("$settingsDir is not inside a coding-study workspace")
    extra["cs.workspace"] = workspace
    includeBuild(workspace.resolve(".cs/runtime/runners/jvm"))
}

val workspace = extra["cs.workspace"] as File

dependencyResolutionManagement {
    repositories {
        mavenCentral()
    }
    versionCatalogs {
        create("libs") {
            from(files(workspace.resolve("jvm/gradle/libs.versions.toml")))
        }
    }
}

rootProject.name = "bank-project-java"

includeBuild(workspace.resolve(".cs/runtime/runners/jvm"))
```

The settings walk up to the workspace marker, rather than naming `../..`, because the same files build in `projects/<slug>/` and in a reference's copy under `.cs/build/projects/` ([reference](#reference)). The `pluginManagement` block runs before the rest of the file and cannot share its variables, so it hands the workspace on through `extra`.

`build.gradle.kts`, Java, then Kotlin:

```kotlin
// Builds with JDK 21, JUnit 5 and the cstudy runner (the cs.project plugin); keep this file
// as it is.
plugins {
    id("cs.project")
}
```

```kotlin
// Builds with JDK 21, Kotlin, kotlin.test on JUnit 5 and the cstudy runner (the cs.project
// plugin); keep this file as it is.
plugins {
    alias(libs.plugins.kotlin.jvm)
    id("cs.project")
}
```

`gradle.properties` and `gradle/wrapper/gradle-wrapper.properties` are the workspace's `jvm/gradle.properties` and `jvm/gradle/wrapper/gradle-wrapper.properties`, so the folder's builds share the workspace's Gradle version and daemon, and an IDE opening the folder picks the same Gradle.

### Statement

`problem.md` has the progressive sections ([authoring](authoring.md#problemmd)) plus a required `## Project` section after `## Output`: what the starter holds, the entry contract, and how to run the tests natively. Its text uses the problem language's names (`create_account` in Python), and so does the rendered statement: example markers render operations with the language's method names, and each `## Level <n>` section starts with a generated line naming the methods that level adds, in the language's names, with parameter names and types as the language spells them (`Methods to add: create_account(timestamp: int, account_id: str) -> bool`; in Go, `CreateAccount(timestamp int64, accountId string) bool`; Java `boolean createAccount(long timestamp, String accountId)`; Kotlin `createAccount(timestamp: Long, accountId: String): Boolean`, without a return type for a `void` method). `## Statement`, `## Input`, `## Output`, `## Project` and `## Constraints` show at every level, so they describe only what holds for all levels and never a later level's methods.

### Generated test files

`cstudy` writes one native test file per level from that level's visible cases, in `project.tests` under the project root. It writes level 1's file when an attempt starts and each next level's file when that level opens, never over an existing file: the files are yours to edit and extend, and a missing file of an unlocked level is written again when the attempt resumes ([cli](cli.md#cstudy-start)).

| Item | Python | TypeScript |
|------|--------|------------|
| File | `<tests>/test_level_<n>.py` | `<tests>/level-<n>.test.ts` |
| Framework | pytest | `node:test` with `node:assert/strict` |
| One test per visible case | `def test_<case id, "-" as "_">() -> None:` | `test("<case id>", () => { ... });` |
| Case `note` | The test's docstring | A comment above the test |
| Header | A docstring naming the level and the problem, and `Yours to edit and extend: cstudy never rewrites this file.` | The same text as `//` comments |
| Import | `from <entry module> import <Class>` | `import { <Class> } from "<relative path to the entry file>";` |

| Rule | Detail |
|------|--------|
| Body | The constructor op becomes `bank = Bank(...)` (`const bank = new Bank(...)`), the instance named after the class in the language's case. Each later op becomes one statement in the language's method names: a call alone where the method returns `void`, otherwise an assertion on its result. A case with no other operation calls the constructor alone (`Bank(...)`), so no variable goes unused |
| `exact` | Python: `is True`, `is False` and `is None` for those values, since the core never equates `true` and `1`; `==` for everything else. TypeScript: `assert.equal` for scalars, `assert.deepEqual` for arrays and lists (both strict under `node:assert/strict`) |
| `unordered` | Both sides sorted before comparing: `sorted(...) == [...]` with the expected literal already sorted; `assert.deepEqual([...result].sort(), [...])`, JavaScript's default sort, which orders items by their text, with the expected literal sorted the same way (`[10, 100, 9]`) |
| `float` | Python: `pytest.approx(expected, rel=tol, abs=tol)`; TypeScript: a helper `assertClose(actual, expected, tol)` defined once in the file. Both pass exactly when `abs(a - e) <= tol * max(1, abs(e))` |
| Agreement | A generated test passes when the core comparator would pass the case and fails when it would fail it, with these exceptions. Python: `==` equates `True` with `1` and `False` with `0` where a number is expected, alone or inside a list, where the core does not. TypeScript: strict assertions compare numbers with `Object.is`, so a result of `-0` fails against `0`, which the core passes, since JSON has no negative zero; and the generated `unordered` comparison uses the default sort, which orders by text and keeps items of the same text in the order it found them, so an `unordered` list of lists whose different items join to the same text (`["a,b"]` and `["a", "b"]`) can fail |
| Values | Literals of the language, formatted as ruff and Prettier format them; `decimal` and `date` in Python as `Decimal("2500.50")` (a whole number as `Decimal(10)`, except `-0`, which stays `Decimal("-0")`) and `date.fromisoformat("2026-01-01")`, imported when used |

Java and Kotlin write a test class per level in the package of `project.tests`:

| Item | Java | Kotlin |
|------|------|--------|
| File | `<tests>/Level<n>Test.java` (`src/test/java/bank/Level1Test.java`) | `<tests>/Level<n>Test.kt` |
| Framework | JUnit 5 Jupiter: `org.junit.jupiter.api.Test` and the static methods of `org.junit.jupiter.api.Assertions` | kotlin.test on JUnit 5: `kotlin.test.Test` and its assertion functions |
| Package and class | `package <tests below src/test/java, "/" as ".">;`, then `class Level<n>Test` | `package ...` from `src/test/kotlin`, then `class Level<n>Test` |
| One test per visible case | `@Test void <case id, "-" as "_">()`, prefixed `case_` when that is no Java identifier or is a keyword | `@Test fun <case id>()`, in backticks when the id is no Kotlin identifier or is a keyword (``fun `ex-overdraft`()``) |
| Case `note` | `//` comment lines above `@Test` | The same |
| Header | The Python header's two lines as `//` comments, before `package` | The same |
| Import | `import <entry>;` when the entry class is in another package | `import <entry>` likewise |

| Rule | Java | Kotlin |
|------|------|--------|
| Body | `Bank bank = new Bank(...);`, the instance named after the class in lowerCamelCase; then one statement per op, a `void` call alone; a case with no other op is `new Bank(...);` | `val bank = Bank(...)`; the same statements; `Bank(...)` alone |
| `exact` | `assertTrue(...)` and `assertFalse(...)` for `true` and `false`, `assertNull(...)` for `null`; a `decimal` as its canonical text, `assertEquals("2500.5", x.stripTrailingZeros().toPlainString())`, since `BigDecimal.equals` compares the scale; `assertArrayEquals(new int[] {1, 2}, x)` for arrays; `assertEquals(expected, x)` for the rest | The same, with `assertContentEquals(intArrayOf(1, 2), x)` for arrays |
| `unordered` | A list as `assertEquals(List.of(...), x.stream().sorted().toList())`, an array as `assertArrayEquals(new int[] {...}, Arrays.stream(x).sorted().toArray())` (`.toArray(String[]::new)` and `.toArray(LocalDate[]::new)` for strings and dates), the expected literal already sorted as Java sorts it | `assertEquals(listOf(...), x.sorted())`, `assertContentEquals(intArrayOf(...), x.sortedArray())` |
| `float` | `assertEquals(expected, x, delta)` on a `double`, `delta` being `tol * max(1, abs(expected))` written as `2.5 * 1e-06` (or the tolerance alone when `abs(expected)` is at most 1), which the JVM computes to the same double as the core, so the test passes exactly when the core's comparator does | `assertEquals(expected, x, delta)` (kotlin.test's `absoluteTolerance`) |
| Values | `5`; `5L` for every `long`; `2.5` and `3.0`; `true`; `'a'`; `"ivy"`; `null`; `new BigDecimal("2500.50")`; `LocalDate.parse("2026-01-01")`; `new int[] {1, 2}` (`new int[][] {{1, 2}}` nested); `List.of(1, 2)`, or `Arrays.asList(...)` when an element is `null` | The same scalars, with `$` escaped in strings and `Int.MIN_VALUE` and `Long.MIN_VALUE` for the smallest values, which have no literal; `BigDecimal("2500.50")`; `intArrayOf(1, 2)` (`longArrayOf`, `doubleArrayOf`, `booleanArrayOf`, `charArrayOf`, and `arrayOf(...)` for other elements); `listOf(1, 2)` |
| Layout | 4-space indent; imports as Google Java style orders them: the static `Assertions` methods in one block, then the rest, each in ASCII order, with a blank line between; a blank line between tests. A statement over 100 columns puts its call's arguments on one continuation line 8 columns deeper, or failing that one argument per line, each laid out the same way | ktlint's official style: 4-space indent; one block of imports in ASCII order with `java`, `javax` and `kotlin` imports last. A statement over 140 columns puts each argument of its call on its own line 4 columns deeper, with a trailing comma, and the closing parenthesis on a line of its own |
| Agreement | As for Python and TypeScript, with no exception for `true` and `1`; `0.0` and `-0.0` differ under `exact`, as `assertEquals` compares doubles bit for bit | The same |

Generated level 1 tests from case `ex1` of `0248-scheduled-transfers-bank`:

```python
"""Level 1 examples of bank-project-python, written by `cstudy start`.

Yours to edit and extend: cstudy never rewrites this file.
"""

from bank.bank import Bank


def test_ex1() -> None:
    bank = Bank()
    assert bank.create_account(1, "ivy") is True
    assert bank.create_account(2, "leo") is True
    assert bank.create_account(3, "ivy") is False
    assert bank.deposit(4, "ivy", 800) == 800
    assert bank.deposit(5, "max", 50) == -1
```

```ts
// Level 1 examples of bank-project-typescript, written by `cstudy start`.
// Yours to edit and extend: cstudy never rewrites this file.
import assert from "node:assert/strict";
import { test } from "node:test";

import { Bank } from "../src/bank.ts";

test("ex1", () => {
  const bank = new Bank();
  assert.equal(bank.createAccount(1, "ivy"), true);
  assert.equal(bank.createAccount(2, "leo"), true);
  assert.equal(bank.createAccount(3, "ivy"), false);
  assert.equal(bank.deposit(4, "ivy", 800), 800);
});
```

```java
// Level 1 examples of bank-project-java, written by `cstudy start`.
// Yours to edit and extend: cstudy never rewrites this file.
package bank;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class Level1Test {
    @Test
    void ex1() {
        Bank bank = new Bank();
        assertTrue(bank.createAccount(1L, "ivy"));
        assertTrue(bank.createAccount(2L, "leo"));
        assertFalse(bank.createAccount(3L, "ivy"));
        assertEquals(800L, bank.deposit(4L, "ivy", 800L));
        assertEquals(-1L, bank.deposit(5L, "max", 50L));
    }
}
```

```kotlin
// Level 1 examples of bank-project-kotlin, written by `cstudy start`.
// Yours to edit and extend: cstudy never rewrites this file.
package bank

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class Level1Test {
    @Test
    fun ex1() {
        val bank = Bank()
        assertTrue(bank.createAccount(1L, "ivy"))
        assertTrue(bank.createAccount(2L, "leo"))
        assertFalse(bank.createAccount(3L, "ivy"))
        assertEquals(800L, bank.deposit(4L, "ivy", 800L))
        assertEquals(-1L, bank.deposit(5L, "max", 50L))
    }
}
```

#### Go test files

Go's generated files use the standard `testing` package and the [Go mapping](#go-and-rust-mapping) of every value. A file is an external test package: it reaches the entry's package by its import path, as `cstudy submit` does, and so it sees only what the package exports.

| Item | Go |
|------|----|
| File | `<tests>/level_<n>_test.go`, declaring `package <name>_test`, where `<name>` is the last directory name of `project.tests` (`package tests_test`) |
| One test per visible case | `func Test<Id>(t *testing.T)`: the case id with `-` as `_` and its first letter in upper case (`ex1` is `TestEx1`, `l2-ex1` is `TestL2_ex1`) |
| Case `note` | A `//` comment above the test |
| Header | The same text as `//` comments, then a blank line before the package clause |
| Import | `testing`; the entry's package by its import path, `<slug>` for an entry at the root or `<slug>/<directory>`, under an explicit name, so the file does not depend on the package's own: the entry's directory name, or the entry file's name without `.go` for an entry at the root (`bank "bank-project-go"` for `bank.go`, `ledger "bank-project-go/ledger"` for `ledger/bank.go`); `math`, `slices`, `time` and `github.com/shopspring/decimal` when used, in gofmt's groups |

| Rule | Go |
|------|----|
| Body | The constructor op becomes `b := bank.NewBank(...)`, the instance named after the class's first letter in lower case, or the class in lowerCamelCase when the test already uses that name (`t`, or the import's); `bank.NewBank(...)` alone when no other op follows. A `void` method's call stands alone; any other becomes `if got := b.CreateAccount(1, "ivy"); <mismatch> {` with `t.Errorf` naming the call, the result (`%v`) and the expected value as the file writes them |
| `exact` | `got != <value>` for scalars and dates; `!got` and `got` for `true` and `false`; `!got.Equal(<value>)` for a decimal; `!slices.Equal(got, <value>)` for a list, and `slices.EqualFunc` through nested lists and lists of decimals, with `slices.Equal` and `decimal.Decimal.Equal` |
| `unordered` | The result sorted first, with `slices.Sorted(slices.Values(...))`, or `slices.SortedFunc` with `slices.Compare`, `decimal.Decimal.Cmp` or `time.Time.Compare`, against a literal already sorted that way. Lists of numbers, strings, characters, decimals and dates, and lists of lists of numbers, strings and characters; any other `unordered` list cannot be generated, which `cstudy verify` reports |
| `float` | A function `closeTo(got, want float64) bool`, defined once in the file when used, which holds exactly when `abs(a - e) <= tol * max(1, abs(e))`; lists compare item by item with `slices.EqualFunc` |
| Agreement | As for Python and TypeScript, with one exception: `!=` on a `time.Time` that carries a monotonic clock reading, one derived from `time.Now()`, fails where the runner, which writes the date, passes it. A nil slice equals an empty one, as the runner encodes it |
| Values | Go literals laid out as gofmt keeps them, one statement per line: `[]string{"ivy", "leo"}`, `[][]int{{1, 2}, {3}}`, `'a'` for a `char`, `decimal.RequireFromString("2500.50")` for a `decimal` (an input keeps its scale) and `time.Date(2026, time.January, 1, 0, 0, 0, 0, time.UTC)` for a `date` |

```go
// Level 1 examples of bank-project-go, written by `cstudy start`.
// Yours to edit and extend: cstudy never rewrites this file.

package tests_test

import (
	"testing"

	bank "bank-project-go"
)

func TestEx1(t *testing.T) {
	b := bank.NewBank()
	if got := b.CreateAccount(1, "ivy"); !got {
		t.Errorf(`b.CreateAccount(1, "ivy") = %v, want true`, got)
	}
	if got := b.CreateAccount(3, "ivy"); got {
		t.Errorf(`b.CreateAccount(3, "ivy") = %v, want false`, got)
	}
	if got := b.Deposit(4, "ivy", 800); got != 800 {
		t.Errorf(`b.Deposit(4, "ivy", 800) = %v, want 800`, got)
	}
}
```

A generated file is in one package with every other test file of its directory, so a level file that calls a method you have not written yet stops that package from compiling: `cstudy test` reports one `error` for the package until the method exists, and `cstudy test --level N` leaves out the files of the levels above N.

### Rust projects

A Rust project is a library crate of its own: Cargo refuses a workspace member outside the workspace root, so the folder cannot join the workspace's `rust/` project ([ADR 0014](../decisions/0014-project-problems.md#rust-spike-k6)). `project.entry` is the crate, and `project.tests` is `tests`.

| Item | Rule |
|------|------|
| `Cargo.toml` | A `[package]` whose `name` is `project.entry`, with `edition = "2021"` and `rust-version = "1.80"`, and no `build`, `links` or `workspace` key. The only other tables are `[dependencies]` and `[dev-dependencies]`, and they may list only the vendored crates, each exactly as the runner declares it: `rust_decimal = { version = "=1.43.0", default-features = false, features = ["maths"] }` and `chrono = { version = "=0.4.45", default-features = false, features = ["std"] }`. A signature that uses `decimal` needs `rust_decimal` in `[dependencies]`, one that uses `date` needs `chrono`: the entry class declares their types, and the harness's copy of each crate is the same one |
| `.cargo/config.toml` | Points crates.io at the runtime's vendored crates, by a path relative to the folder, so that rust-analyzer and the native `cargo test` build offline. Its tables are exactly the ones below; `cstudy start` writes the file when a folder lacks it |
| Crate name | `project.entry`: lowercase letters, digits and `_`, starting with a letter; not a Rust keyword and not a crate the build or the tests already name (`std`, `core`, `alloc`, `proc_macro`, `test`, `user`, `cs_runner`, `cs_support`, `rust_decimal`, `chrono`, `arrayvec`, `num_traits`, `autocfg`) |
| Entry class | Public at the crate root, as `use bank::Bank;` imports it: declared in `src/lib.rs`, or in a module that `src/lib.rs` re-exports (`pub use bank::Bank;`). Methods are named in snake case and take `&mut self`, the constructor is `pub fn new(...) -> Self`, and the types are the [Rust mapping](#go-and-rust-mapping)'s, as a single-file stub declares them; a method of level 1 has the body `todo!()` |
| Never | `Cargo.lock`, `target/`, `build.rs`, `rust-toolchain` and `rust-toolchain.toml` |

The starter's `.cargo/config.toml`:

```toml
[source.crates-io]
replace-with = "cstudy-vendor"

[source.cstudy-vendor]
directory = "../../.cs/runtime/runners/rust/vendor"
```

A statement's `Methods to add:` line declares each method as the crate does: `create_account(&mut self, timestamp: i64, account_id: String) -> bool`, without `-> ...` for a method that returns nothing.

Generated test files:

| Item | Rust |
|------|------|
| File | `tests/level_<n>.rs`, an integration test: a crate of its own that uses the project's library |
| Framework | libtest, through `#[test]` functions |
| One test per visible case | `#[test] fn <case id, "-" as "_">()`; an id that is not a Rust identifier on its own, one that starts with a digit or is a keyword, gets the prefix `case_` (`case_1`, `case_loop`) |
| Case `note` | A `///` comment above the test |
| Header | `//!` comments naming the level and the problem, and `Yours to edit and extend: cstudy never rewrites this file.` |
| Import | `use <crate>::<Class>;`, and `use chrono::NaiveDate;` and `use rust_decimal::Decimal;` when a value needs them |
| Body | `let mut bank = Bank::new(...);`, the instance named after the class in snake case, then one statement per operation: the call alone for a method that returns nothing, otherwise an assertion on its result. A case with no other operation calls `Bank::new(...);` alone |
| `exact` | `assert!(...)` and `assert!(!...)` for a `bool`, `assert_eq!(result, expected)` for anything else, with `Vec::<T>::new()` for an empty list |
| `unordered` | `assert_eq!(sorted(result), expected)`, the expected list already in Rust's order, through a helper `sorted` defined once in the file. Its items must be ordered (`Ord`): a list holding doubles cannot be generated, and `cstudy verify` reports it |
| `float` | A helper `assert_close(actual, expected, tolerance)` defined once in the file, which passes exactly when `abs(a - e) <= tol * max(1, abs(e))`; for a list of doubles, `assert_all_close`, item by item after equal lengths. A `float` comparator on deeper lists of doubles cannot be generated, and `cstudy verify` reports it |
| Values | Rust literals as rustfmt formats them, within 100 columns; a `String` argument as `"ivy".to_string()` and an expected one as `"ivy"`, a `double` with a decimal point (`2.0`), a `char` as `'a'`, lists as `vec![...]`, a `decimal` as `Decimal::from_str_exact("2500.50").unwrap()` and a `date` as `NaiveDate::from_ymd_opt(2026, 1, 1).unwrap()` |
| Agreement | A generated test passes exactly when the core comparator would pass the case |

The file is laid out as rustfmt lays it out with its defaults, and it is clippy-clean for Rust 1.80. Generated level 1 tests from case `ex1` of `0248-scheduled-transfers-bank`:

```rust
//! Level 1 examples of bank-project-rust, written by `cstudy start`.
//!
//! Yours to edit and extend: cstudy never rewrites this file.

use bank::Bank;

#[test]
fn ex1() {
    let mut bank = Bank::new();
    assert!(bank.create_account(1, "ivy".to_string()));
    assert!(bank.create_account(2, "leo".to_string()));
    assert!(!bank.create_account(3, "ivy".to_string()));
    assert_eq!(bank.deposit(4, "ivy".to_string(), 800), 800);
    assert_eq!(bank.deposit(5, "max".to_string(), 50), -1);
}
```

### Levels and grading

| Rule | Detail |
|------|--------|
| Carry-over | One folder for every level: level 2 extends the code of level 1. Nothing is reset or replaced when a level opens |
| Native tests | `cstudy test` runs the generated files of the unlocked levels, the starter's test files and your own. Their verdict is feedback: no comparator runs on it, nothing is stored as a grade, and no level opens from it |
| Grading | `cstudy submit` sends the inputs of every case of levels 1 to the unlocked level, visible and hidden, to the runner, which constructs the entry class and calls the operations; the core's `ops` comparator judges each output, with the hang guard and failure rules of every case. Visible cases are graded from `tests.json` too, so editing a generated test file never changes a grade |
| Graded API | The runner checks only the methods of the levels it grades, so a method of a locked level never has to exist |
| Unlock | `cstudy start` opens level 1 on a new attempt; a resumed attempt keeps its level, and a `--fresh` or review attempt starts again at level 1. A submission of every case of levels 1 to the unlocked level (no lower `--level`) that passes them all opens the next level: it rewrites the statement and writes that level's test file. One submission opens at most one level |
| Every submission regrades | A submission at level N grades levels 1 to N again, because later rules change earlier results (a scheduled transfer that runs counts toward top spenders) |
| Full pass | A submission that passes every case of every level (`first_pass_at`) |
| Levels finished | What `cstudy done` grades from ([progress-and-scheduling](progress-and-scheduling.md#project-attempts)) |

### Reference

The one approach's reference is the directory `solutions/<approach-id>/`, an overlay on `starter/` that holds the changed and added files only and implements every level. `cstudy verify` copies `starter/`, then the overlay, into `.cs/build/projects/<slug>/<approach-id>/`, writes the generated test file of every level into the copy, and runs it ([runners](runners.md#project-jobs)). An overlay path stays inside the tree, and an overlay never deletes a starter file. `solutions/explanation.md` has the one approach section with every required subsection plus `### Design`: the files of the reference and what each is responsible for ([authoring](authoring.md#explanationmd)).

## Concurrent problems

A concurrent problem (`kind: concurrent`, `track: concurrency`) is a class whose methods several workers call at the same time. Decision record: [ADR 0006](../decisions/0006-concurrency-stress-testing.md).

| Case type | Runs | Passes when |
|-----------|------|-------------|
| Sequential (`ops`, `args`) | Once, single-threaded, exactly like a [design problem](#operation-sequences-design-problems) | The `ops` comparator matches `expected` |
| Stress (`stress`) | N runs per [variant](#models-and-language-support); each run executes worker scripts concurrently, then an optional single-threaded final sequence | Every run ends without error, invalid output or stall, and satisfies every invariant |

| Decision | Choice | Rejected alternative |
|----------|--------|----------------------|
| What a stress run checks | Invariants over all recorded op inputs and outputs, probe counters and a quiescent final sequence | Linearizability checking: NP-complete in general, needs per-op timestamps from 3 runtimes, and its counterexamples are hard to read |
| Who expands and judges | CLI core expands templates into explicit per-worker scripts and evaluates invariants; runners only execute and record | Scenario logic in each runner: 3 implementations of templates and invariants |
| Verdict over N runs | A case passes only if every run passes | Majority or threshold: a correct implementation satisfies every invariant on every schedule, so one failing run is a real bug |
| Proof that a scenario can catch bugs | Deliberately broken references that must fail in at least 9 of 10 runs (`cstudy verify` D7) | Trusting scenario design: a scenario that never interleaves passes everything |
| Strength of a pass | Evidence, not proof: the statement says so | Claiming thread safety from a green run |

### Models and language support

| Model | Workers are | Interleaving happens | Repeatability |
|-------|-------------|----------------------|---------------|
| `threads` | OS-scheduled threads released together by a start gate | JVM: anywhere, with true parallelism. Python: at GIL switch points, widened by [injected yields](#observable-races-in-python) | None: the same seed gives different schedules |
| `async` | Coroutines on one event loop (Python `asyncio` tasks, Node promise chains) started together | Only at `await` points | Deterministic: the same code and seed give the same schedule |

| Language | Model | Variants (each a separate verdict) | Notes |
|----------|-------|------------------------------------|-------|
| Java | `threads` | `platform`, `virtual` (from `concurrency.jvm_threads`) | `synchronized`, `volatile`, `java.util.concurrent`. On JDK 21 a virtual thread pins its carrier inside `synchronized` and `Object.wait`: still correct, only slower |
| Kotlin | `threads` | `platform`, `virtual` | Same JVM runner and JDK APIs (`@Volatile`, `synchronized(lock) {}`, `ReentrantLock.withLock`). Coroutines are not autograded in v1 (PRD Q5); every Kotlin concurrent problem has a coroutine paragraph in its explanation's `### Language notes` |
| Python | `threads` or `async`, one per problem | `thread` or `async` | CPython 3.13 with the GIL; which races a test can observe: [below](#observable-races-in-python) |
| TypeScript | `async` only | `async` | Node 24, one event loop; `worker_threads` is not supported (objects cannot be shared between isolates, only `SharedArrayBuffer`). Synchronous methods are atomic, so a problem whose race needs shared-memory threads omits `typescript` from `languages` |
| Go | `threads` only | `thread` | Goroutines released by a start gate, in parallel on up to `GOMAXPROCS` threads; `sync` primitives, channels and atomics. A data race is observable without injected yields, but a concurrent map write is a fatal runtime error (a crash), so broken references race on other state |
| Rust | `threads` only | `thread` | `std::thread` workers over a shared `Arc<T>` (`T: Send + Sync`); `Mutex`, `Condvar`, `RwLock` and atomics. A broken reference is a logic race, since safe Rust has no data races: check-then-act across two lock acquisitions, `if` instead of `while` around `Condvar::wait`, a lock-order deadlock, or a separate atomic load and store |

`concurrency.model` must give every language in `languages` a model from this table; anything else is a content error.

### Observable races in Python

With the GIL, a thread switch happens only between bytecode instructions at points where the interpreter checks for a pending switch. During a stress run the Python runner sets `sys.setswitchinterval(1e-5)` and, through `sys.monitoring`, yields with `time.sleep(0)` before a random fraction of the user file's lines (or instructions) executed by worker threads ([runners](runners.md#perturbation)).

| Bug pattern | Observable with `python_granularity: line` (default) | With `instruction` |
|-------------|------------------------------------------------------|--------------------|
| Check-then-act across lines (`if len(q) < cap:` then `q.append(x)`) | yes | yes |
| Read-modify-write across lines (`v = self.n`, then `self.n = v + 1`) | yes | yes |
| Read-modify-write on one line (`self.n += 1`, `d[k] += 1`) | no | yes |
| `if` instead of `while` around `Condition.wait` with 2 or more waiters | yes | yes |
| Deadlock: lock-order inversion, `notify` waking the wrong waiter | yes, as `stalled` | yes |
| One C-level operation on a builtin (`list.append`, `deque.popleft`, `dict.pop`) | no: atomic under the GIL | no |
| Missing memory visibility (`volatile`) | no: Python has no such bug | no |

Content rule: a Python broken reference must target a pattern marked observable for its granularity; `python_granularity: instruction` costs roughly 10 times more per op, so scenarios that need it keep Python iterations low through a per-language `repeat`.

### concurrency block in meta.yaml

```yaml
kind: concurrent
track: concurrency
languages: [java, kotlin, python, typescript]
concurrency:
  model: {java: threads, kotlin: threads, python: threads, typescript: async}   # or one string for all
  jvm_threads: [platform, virtual]
  runs: 3
  deadline_ms: 5000
  perturb: {yield_probability: 0.05, max_yields: 3, python_granularity: line}
  broken:
    - {id: no-lock, name: No lock, bug: "...", languages: [java, kotlin, python], caught_by: [s1]}
```

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `model` | `threads`, `async`, or a map from language to model | required | Constraints: [language table](#models-and-language-support) |
| `jvm_threads` | non-empty subset of `platform`, `virtual` | `[platform]` | Each entry is a separate variant of every stress case for Java and Kotlin |
| `runs` | int, 1 to 100 | 3 | Runs per stress case and variant in plain `cstudy test`; `cstudy test --stress N` overrides; `cstudy verify` always uses 10 unless `--stress N` |
| `deadline_ms` | int, 100 to 30000 | 5000 | Per run, from gate open until every worker finished; a stress case may override |
| `perturb.yield_probability` | number, 0 to 1 | 0.05 | Chance of a yield before each worker op, and before each injection point in Python threads |
| `perturb.max_yields` | int, 1 to 100 | 3 | A yield is 1 to `max_yields` scheduler yields, uniformly chosen |
| `perturb.python_granularity` | `line`, `instruction`, `none` | `line` | Python `threads` model only: injection points inside the user file |
| `broken` | list | required for `ready` | [Broken references](#broken-references) |

Other `meta.yaml` rules for `concurrent` problems:

| Field | Rule |
|-------|------|
| `comparator` | Must be `ops` (with optional `per_method`); used by sequential cases and `final.expected` |
| `signature` | `class` only; `blocking: true` marks methods that may wait |
| `approaches` | `id`, `name`, `role`, `time`, `space` as usual, and optional `languages` where an approach has references in fewer languages than the problem ([Approaches](#approaches-and-complexity)); `time_class`, `space_class` and `oracle` are not allowed |
| `perf`, `generator.py` | Not allowed: no bench, ladder, time limits or oracle for concurrent problems in v1 |

### Stress cases

```json
{
  "id": "s1",
  "note": "4 producers, 4 consumers, 1 observer on capacity 4",
  "stress": {
    "seed": 1000,
    "deadline_ms": 5000,
    "setup": {"ops": ["BoundedBlockingQueue"], "args": [[4]]},
    "workers": [
      {"group": "producer", "count": 4, "repeat": 500,
       "steps": [{"op": "put", "args": [{"$seq": {"start": 0, "worker_stride": 1000000, "step": 1}}]}]},
      {"group": "consumer", "count": 4, "repeat": 500, "steps": [{"op": "take", "args": []}]}
    ],
    "final": {"ops": ["size"], "args": [[]], "expected": [0]},
    "invariants": [
      {"type": "equal_multisets", "left": {"op": "put", "of": "arg0"}, "right": {"op": "take"}}
    ]
  }
}
```

| `stress` field | Required | Notes |
|----------------|----------|-------|
| `seed` | no (default 1) | Run `r` (0-based) uses seed `seed + r` for template expansion and runner perturbation |
| `deadline_ms` | no | Overrides `concurrency.deadline_ms` |
| `setup` | yes | `ops` and `args` as in operation sequences; `ops[0]` is the constructor; may prefill; runs single-threaded before the gate opens |
| `workers` | yes | One or more worker groups, at least 2 workers in total |
| `final` | no | `ops` and `args` (no constructor) run single-threaded on the same instance after every worker finished; optional `expected`, compared with the `ops` comparator |
| `invariants` | yes, unless `final.expected` is given | Checked in order after the run |
| `perturb` | no | Overrides `concurrency.perturb` field by field |

| Worker group field | Required | Notes |
|--------------------|----------|-------|
| `group` | yes | `^[a-z][a-z0-9-]*$`, unique within the case |
| `count` | yes | Workers in the group, at least 1 |
| `repeat` | yes | Iterations per worker: an int, or `{"default": 2000, "python": 300}` with per-language overrides |
| `steps` | exactly one of `steps`, `mix` | Every iteration runs all steps in order |
| `mix` | exactly one of `steps`, `mix` | Every iteration runs one step chosen by its `weight` (positive int) |

A step is `{"op": <method or harness op>, "args": [<value or template>, ...]}`, plus `weight` inside `mix`. Methods must exist in the signature with matching arity, and the constructor is not allowed in steps.

#### Templates

A template replaces one whole argument; templates do not nest inside arrays. The CLI expands them per run before sending the request, so runners only ever see literal values.

| Template | Value for worker `w` (index within its group) at iteration `i` |
|----------|---------------------------------------------------------------|
| `{"$seq": {"start": s, "worker_stride": k, "step": d}}` | `s + w * k + i * d` (`start` required, `step` default 1, `worker_stride` default 0) |
| `{"$rand": [lo, hi]}` | Uniform integer in `[lo, hi]` |
| `{"$pick": [v1, v2, ...]}` | One of the listed JSON values, uniformly |
| any other JSON value | Itself |

Randomness comes from one `random.Random(f"{seed + r}:{group}:{w}")` stream per worker, consumed in iteration order: in a `mix`, `rng.choices(steps, weights=...)` first, then the step's templates left to right. Expansion is therefore reproducible (NFR-4). `cstudy verify --static` checks every template's full value range against the parameter type, for example `start + (count - 1) * worker_stride + (repeat - 1) * step` against the `int` range.

#### Harness ops

Ops starting with `@` are implemented by the runner, not the user's class. Their output is `null`.

| Op | Args | Effect |
|----|------|--------|
| `@enter` | `[section, mode]`: a string name and `"exclusive"` or `"shared"` | Enter a probe section. Exclusive entry while anyone is inside, or shared entry while an exclusive holder is inside, counts one violation |
| `@exit` | `[section]` | Leave the section this worker entered last under that name |
| `@pause` | `[n]`, 1 to 1000 | Yield to the scheduler `n` times, to widen race windows ([runners](runners.md#harness-ops)) |

Within every iteration of a worker, `@enter` and `@exit` must be balanced and properly nested (static check). Probes measure the user's lock, not shared data, for example a read-write lock:

```json
{"group": "reader", "count": 6, "repeat": 400,
 "steps": [{"op": "acquireRead", "args": []}, {"op": "@enter", "args": ["data", "shared"]},
           {"op": "@pause", "args": [2]}, {"op": "@exit", "args": ["data"]}, {"op": "releaseRead", "args": []}]}
```

#### Run record

The CLI joins the expanded scripts with the runner's outputs into one record per run. Invariants and `stress_checker.py` read only this record.

```json
{
  "run": 0, "seed": 1000, "variant": "platform",
  "setup": [{"op": "BoundedBlockingQueue", "args": [4], "output": null}],
  "workers": [
    {"group": "producer", "index": 0, "ops": [{"op": "put", "args": [0], "output": null}]},
    {"group": "consumer", "index": 0, "ops": [{"op": "take", "args": [], "output": 2000001}]}
  ],
  "final": [{"op": "size", "args": [], "output": 0}],
  "sections": {"data": {"entries": 2400, "violations": 0, "max_occupancy": 6}}
}
```

#### Selectors

| Field | Default | Meaning |
|-------|---------|---------|
| `op` | required | Method name |
| `of` | `output` | `output`, or `arg0`, `arg1`, ... for an argument; a `void` method has no output to select (static error) |
| `group` | every group | Restrict to one worker group (setup and final belong to no group, so a `group` selector excludes them) |
| `scope` | `all` | `setup`, `workers`, `final` or `all` |

Values are collected in record order: setup, then workers (group declaration order, worker index, op order), then final. For `source_order`, each worker's values form one sequence, and setup and final are one sequence each.

#### Invariants

| `type` | Fields | Passes when | Typical bug caught |
|--------|--------|-------------|--------------------|
| `equal_multisets` | `left`, `right` (selectors) | Both select the same multiset | Lost or duplicated elements |
| `distinct` | `values` | No value occurs twice | Double delivery |
| `bounds` | `values`, `min` and/or `max` | Every value is within the bounds | Capacity overflow, negative balance |
| `count` | `values`, optional `equals`, `min` and/or `max` | The number of values (equal to `equals` when given) is within the bounds | A limiter granting too many permits |
| `sum` | `values`, `min` and/or `max` | The sum is within the bounds | Money or tokens not conserved |
| `source_order` | `values`, `stride` | In each sequence, values with the same `floor(v / stride)` strictly increase | FIFO order violated |
| `section` | `name`, `max_violations` (default 0), optional `min_occupancy`, `max_occupancy` | The probe counters are within the bounds | Mutual exclusion broken; a semaphore admitting too many or serializing everything |
| `checker` | `name` | `stress_checker.py` returns `None` for that name | Anything else, for example cached values matching their keys |

Values compare as canonical JSON, with the same type-strict equality as the comparators. `min` and `max` are inclusive.

Content rule: every invariant must hold on every schedule of a correct implementation. The only allowed exception is `min_occupancy` (it asserts that concurrency actually happened), and only when its section contains a `@pause` and the correct references pass it 10 of 10 times in `cstudy verify`.

`stress_checker.py` contract (stdlib only):

```python
def check(name: str, scenario: dict, run: dict) -> str | None:
    """Return None when the run record satisfies invariant `name`, else a one-line reason."""
```

`scenario` is the case's `stress` object as written in `tests.json`; `run` is the run record.

#### Evaluating a run and a case

1. Runner status: `error`, `invalid_output`, `stalled` (deadline passed) or `timeout` (hang guard) fails the run with that status.
2. `final.expected`, when present, is compared with the `ops` comparator.
3. Invariants are evaluated in order; every failing invariant contributes a reason (the first 3 are shown).

A stress case has one verdict per variant: `PASS` when all N runs pass, otherwise the status of the first failing run (`FAIL` for an expected value or invariant, `ERROR`, `INVALID`, `STALLED`, `TIMEOUT`) with `k/N runs passed` and up to 3 failing runs, each with its seed and reason. A problem passes when every sequential case and every (stress case, variant) passes.

In the `async` model a failing seed reproduces exactly: `cstudy test --case s1 --seed 1007 --stress 1`. In the `threads` model it does not; more runs (`--stress 20`) raise the chance of seeing it again.

### Broken references

Deliberately wrong references prove that each scenario can catch the bugs it was written for. They live in `solutions/broken/<id>.<ext>` and are declared in `concurrency.broken`.

| Field | Required | Notes |
|-------|----------|-------|
| `id` | yes | `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, unique across approach and broken ids; approach ids of concurrent problems must not start with `broken-` (materialized names would collide) |
| `name` | yes | Short display name |
| `bug` | yes | One line naming the bug class |
| `languages` | no | Subset of `languages`; default all |
| `caught_by` | yes | Stress case ids that must catch it |

| Rule | Detail |
|------|--------|
| Sequentially correct | A broken reference passes every sequential case, so the bug is a concurrency bug and not a logic error (`cstudy verify` D7) |
| Detection | It fails each `caught_by` case in at least 9 of 10 runs, per language and variant (D7); this is the Phase 5 exit criterion, checked for every problem |
| Correct references | Pass every stress case 10 of 10 times per variant (D6) |
| Coverage | `ready` requires at least one broken reference for every language in `languages` |
| Explanation | `## Broken: <id> (<name>)` section in `explanation.md` ([authoring](authoring.md#explanationmd)) |
| Display | `cstudy solution --broken [ID]` shows the code with its explanation section, as a "spot the bug" exercise |

### Stubs for concurrent problems

| Language | `threads` model | `async` model |
|----------|-----------------|---------------|
| Python | Plain methods | `blocking` methods are `async def`; others plain |
| TypeScript | not allowed | `blocking` methods are `async name(...): Promise<T>`; others plain |
| Java | `blocking` methods declare `throws InterruptedException`; imports add `java.util.concurrent.*` and `java.util.concurrent.locks.*` | not allowed |
| Kotlin | Plain methods (no checked exceptions) | not allowed |
| Go | Plain methods on `*T`: a `blocking` method blocks its goroutine | not allowed |
| Rust | Plain methods taking `&self`, since the worker threads share the instance, which must be `Send + Sync`: a `blocking` method blocks its thread | not allowed |

The stub header gains one line naming the model, for example `Concurrency: threads (platform and virtual)`. In the `async` model the runner awaits a method's return value whenever it is awaitable, declared `blocking` or not.

### Limits

| Limit | Value |
|-------|-------|
| Workers per run | 2 to 64 |
| Ops per run after expansion (setup, workers and final) | at most 20,000, which keeps a request with every run of every case under about 30 MB |
| Stress cases per problem | at most 6 (`ready`: at least 2) |
| Time limits | Never apply to stress cases; sequential cases follow the normal rules |
| Hang guard per stress run | `deadline_ms + 5000` ([runners](runners.md#concurrent-jobs)) |

### Worked example: bounded-blocking-queue

`problems/0190-bounded-blocking-queue/meta.yaml` (the id is whatever `cstudy new` assigns):

```yaml
# yaml-language-server: $schema=../../schemas/meta.schema.json
id: "0190"
slug: bounded-blocking-queue
title: Bounded Blocking Queue
status: ready
difficulty: medium
track: concurrency
kind: concurrent
languages: [java, kotlin, python, typescript]
signature:
  class:
    name: BoundedBlockingQueue
    constructor: {params: [{name: capacity, type: int}]}
    methods:
      - {name: put, blocking: true, params: [{name: value, type: int}], returns: {type: void}}
      - {name: take, blocking: true, params: [], returns: {type: int}}
      - {name: size, params: [], returns: {type: int}}
comparator: {type: ops}
concurrency:
  model: {java: threads, kotlin: threads, python: threads, typescript: async}
  jvm_threads: [platform, virtual]
  runs: 3
  deadline_ms: 5000
  broken:
    - id: no-lock
      name: Deque without a lock
      bug: Spin-waits on the size, then mutates a shared deque with no mutual exclusion
      languages: [java, kotlin, python]
      caught_by: [s1]
    - id: if-not-while
      name: Wait guarded by if
      bug: A woken worker does not re-check its condition, so another worker can invalidate it first
      caught_by: [s2]
approaches:
  - {id: monitor, name: One lock with two conditions, role: optimal, time: "O(1) per op", space: "O(capacity)"}
  - {id: semaphores, name: Two counting semaphores and a mutex, role: optimal, time: "O(1) per op", space: "O(capacity)"}
references:
  leetcode: {number: 1188, url: "https://leetcode.com/problems/design-bounded-blocking-queue/"}
related: [concurrency-limiter, read-write-lock]
estimate_minutes: 30
```

Reference files: `solutions/monitor.{py,ts,java,kt}`, `solutions/semaphores.{py,java,kt}` (`semaphores` has no TypeScript file, which is allowed because `monitor` covers every language), `solutions/broken/no-lock.{py,java,kt}`, `solutions/broken/if-not-while.{py,ts,java,kt}`. In TypeScript, `monitor` keeps FIFO queues of pending resolvers for takers and putters.

`tests.json`:

```json
{
  "$schema": "../../schemas/tests.schema.json",
  "version": 1,
  "cases": [
    {"id": "ex1", "visible": true,
     "ops": ["BoundedBlockingQueue", "put", "put", "size", "take", "take", "size"],
     "args": [[2], [5], [7], [], [], [], []],
     "expected": [null, null, null, 2, 5, 7, 0]},
    {"id": "ex2", "visible": true,
     "ops": ["BoundedBlockingQueue", "put", "take", "put", "size", "take"],
     "args": [[1], [3], [], [4], [], []],
     "expected": [null, null, 3, null, 1, 4]},
    {"id": "h1", "note": "interleaved fill and drain keeps FIFO order",
     "ops": ["BoundedBlockingQueue", "put", "put", "take", "put", "put", "size", "take", "take", "take", "size"],
     "args": [[3], [1], [2], [], [3], [4], [], [], [], [], []],
     "expected": [null, null, null, 1, null, null, 3, 2, 3, 4, 0]},
    {"id": "h2", "note": "zero and negative values",
     "ops": ["BoundedBlockingQueue", "put", "put", "take", "take"],
     "args": [[2], [0], [-5], [], []],
     "expected": [null, null, null, 0, -5]},
    {"id": "h3", "note": "duplicate values",
     "ops": ["BoundedBlockingQueue", "put", "put", "put", "size", "take", "take", "take"],
     "args": [[4], [9], [9], [9], [], [], [], []],
     "expected": [null, null, null, null, 3, 9, 9, 9]},
    {"id": "h4", "note": "filled exactly to capacity",
     "ops": ["BoundedBlockingQueue", "put", "put", "put", "size", "take", "take", "take", "size"],
     "args": [[3], [1], [2], [3], [], [], [], [], []],
     "expected": [null, null, null, null, 3, 1, 2, 3, 0]},
    {"id": "s1", "note": "4 producers, 4 consumers and a size observer on capacity 4",
     "stress": {
       "seed": 1000,
       "setup": {"ops": ["BoundedBlockingQueue"], "args": [[4]]},
       "workers": [
         {"group": "producer", "count": 4, "repeat": 500,
          "steps": [{"op": "put", "args": [{"$seq": {"start": 0, "worker_stride": 1000000}}]}]},
         {"group": "consumer", "count": 4, "repeat": 500,
          "steps": [{"op": "take", "args": []}]},
         {"group": "observer", "count": 1, "repeat": 500,
          "steps": [{"op": "size", "args": []}, {"op": "@pause", "args": [1]}]}
       ],
       "final": {"ops": ["size"], "args": [[]], "expected": [0]},
       "invariants": [
         {"type": "equal_multisets", "left": {"op": "put", "of": "arg0"}, "right": {"op": "take"}},
         {"type": "distinct", "values": {"op": "take"}},
         {"type": "source_order", "values": {"op": "take"}, "stride": 1000000},
         {"type": "bounds", "values": {"op": "size"}, "min": 0, "max": 4}
       ]
     }},
    {"id": "s2", "note": "capacity 1 forces a hand-off on every op",
     "stress": {
       "seed": 2000,
       "setup": {"ops": ["BoundedBlockingQueue"], "args": [[1]]},
       "workers": [
         {"group": "producer", "count": 3, "repeat": {"default": 1000, "python": 400},
          "steps": [{"op": "put", "args": [{"$seq": {"start": 1, "worker_stride": 1000000}}]}]},
         {"group": "consumer", "count": 3, "repeat": {"default": 1000, "python": 400},
          "steps": [{"op": "take", "args": []}]}
       ],
       "final": {"ops": ["size"], "args": [[]], "expected": [0]},
       "invariants": [
         {"type": "equal_multisets", "left": {"op": "put", "of": "arg0"}, "right": {"op": "take"}},
         {"type": "source_order", "values": {"op": "take"}, "stride": 1000000}
       ]
     }}
  ]
}
```

Why these cases catch the broken references:

| Broken | Language | Expected failure |
|--------|----------|------------------|
| `no-lock` | Java, Kotlin | Concurrent `ArrayDeque` mutation loses or duplicates elements (`equal_multisets`, `distinct`), returns `null` to an `int` (`ERROR`), or the JIT hoists the non-volatile size read out of the spin loop (`STALLED`) |
| `no-lock` | Python | Two consumers pass `while not self._items` before either calls `popleft` (line injection between them): `IndexError`, so `ERROR` |
| `if-not-while` | Java, Kotlin, Python | `notifyAll` / `notify_all` wakes several takers for one element; the second removes from an empty deque: `ERROR` |
| `if-not-while` | TypeScript | A resumed taker shifts after another taker emptied the array: `undefined` for `int`, so `INVALID` (deterministic for a given seed) |

Measured on the fixture copy of this problem (`cli/tests/fixtures/concurrency/`, `monitor` only), `cstudy verify --require-ready` with 10 runs per variant on 2026-10-25 at a load average of 2.5 on 11 cores:

| Reference | Java platform | Java virtual | Kotlin platform | Kotlin virtual | Python thread | TypeScript async |
|-----------|---------------|--------------|-----------------|----------------|---------------|------------------|
| `no-lock` on `s1` | 10/10 failed (`ERROR`) | 10/10 (`ERROR`) | 10/10 (`ERROR`) | 10/10 (`ERROR`) | 10/10 (`ERROR`) | not listed |
| `if-not-while` on `s2` | 10/10 (`ERROR`) | 10/10 (`ERROR`) | 10/10 (`ERROR`) | 10/10 (`ERROR`) | 10/10 (`ERROR`) | 10/10 (`INVALID`) |
| `monitor`, every stress case | 10/10 passed | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |

The slowest correct run took 76 ms (Python `s1`), 1.5% of the 5000 ms deadline; `cstudy verify` took 3 to 4 s per language with a warm Gradle daemon.

Generated stubs:

```python
# python/practice/bounded_blocking_queue.py
"""Bounded Blocking Queue. Statement: .statements/bounded-blocking-queue.md. Run: cstudy test bounded-blocking-queue

Concurrency: threads
"""


class BoundedBlockingQueue:
    def __init__(self, capacity: int) -> None:
        pass

    def put(self, value: int) -> None:
        raise NotImplementedError

    def take(self) -> int:
        raise NotImplementedError

    def size(self) -> int:
        raise NotImplementedError
```

```typescript
// typescript/practice/bounded-blocking-queue.ts
// Bounded Blocking Queue. Statement: .statements/bounded-blocking-queue.md. Run: cstudy test bounded-blocking-queue
// Concurrency: async
export class BoundedBlockingQueue {
  constructor(capacity: number) {}

  async put(value: number): Promise<void> {
    throw new Error("Not implemented");
  }

  async take(): Promise<number> {
    throw new Error("Not implemented");
  }

  size(): number {
    throw new Error("Not implemented");
  }
}
```

```java
// jvm/java/src/main/java/practice/bounded_blocking_queue/BoundedBlockingQueue.java
// Bounded Blocking Queue. Statement: .statements/bounded-blocking-queue.md. Run: cstudy test bounded-blocking-queue
// Concurrency: threads (platform and virtual)

package practice.bounded_blocking_queue;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.locks.*;

public class BoundedBlockingQueue {
    public BoundedBlockingQueue(int capacity) {
    }

    public void put(int value) throws InterruptedException {
        throw new UnsupportedOperationException("Not implemented");
    }

    public int take() throws InterruptedException {
        throw new UnsupportedOperationException("Not implemented");
    }

    public int size() {
        throw new UnsupportedOperationException("Not implemented");
    }
}
```

```kotlin
// jvm/kotlin/src/main/kotlin/practice/bounded_blocking_queue/BoundedBlockingQueue.kt
// Bounded Blocking Queue. Statement: .statements/bounded-blocking-queue.md. Run: cstudy test bounded-blocking-queue
// Concurrency: threads (platform and virtual)

package practice.bounded_blocking_queue

class BoundedBlockingQueue(capacity: Int) {
    fun put(value: Int) {
        TODO("Not implemented")
    }

    fun take(): Int {
        TODO("Not implemented")
    }

    fun size(): Int {
        TODO("Not implemented")
    }
}
```

A Python problem with `model: async` generates `async def put(self, value: int) -> None:` and `async def take(self) -> int:` instead.

## Generated cases and generator.py

```python
import random

def generate(rng: random.Random, n: int) -> dict:
    """Return one input. function kind: {param: value}. class kinds: {"ops": [...], "args": [...]}."""

def validate(case_input: dict) -> None:  # optional
    """Raise AssertionError if the input violates the problem's constraints."""
```

| Rule | Detail |
|------|--------|
| Dependencies | Python stdlib only; all randomness from `rng` |
| Value types | `decimal` and `date` values are strings, because `Decimal` and `date` objects are not JSON |
| Determinism | Same `(seed, n)` yields identical output; `cstudy verify` checks by calling twice |
| Size meaning | `n` is the size parameter named in `perf.size_param`; the generator maps it to all dimensions |
| Users | Generated test cases, oracle cross-check (`cstudy verify --oracle`), oracle inputs of `cstudy test --stress N` ([cli](cli.md#oracle-inputs)), bench size ladder |
| Expected values | For `generate` cases: output of `perf.expected_from` (a Python approach) via the Python runner, cached in `.cs/cases/`; for `cstudy test --stress` oracle inputs: output of the `oracle` approach, cached the same way under its own key |

## Approaches and complexity

`solutions/` holds several reference approaches (for example brute force, better, optimal). Together they form the problem's complexity ladder ([performance-analysis](performance-analysis.md)).

```yaml
approaches:
  - id: brute-force             # matches solutions/brute-force.<ext>
    name: Check every pair
    role: brute                 # brute | intermediate | optimal
    time: "O(n^2)"              # human notation, may use several variables
    space: "O(1)"
    time_class: "n^2"           # growth in the size-ladder parameter n
    space_class: "1"
    oracle: true                # at most one; must exist in Python
  - id: hash-map
    name: One-pass hash map
    role: optimal
    time: "O(n)"
    space: "O(n)"
    time_class: "n"
    space_class: "n"
```

Complexity classes, ordered: `1`, `log n`, `sqrt n`, `n`, `n log n`, `n^2`, `n^2 log n`, `n^3`, `2^n`, `n!`. At least one approach has `role: optimal`; several may (for example heap and quickselect).

Every approach has a reference in every language the problem lists. A `concurrency` or `debugging` problem may name fewer for one approach, with `languages` (a subset of the problem's), where a language has no equivalent of the technique: `0201-bounded-blocking-queue`'s `semaphores` lists `languages: [java, kotlin, python, go]`, since neither TypeScript nor Rust's standard library has a semaphore. The explanation says why in the approach's language notes. A reference file in a language the approach does not name is a static error (S7), and a missing one in a language it names fails the [ready criteria](authoring.md#ready-criteria).

## Performance block

```yaml
perf:
  size_param: n                         # what n means, for display
  size_ladder: [100, 1000, 10000, 100000, 1000000]   # never above the stated constraints
  budget_ms: 2000                       # one run above this stops the ladder for that target
  expected_from: hash-map               # Python approach that computes expected for generated cases
  time_limit: {factor: 5}               # suggestion when time limits are enabled; or {ms: 1500}
```

| Field | Default |
|-------|---------|
| `size_ladder` | `[100, 1000, 10000, 100000]` |
| `budget_ms` | `2000` |
| `expected_from` | first `optimal` approach with a Python file |
| `time_limit` | none; the built-in default applies (see [performance-analysis](performance-analysis.md#time-limits)) |

`meta.yaml` can only suggest a time-limit value. Time limits are off unless enabled by flag or user config ([cli](cli.md#configuration)).

## Worked example: two-sum

`problems/0001-two-sum/meta.yaml`:

```yaml
# yaml-language-server: $schema=../../schemas/meta.schema.json
id: "0001"
slug: two-sum
title: Two Sum
status: ready
difficulty: easy
track: dsa
kind: function
patterns: [arrays-hashing]
signature:
  function:
    name: twoSum
    params:
      - {name: nums, type: "int[]"}
      - {name: target, type: int}
    returns: {type: "int[]"}
comparator: {type: unordered}
approaches:
  - {id: brute-force, name: Check every pair, role: brute, time: "O(n^2)", space: "O(1)", time_class: "n^2", space_class: "1", oracle: true}
  - {id: hash-map, name: One-pass hash map, role: optimal, time: "O(n)", space: "O(n)", time_class: "n", space_class: "n"}
perf:
  size_param: n
  size_ladder: [100, 1000, 10000, 100000]
  expected_from: hash-map
  time_limit: {factor: 5}
references:
  leetcode: {number: 1, url: "https://leetcode.com/problems/two-sum/"}
related: [three-sum]
estimate_minutes: 15
```

`tests.json` (excerpt):

```json
{
  "$schema": "../../schemas/tests.schema.json",
  "version": 1,
  "cases": [
    {"id": "ex1", "visible": true, "input": {"nums": [4, 9, 2, 8], "target": 11}, "expected": [1, 2]},
    {"id": "ex2", "visible": true, "input": {"nums": [5, 5], "target": 10}, "expected": [0, 1]},
    {"id": "h1", "input": {"nums": [-3, 8, 0, 3], "target": 0}, "expected": [0, 3]},
    {"id": "g1", "generate": {"n": 100000, "seed": 1}}
  ]
}
```

`generator.py`:

```python
import random

def generate(rng: random.Random, n: int) -> dict:
    # n - 1 distinct even numbers plus one odd number; an odd target forces the
    # unique answer to be (odd, chosen even), matching the statement's guarantee.
    nums = [2 * v for v in rng.sample(range(-4 * 10**8, 4 * 10**8), n - 1)]
    odd = 2 * rng.randrange(-10**8, 10**8) + 1
    target = odd + rng.choice(nums)
    nums.insert(rng.randrange(n), odd)
    return {"nums": nums, "target": target}
```

The statement guarantees exactly one answer, so `unordered` suffices. A generator that cannot guarantee uniqueness must be paired with a `checker` comparator instead.

Generated stubs:

```python
# python/practice/two_sum.py
"""Two Sum. Statement: .statements/two-sum.md. Run: cstudy test two-sum"""


def two_sum(nums: list[int], target: int) -> list[int]:
    raise NotImplementedError
```

```typescript
// typescript/practice/two-sum.ts
// Two Sum. Statement: .statements/two-sum.md. Run: cstudy test two-sum
export function twoSum(nums: number[], target: number): number[] {
  throw new Error("Not implemented");
}
```

```java
// jvm/java/src/main/java/practice/two_sum/Solution.java
// Two Sum. Statement: .statements/two-sum.md. Run: cstudy test two-sum

package practice.two_sum;

import java.util.*;

public class Solution {
    public int[] twoSum(int[] nums, int target) {
        throw new UnsupportedOperationException("Not implemented");
    }
}
```

```kotlin
// jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt
// Two Sum. Statement: .statements/two-sum.md. Run: cstudy test two-sum

package practice.two_sum

class Solution {
    fun twoSum(nums: IntArray, target: Int): IntArray {
        TODO("Not implemented")
    }
}
```

```go
// go/practice/two_sum/two_sum.go
// Two Sum. Statement: .statements/two-sum.md. Run: cstudy test two-sum

package two_sum

func twoSum(nums []int, target int) []int {
	panic("not implemented")
}
```

```rust
// rust/practice/two_sum.rs
// Two Sum. Statement: .statements/two-sum.md. Run: cstudy test two-sum

pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {
    todo!()
}
```

## Worked example: lru-cache

```yaml
id: "0002"
slug: lru-cache
title: LRU Cache
status: ready
difficulty: medium
track: dsa
kind: design
patterns: [linked-list, arrays-hashing]
signature:
  class:
    name: LRUCache
    constructor: {params: [{name: capacity, type: int}]}
    methods:
      - {name: get, params: [{name: key, type: int}], returns: {type: int}}
      - {name: put, params: [{name: key, type: int}, {name: value, type: int}], returns: {type: void}}
comparator: {type: ops}
approaches:
  - {id: ordered-scan, name: List with linear scan, role: brute, time: "O(capacity) per op", space: "O(capacity)", time_class: "n^2", space_class: "n", oracle: true}
  - {id: hash-map-dll, name: Hash map plus doubly linked list, role: optimal, time: "O(1) per op", space: "O(capacity)", time_class: "n", space_class: "n"}
perf:
  size_param: number of operations, capacity n/10
  size_ladder: [1000, 10000, 100000]
  expected_from: hash-map-dll
references:
  leetcode: {number: 146, url: "https://leetcode.com/problems/lru-cache/"}
```

For design problems `time_class` describes the whole generated op sequence of length `n`, which is why the brute force is `n^2`.

Stubs (constructors never throw, so the first failing op points at an unimplemented method):

```python
# python/practice/lru_cache.py
"""LRU Cache. Statement: .statements/lru-cache.md. Run: cstudy test lru-cache"""


class LRUCache:
    def __init__(self, capacity: int) -> None:
        pass

    def get(self, key: int) -> int:
        raise NotImplementedError

    def put(self, key: int, value: int) -> None:
        raise NotImplementedError
```

```typescript
// typescript/practice/lru-cache.ts
// LRU Cache. Statement: .statements/lru-cache.md. Run: cstudy test lru-cache
export class LRUCache {
  constructor(capacity: number) {}

  get(key: number): number {
    throw new Error("Not implemented");
  }

  put(key: number, value: number): void {
    throw new Error("Not implemented");
  }
}
```

```java
// jvm/java/src/main/java/practice/lru_cache/LRUCache.java
// LRU Cache. Statement: .statements/lru-cache.md. Run: cstudy test lru-cache

package practice.lru_cache;

import java.util.*;

public class LRUCache {
    public LRUCache(int capacity) {
    }

    public int get(int key) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public void put(int key, int value) {
        throw new UnsupportedOperationException("Not implemented");
    }
}
```

```kotlin
// jvm/kotlin/src/main/kotlin/practice/lru_cache/LRUCache.kt
// LRU Cache. Statement: .statements/lru-cache.md. Run: cstudy test lru-cache

package practice.lru_cache

class LRUCache(capacity: Int) {
    fun get(key: Int): Int {
        TODO("Not implemented")
    }

    fun put(key: Int, value: Int) {
        TODO("Not implemented")
    }
}
```

```go
// go/practice/lru_cache/lru_cache.go
// LRU Cache. Statement: .statements/lru-cache.md. Run: cstudy test lru-cache

package lru_cache

type LRUCache struct{}

func NewLRUCache(capacity int) *LRUCache {
	return &LRUCache{}
}

func (c *LRUCache) Get(key int) int {
	panic("not implemented")
}

func (c *LRUCache) Put(key int, value int) {
	panic("not implemented")
}
```

```rust
// rust/practice/lru_cache.rs
// LRU Cache. Statement: .statements/lru-cache.md. Run: cstudy test lru-cache

pub struct LRUCache {}

impl LRUCache {
    pub fn new(capacity: i32) -> Self {
        LRUCache {}
    }

    pub fn get(&mut self, key: i32) -> i32 {
        todo!()
    }

    pub fn put(&mut self, key: i32, value: i32) {
        todo!()
    }
}
```
