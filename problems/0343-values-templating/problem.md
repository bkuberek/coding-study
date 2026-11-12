# Layered Values and Templates

## Statement

Build `ValuesRenderer`, which merges layers of configuration values and fills a template with the result, the way deployment tools produce the text that describes a service. The API grows over four levels: every level adds methods or rules to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What are configuration values?** A service that runs in several places (a laptop, a test environment, production) needs settings that differ between them: how many copies to run, which version of its image, which port to listen on. Rather than changing the code for each place, those settings are kept as data, the *values*: a tree of named settings such as `{"replicas": 3, "image": {"tag": "1.4"}}`.

**Why layers?** Most settings are the same everywhere and only a few change. So the values come in *layers*: a `defaults` layer with every setting, a `production` layer with the few that production changes, perhaps an `overrides` layer for one urgent fix. Merging the layers in order gives the final values, and a later layer wins wherever two layers set the same thing. The exact rules matter more than they seem: does a list from a later layer add to the earlier list or replace it? How does a layer remove a setting that a lower layer added?

**Why templates?** What finally gets deployed is text: a *manifest*, a description of the service with its image, its ports and its labels. Writing one manifest per environment by hand repeats almost everything. A *template* is the manifest written once, with holes such as `{{ image.tag }}` that are filled from the merged values.

**Why a schema?** A typo in a layer (`replcias: 3`) or a value of the wrong kind (`replicas: "three"`) should be caught before anything is deployed, with a message that says where the problem is and which layer caused it. A *schema* describes what valid values look like, and checking the values against it is *validation*.

Aim to finish in 150 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 35, level 2 by 75, level 3 by 110 and level 4 by 140, keeping the last minutes for a final run.

## Input

- `ValuesRenderer()`: creates a renderer with no layers.
- A JSON document, such as a layer of values, arrives as a list of **rows**, one for each value in the document except the outermost object. A row is `[pointer, kind, text]`:
  - `pointer` says where the value sits. `/image` is the member `image` of the outermost object, `/image/tag` the member `tag` inside that, and `/ports/0` the first item of the list `ports`. This is a *JSON Pointer* (RFC 6901): a sequence of segments, each after a `/`, that names an object member by its key or a list item by its index counted from 0. The empty pointer `""` means the whole document.
  - `kind` is the kind of JSON value (RFC 8259): `object`, `array` (JSON's word for a list), `string`, `number`, `boolean` or `null`.
  - `text` is the value itself: the characters of a string, a number in decimal (`-5`, `0`, `443`), `true` or `false` for a boolean, and `""` for an object, an array or a null. The content of an object or an array is in the rows that follow it.
  - The outermost value is always an object and has no row of its own. A row comes after the row of its parent, the items of a list come in index order, and the members of an object come in any order.

  For example, `{"image": {"tag": "1.4"}, "ports": [80, 443], "debug": false}` arrives as `[["/image", "object", ""], ["/image/tag", "string", "1.4"], ["/ports", "array", ""], ["/ports/0", "number", "80"], ["/ports/1", "number", "443"], ["/debug", "boolean", "false"]]`.
- A **key** is made of letters, digits and `_`, and does not start with a digit. So a key never holds the `/` or `~` characters that RFC 6901 would have to escape (as `~1` and `~0`), and a pointer is just its keys and indexes joined with `/`.
- Each level's section describes the methods it adds and their parameters.

## Output

Each method's section describes what it returns: a `bool`, a list of rows, or a list of strings. Rows listed **in document order** follow the tree: the row of an object or array comes before the rows inside it, the members of an object follow in ascending order of their keys, and the items of a list follow in index order. Texts are compared by the numeric value of their characters, so `B` comes before `_`, `_` before `a`, and `a10` before `a9`.

## Level 1: Merging layers

- `setLayer(name, rows)`: stores a layer of values under `name`. A new name goes after every layer stored so far, and the call returns `true`. A name that is already stored gets the new rows in its old place in the order, and the call returns `false`.
- `merged()`: the result of merging every stored layer, oldest first, as rows in document order. With no layers it is `[]`.

The merge starts from an empty object and applies the members of each layer to it, in the order of the layers. A member with key `k` changes the result like this:

- A `null` member removes `k` from the result, if it is there.
- An object member: when the result already has an object under `k`, the member's own members are applied to that object in the same way, one key at a time. Otherwise the result first gets a new empty object under `k`, replacing anything else that was there, and the members are applied to it.
- Any other member, a string, a number, a boolean or a list, replaces whatever the result had under `k` with a copy of itself. A list is never combined with an earlier list: it replaces it whole, with everything inside it as it was, including any `null` items.

**Compared with JSON Merge Patch.** RFC 7396, which replaced RFC 7386 with the same algorithm, describes how one JSON document patches another: `null` removes a member, objects merge member by member, anything else replaces the target, and so a list can only be replaced as a whole. Applying each layer to the result as a merge patch gives exactly the rules above. Where they differ, the difference is in scope. A merge patch may be any JSON value, and one that is not an object replaces the whole target; a layer is always an object. RFC 7396 puts no order on members; `merged` lists them in document order. And the merge here runs over a chain of layers rather than one patch. Like a merge patch, a layer cannot store `null` as a member of an object, only as a list item: a `null` inside a new object is dropped, as in RFC 7396's own example, where `{"a":{"bb":{"ccc":null}}}` applied to `{}` gives `{"a":{"bb":{}}}`.

### Example 1

<!-- case: ex1 -->

`replicas` is a number in both layers, so production's `3` replaces `1`. `image` is an object in both, so only its `tag` changes and `repo` stays. `ports` is a list, so production's list replaces the default one whole: the result has `443` alone, not `80` and `443`. The rows come in document order: `image` before `name`, and `image`'s members right after its own row.

### Example 2

<!-- case: ex2 -->

The `overrides` layer removes `debug` and the `format` member of `log`, and leaves `level` alone. Setting `defaults` again returns `false` and keeps the layer in first place, so `overrides` still applies after it: `debug` stays removed, and the new `zone` appears.

## Level 2: Rendering a template

- `render(template)`: fills `template` with the merged values. On success it returns `["ok", text]`. On failure it returns `["error", code, position, detail]` and no text. `code` names the problem, `position` is `"line:column"` of the `{{` that opens the tag at fault, both counted from 1 (a newline `\n` starts a new line), and `detail` is described with each code.

Template text is copied as it is, except for **tags**. A tag starts at `{{` and ends at the first `}}` after it. The text between tags may hold anything else, a lone `}}` or a single `{` included. Inside a tag, spaces may surround and separate its parts, and no other whitespace is allowed. A tag is one of:

- `{{ path }}`: the value at `path`. A **path** is one or more segments joined by `.`, each a key or a list index (`0`, or digits that do not start with `0`): `name`, `app.name`, `ports.1`, `containers.0.image`.
- `{{ path | default "text" }}`: the value at `path`, or `text` when the value is missing. `default` is the only filter.
- `{{ "text" }}`: the text itself. This is how a template writes `{{` into its output: `{{ "{{" }}`.

**String literals.** A string literal is written between double quotes. Inside it, `\"` stands for a double quote and `\\` for a backslash. Any other backslash, or a literal without its closing quote, makes the tag malformed. A literal cannot hold `}}`, since the tag ends there.

**Looking up a path.** Start at the merged values and follow the segments: a key picks that member of an object, and an index picks that item of a list. The value is **missing** when the path cannot be followed, or when it leads to a `null`. A path cannot be followed when an object lacks the key, when an index is past the end of the list, when a key is used on a list or an index on an object, and when any segment comes after a string, a number or a boolean.

**What is inserted.** A string inserts its characters, a number its decimal text, and a boolean `true` or `false`. A value is inserted exactly as it is: nothing is escaped, quoted or rendered again, so a value that holds `{{` stays as written. A `default` replaces only a missing value: `false`, `0` and `""` are values, and they are inserted.

**Errors.** The whole template is checked first, left to right, and rendering starts only when no tag is malformed. The first problem found is the one reported.

| `code` | When | `detail` |
|--------|------|----------|
| `unclosed_tag` | A `{{` has no `}}` after it | `""` |
| `bad_expression` | A tag is none of the forms above: an empty tag, a malformed path, a filter other than `default`, a bad string literal, or parts in the wrong order | `""` |
| `missing_value` | A path without `default` is missing | the path as written |
| `not_scalar` | A path leads to an object or a list | the path as written |

The first two are found by the check. The last two are found while rendering, in the order the output is produced, so a malformed tag anywhere in the template wins over a missing value before it.

### Example 1

<!-- case: ex3 -->

Spaces inside the tags are optional: `{{app.replicas}}` works like `{{ app.replicas }}`. `ports.1` is the second item of the list, and `false` prints as `false`. `region` is missing, so its default is used, while `app.name` exists and its default is ignored.

### Example 2

<!-- case: ex4 -->

`app.owner` is missing and has no default; its tag opens at line 2, column 4. `image` is an object, which has no text of its own. A `{{` without a `}}` is reported at its own position. The last template writes `{{` with a string literal, and the final `}}` is plain text because no tag is open.

## Level 3: Conditions, loops and whitespace

A tag whose first word is `if`, `else`, `end` or `for` is a **block tag**, and must be one of these forms; any other tag that starts with one of these words is a `bad_expression`.

- `{{ if path }}...{{ end }}` and `{{ if path }}...{{ else }}...{{ end }}`: renders the part before `else` when the value at `path` is true, and the `else` part, or nothing, when it is false. A condition never fails: a missing value is false.
- `{{ for item in path }}...{{ end }}` and `{{ for key, item in path }}...{{ end }}`: renders the body once for each item of a list, in index order, or once for each member of an object, in ascending order of the keys. `item` is the item or the member's value. `key`, when given, is the item's index (a number) or the member's key (a string).

The names of loop variables are made of letters, digits and `_`, do not start with a digit, are none of `if`, `else`, `end`, `for` and `in`, and the two names of one `for` differ. Blocks nest: a block may hold any tags, other blocks included.

**True and false.** These values are false: a missing value (a `null` included), `false`, the empty string `""`, the number `0`, an empty list and an empty object. Every other value is true, including the strings `"0"`, `"false"` and `" "`, the number `-1`, and the list `[0]`.

**Scoping.** A path whose first segment is the name of a loop variable starts from that variable's value instead of the values, and its other segments are followed from there: inside `{{ for c in containers }}`, `c.name` is the `name` of the current container. When loops are nested and several bind the same name, the innermost one wins. A variable exists only between its `for` and the matching `end`; before and after, its name refers to the values again. While it exists, it hides a value of the same name completely: when the current `c` has no `name`, `c.name` is missing, even if the values have a `c` with a `name`. The path of a `for` is looked up before the loop binds its own variables, so `{{ for row in row }}` walks the `row` of an outer loop, or of the values.

**Errors.** A `for` whose path is missing fails with `missing_value`, and one whose path leads to a string, a number or a boolean fails with `not_iterable`; the detail of both is the path as written. A part that is not rendered (the branch not taken, the body of a loop over an empty list) is never looked at while rendering, so a missing value there is no error; a malformed tag there still is, since the check covers the whole template. The check also finds two new problems, reported like the others at the tag's `{{`:

| `code` | When | `detail` |
|--------|------|----------|
| `unexpected_tag` | An `end` with no block open, an `else` whose innermost open block is a `for`, or a second `else` in the same `if` | `""` |
| `unclosed_block` | The template ends while blocks are still open: reported at the innermost of them | `""` |

**Whitespace control.** Templates are easier to read with block tags on lines of their own, but those lines would leave newlines in the output. A `-` right after `{{` removes all spaces and newlines at the end of the template text just before the tag, and a `-` right before `}}` removes all spaces and newlines at the start of the text just after it. Only the template's own text is trimmed, before anything renders: a value is never trimmed, and every round of a loop uses the same trimmed body. A `-` can never be part of a path, so `{{-name-}}` is the tag `name` with both sides trimmed.

### Example 1

<!-- case: ex5 -->

In the first template, `{{-` before `for` removes the newline after `ports:`, and `{{-` before `end` removes the newline at the end of the body, so each round writes a newline, two spaces, a dash and a port. `tls` is true, so the `if` part renders. The two-variable loop walks the object `labels` in key order: `app` before `team`.

### Example 2

<!-- case: ex6 -->

`i` is 0 in the first round, and 0 is false, so the separator comes only before the second name. In the second template the loop variable `name` hides the value `name` inside the loop, and after `end` the name refers to the values again. The second container has no `port`, so its default is used. `name` is a string, which a loop cannot walk.

## Level 4: Schemas and provenance

- `setSchema(rows)`: replaces the schema with this JSON document, given as rows like a layer. No rows is the empty schema `{}`, which accepts any values. Until the first call, the schema is empty.
- `validate()`: checks the merged values against the schema and returns every error as `[pointer, keyword, layer]`.
- `provenance()`: for each row of `merged()`, in the same order, `[pointer, layer]` with the name of the layer that set that value.
- `render(template)` now validates the merged values first. When `validate()` reports any error, `render` returns `["error", "invalid_values", "", count]`, where `count` is the number of errors in decimal, and does not look at the template at all.

**The schema.** A schema is an object whose members are *keywords*, a subset of JSON Schema (draft 2020-12). It applies to one location in the values, the *instance*: the schema given to `setSchema` applies to the whole values, at the pointer `""`, and the keywords `properties` and `items` apply schemas of their own to members and items.

| Keyword | Its value | The instance is valid when |
|---------|-----------|----------------------------|
| `type` | `object`, `array`, `string`, `number`, `integer`, `boolean` or `null` | it has that kind; `number` and `integer` both match every number, since every number here is a whole number |
| `enum` | a list of strings, numbers and booleans | it equals one of them, with the same kind and the same text: `1` is not `"1"`, and `true` is not `"true"` |
| `minimum`, `maximum` | a number | it is not a number, or it is at least `minimum`, or at most `maximum`: both bounds are allowed values |
| `required` | a list of keys | it is not an object, or it has every one of the keys |
| `properties` | an object whose members are schemas | each of its members whose key is listed is valid against that key's schema |
| `additionalProperties` | `true` or `false` | the value is `true`, or the instance is not an object, or the key of each of its members is listed in `properties` (with no `properties`, no key is listed) |
| `items` | a schema | it is not a list, or each of its items is valid against that schema |

Every keyword is checked on its own, at every location that a schema reaches, and every failure is reported: a failed `type` does not stop the other keywords of the same schema. A member that is missing from the values is not checked any further, so the `required` error is the only error about it.

**Errors.** An error is `[pointer, keyword, layer]`. `pointer` is the instance's location; for `required`, it is where the missing member would be, such as `/image/tag`. `keyword` names the keyword that failed. `layer` is the layer that set the value at `pointer` (as `provenance` gives it), and `""` for a missing member and for the whole values, which no layer sets. The errors are sorted by pointer, then by keyword, comparing texts by the numeric value of their characters, so `/ports/10` comes before `/ports/2`. JSON Schema's own output format also gives each error's instance location as a JSON Pointer.

**Provenance.** A string, number, boolean or list belongs to the last layer that wrote it, even when that layer wrote the same text again, and everything inside a list belongs to the list's layer. An object belongs to the layer that created it: the layer whose merge made it an object where there was none before, because the key was absent or held another kind of value. A later layer that only merges members into an existing object does not take the object over.

### Example 1

<!-- case: ex7 -->

`image` was created by `defaults`, while its `tag` and the misspelled `replcias` were written by `production`. The schema finds three problems: `region` is required and missing, `replcias` is not in `properties` while `additionalProperties` is `false`, and `replicas` is 0, below its minimum of 1. They are sorted by pointer (`/reg` before `/rep`, then `c` before `i`), and `render` refuses to run. The `fix` layer removes the typo, sets `replicas` and adds `region`, and then the values pass and the template renders.

### Example 2

<!-- case: ex8 -->

`labels` was created by `defaults` and keeps that layer, although `production` added `team` to it. The list `ports` was replaced whole by `production`, so it and both its items belong to `production`. After the `canary` layer, the second port is a string and the third is above the maximum, and the errors name the layer that set each value.

## Constraints

- At most 2000 calls in a test, at most 20 layers, and at most 500 rows in one layer or schema.
- Layer names are 1 to 30 characters: letters, digits, `-` and `_`.
- Keys are 1 to 30 characters. Strings hold printable ASCII characters (codes 32 to 126), at most 100 of them. Numbers are whole numbers written in decimal without leading zeros, at most `10^15` in absolute value. Values nest at most 20 levels deep.
- A template has at most 5000 characters: printable ASCII and newlines.
- A schema uses only the keywords of level 4, each with a value of the kind its table row gives, and each `required` list names a key at most once.

## Follow-ups

- Merging lists whole is simple and predictable, but sometimes a later layer should change one item of a list of containers, found by its `name`. How would you merge lists by a key field, and what would a `null` item mean then?
- Values are inserted without escaping. What goes wrong when a value with a quote or a newline is inserted into a quoted string of the manifest, and how would filters such as `| quote` or `| json` help?
- How would you add `pattern`, `$ref` and `oneOf` to the validator, and what changes when a keyword can apply several schemas to one location?
- Provenance names one layer per value. How would you show the whole history of a value: every layer that set it, and which one removed it?
- A template could include another named template. How would you detect a template that includes itself?

## Hints

### Hint 1

Start with the data, not the template. Turn a list of rows into a tree that your language can walk: a dictionary (or map) for an object, a list for an array, and a small record with the kind and the text for everything else. Split a pointer on `/` to get its segments: all of them but the last lead to the parent, which already exists because parents come first, and the last one is the key or index of the new value.

### Hint 2

The merge is one function that takes the result object and one layer object, and looks at each member of the layer. There are three cases, and only one of them calls the function again: an object member over an object in the result. For any other value, put a copy into the result, so that a later change cannot reach back into a layer.

### Hint 3

For `merged`, walk the merged tree depth first: write the row of a value, then the rows inside it, visiting the keys of an object in sorted order and the items of a list by index. Do not sort the pointers as texts at the end: `/ports/10` would come before `/ports/2`.

### Hint 4

For a template, first find the tags: search for `{{` from where the previous tag ended, then for the first `}}` after it. Cut each tag's inside into tokens: words (letters, digits, `_` and `.`), string literals, `|` and `,`. The token list tells you which form the tag has. Keep the offset of each `{{` and turn it into a line and a column only when you report an error.

### Hint 5

Check the whole template before rendering anything. While you scan, keep a stack of open blocks: an `if` or `for` pushes, an `else` marks the top `if`, and an `end` pops. From the scan, build a tree in which an `if` holds two lists (the part before `else` and the part after) and a `for` holds its body. Trimming is easiest on the flat list of texts and tags, before you build the tree: a tag with a left `-` trims the text before it, one with a right `-` the text after it.

### Hint 6

Render the tree with a recursive function that carries a list of loop bindings, innermost last. To look up a path, check whether its first segment names a binding, searching from the end of the list, and otherwise start at the values. A `for` adds its bindings for the body only, which a fresh list per round, or a push before and a pop after, gives you for free.

### Hint 7

Keep the name of the layer on each node of the merged tree: the merge sets it when it copies a value or creates an object, and leaves an existing object's layer alone. Validation is then a recursive function of an instance node, a schema node and a pointer that appends errors to one list. Apply each keyword independently, recurse through `properties` and `items`, and sort the list once at the end.
