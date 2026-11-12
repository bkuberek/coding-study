# Layered Values and Templates: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| merge-parse-render | optimal | O(R + V log V) per merged, provenance or validate, for R rows in all layers and V merged values; render adds O(T + P) for a template of T characters and P printed characters | O(R + T + P) | default answer; one tree of nodes that carry their layer serves all four levels |

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Rows become trees; layers merge into a fresh tree | an ordered map from layer name to the layer's tree |
| 2 | A scanner and a small parser for tags; rendering by lookup | nothing new: a template is parsed and rendered on each call |
| 3 | Block tags nest into a tree; a list of loop bindings | nothing new: the parse builds a tree instead of a flat list |
| 4 | Each node remembers its layer; a schema tree; a validator | the schema's tree |

Two early choices keep the later levels small. The first is to merge into a new tree on every call instead of keeping one merged tree up to date: replacing a layer in the middle of the order is then free, and provenance at level 4 is one more field that the merge fills in. The second is to parse the whole template before rendering anything. Level 2 needs it already, because a malformed tag late in the template must win over a missing value early in it, and at level 3 the same pass is where the stack of open blocks lives.

## Approach: merge-parse-render (Merge into a tree, parse the template once, render with a stack of bindings)

### Intuition

Rows are a flat spelling of a tree, and every rule of the problem is a rule about trees: merging walks two objects side by side, a path walks down from the root, a schema walks beside the values. So turn rows into nodes first, and do all the work on nodes. A node is an object with members, a list with items, or a scalar with a kind and a text; it also records the layer that set it.

A template is a small language. It has a lexical part (where tags start and end, what a string literal is), a grammar (which tag forms exist, how blocks nest) and a meaning (what each form prints). Keeping the three apart makes each rule of the statement land in one place: a missing `}}` is lexical, an `else` inside a `for` is grammar, and a missing value is meaning, found only while rendering.

### Algorithm

1. Level 1: `setLayer` decodes the rows into a tree. Split each pointer on `/`, follow all segments but the last from the root to the parent (which exists, since parents come first), and add the node under the last segment. Layers live in a map that keeps insertion order, so replacing a layer keeps its place. `merged` starts from an empty object and, for every layer in order, applies its members: a `null` removes the key, an object merges into an existing object or into a new one, and anything else replaces the key with a deep copy. It then walks the result depth first, keys sorted, items by index, and writes one row per node.
2. Level 2: `parse` scans the template. It finds the next `{{`, then the first `}}` after it (`unclosed_tag` when there is none), and cuts the inside into tokens: words of letters, digits, `_` and `.`, string literals with their two escapes, and the punctuation `|` and `,`. The list of token kinds decides the form: one string, one path, or a path, `|`, `default` and a string. Anything else is `bad_expression`. Only after the whole template parses does rendering start: a substitution looks its path up and prints a scalar's text, uses the default for a missing value or a `null`, and raises `missing_value` or `not_scalar` otherwise. An error carries the offset of its tag's `{{`, turned into a line and a column only when reported.
3. Level 3: the scan also keeps a stack of open blocks. `if` and `for` push, `else` marks the top `if` (`unexpected_tag` if the top is a `for` or already has an `else`), `end` pops (`unexpected_tag` on an empty stack), and a non-empty stack at the end of the template is `unclosed_block` at its top. A `-` at either end of a tag's inside is a trim marker, applied to the neighbouring text pieces of the flat list before it is nested into a tree: an `if` holds its two branches, a `for` its body. Rendering is a recursive walk with a list of bindings: a lookup whose first segment names a binding, searched from the innermost, starts from the bound node; a `for` looks up its path, then renders its body once per item or per member (sorted keys) with one or two new bindings.
4. Level 4: the merge sets each copied node's layer to the current layer, and a newly created object gets the current layer too, while an object that is merged into keeps its own. `provenance` is the same walk as `merged`, printing layers. `validate` decodes nothing new: it walks the values and the schema together. At each location it checks `type`, `enum`, `minimum` and `maximum` (numbers only), `required` (objects only, with pointers to the missing members), then recurses into each member listed in `properties`, reports the others when `additionalProperties` is `false`, and recurses into each item with `items`. The errors are sorted by pointer and keyword at the end. `render` calls the validator first and stops with `invalid_values` and the count.

### Correctness

Merge: the result after `k` layers is the merge patch of layer `k` applied to the result after `k - 1` layers, by induction on `k`, because `merge_into` follows RFC 7396's recursion case by case for an object patch: `null` removes, an object recurses into the target's object or into a new empty one, and any other value replaces. The deep copy keeps the layers unchanged, so merging again on the next call starts from the same data, and replacing a layer in place changes only that step of the chain.

Order: the depth-first walk writes a node before its descendants, and visits the children of an object in sorted key order and those of a list in index order. That is document order by definition, and every node is written once.

Parsing: the scan reads each character of the template once, and the first problem it meets is the first in text order, because tags are scanned left to right and each is checked fully, its tokens and its place in the block structure, before the scan moves on. An open block can only be reported at the end, after every tag has been checked, which is also the statement's order.

Rendering: a lookup follows the statement's rule, segment by segment, and every way of failing to follow a segment returns "missing". A loop pushes its bindings for its body only, and the list of bindings is searched from the innermost end, so a name means the innermost binding while one exists and the values otherwise. The path of a `for` is looked up before its bindings are pushed.

Validation: each keyword is applied exactly at the locations its schema reaches: the root schema at `""`, a `properties` schema at the member with that key when it exists, an `items` schema at each item. No keyword depends on another, which is what JSON Schema's independence of keywords asks, and a missing member is never visited, so its parent's `required` error is the only one. Provenance follows from the merge: a node's layer is written exactly when a copy or a new object is placed, and nothing else changes it.

### Complexity

- Time: O(R + V log V) per merged, provenance or validate, for R rows in all layers and V merged values; render adds O(T + P) for a template of T characters and P printed characters — merging reads every row of every layer once (a copy is no larger than the rows it came from), the walk sorts the keys of each object, and validation visits each value at most once per schema location; the scan reads each template character once, and rendering does work proportional to what it prints plus one lookup per tag executed, each as long as its path.
- Space: O(R + T + P) — the layers and the merged tree hold at most the rows given, the parse tree is no larger than the template, and the output is what is printed.

### Trade-offs

- Merging on every call costs O(R) per question. A renderer that answers many questions between changes can cache the merged tree and drop the cache on `setLayer`; the tests make few calls, and the fresh merge keeps replacing a layer and provenance trivially right.
- A hand-written scanner is longer than a regular expression such as `\{\{(.*?)\}\}`, but positions, string escapes and the "first `}}`" rule are explicit in it, and every error knows its offset. A regular expression is a fine first version of the lexical part; the grammar still needs a stack.
- Building a tree from the parse is one more pass than interpreting a flat list with jumps, which also works (an `if` jumps to its `else` or `end`, an `end` jumps back to its `for`). The tree makes scoping a function argument instead of a separately managed stack of loop frames.
- Validation by recursion is the definition of JSON Schema evaluation. Real validators compile a schema once and evaluate it many times, and they report annotations as well as errors; with one call per change, compiling does not pay here.

### Pitfalls and edge cases

- Lists replace whole. Merging lists item by item is the most common mistake, and it leaves stale items behind (`h2`).
- A `null` inside a new object is dropped, while a `null` inside a list is kept, because lists are copied as they are (`h2`). An empty object over a scalar makes an empty object, and over an object changes nothing (`h1`).
- Sort keys by character code and list items by index. Sorting the pointers as texts puts `/arr/10` before `/arr/2`, and sorting without regard to case puts `_x` first (`h3`).
- Replacing a layer keeps its place, so a later layer still wins over it (`h4`).
- `default` replaces only a missing value or a `null`, never `false`, `0` or `""` (`h6`). A path that goes on past a scalar is missing, not a scalar.
- Values are inserted as they are: not escaped, not trimmed, not rendered again (`h7`, `h12`).
- Parse before rendering: a malformed tag after a missing value is the error to report, and a malformed tag in a branch that is not taken still counts (`h8`, `h11`). Columns count from 1.
- Truthiness has traps both ways: the strings `"0"` and `"false"` are true, the number `0` and an empty list are false (`h10`).
- An `else` belongs to an `if`, never to a `for`, and an unclosed block is reported at the innermost one (`h11`).
- Trim only the template text next to the marker, before rendering; a `{{-` after a value must not eat the value's trailing spaces (`h12`).
- A loop variable hides a value of the same name completely, even where the variable lacks the rest of the path, and disappears at `end` (`h13`).
- `minimum` and `maximum` include their bound and ignore everything but numbers; `required` and `properties` ignore everything but objects; `enum` compares the kind as well as the text (`h14`).
- Errors sort by pointer as text, then keyword; every keyword reports independently; a missing object does not report its own required members (`h15`).
- An object keeps the layer that created it; a scalar written again with the same text moves to the later layer (`h16`).
- Validation comes before parsing in `render`, and a new schema replaces the old one (`h17`).

### Language notes

- Python and TypeScript keep insertion order in `dict` and `Map`, which is the order of the layers; Java uses a `LinkedHashMap`, Kotlin a `LinkedHashMap` (its `mutableMapOf` is one), Go and Rust keep a list of names next to a map from name to tree. Members of a node need no order, since the walk sorts their keys, so Go uses a plain `map` and Rust a `HashMap`.
- Sorting texts: Python compares strings by code point, TypeScript's `<` and Java's and Kotlin's `compareTo` by UTF-16 unit, and Go and Rust by byte. They agree on ASCII, which is all the keys and pointers hold.
- Numbers stay as text from input to output. Only `minimum` and `maximum` need their value: at most `10^15`, it fits a `long`, an `int64`, an `i64`, and a TypeScript `number`, which holds whole numbers exactly up to `2^53 - 1`.
- The renderer signals errors with an exception (Python, TypeScript, Java, Kotlin) or with a returned error value (Go's second result, Rust's `Result`), caught or matched once in `render`.
- Rust keeps the bindings as a `Vec<(String, &Node)>` borrowed from the merged tree, and builds a separate node for each index or key it binds; the other languages hold references to nodes.

## Further reading

- [RFC 7396, JSON Merge Patch, P. Hoffman and J. Snell, October 2014](https://www.rfc-editor.org/rfc/rfc7396): the merge algorithm (section 2), its limits for arrays and `null`, and the example cases of Appendix A. It obsoletes RFC 7386, which has the same pseudocode.
- [RFC 6901, JSON Pointer, P. Bryan, K. Zyp and M. Nottingham, April 2013](https://www.rfc-editor.org/rfc/rfc6901): the syntax of pointers, the `~0` and `~1` escapes, and array indexes without leading zeros.
- [RFC 8259, The JSON Data Interchange Format, T. Bray, December 2017](https://www.rfc-editor.org/rfc/rfc8259): the four primitive and two structured types, objects as unordered collections, and the note that parsers differ on whether member order is visible.
- [JSON Schema Core, draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-core) and [JSON Schema Validation, draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-validation): `properties`, `additionalProperties`, `items` and the `instanceLocation` of the output format in the first; `type` (with `integer`), `enum`, `minimum`, `maximum` and `required` in the second.
- [YAML 1.2.2, 2021](https://yaml.org/spec/1.2.2/): layers of values are often written in YAML, and the 1.2 revision set out to make YAML a strict superset of JSON.
- T. Xu and Y. Zhou, "Systems Approaches to Tackling Configuration Errors", ACM Computing Surveys 47(4), 2015, [doi:10.1145/2791577](https://doi.org/10.1145/2791577): a survey of configuration errors, which its abstract calls one of the dominant causes of system failures, and of ways to prevent, detect and troubleshoot them.
- Z. Yin, X. Ma, J. Zheng, Y. Zhou, L. N. Bairavasundaram and S. Pasupathy, "An empirical study on configuration errors in commercial and open source systems", Proceedings of the 23rd ACM Symposium on Operating Systems Principles (SOSP), 2011, [doi:10.1145/2043556.2043572](https://doi.org/10.1145/2043556.2043572).
