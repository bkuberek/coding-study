# Search Box with Keyboard Navigation: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| event-state | optimal | O(1) per key event; O(r) per list shown or read; O(c) per search | O(c + r + s) | default answer; it survives all four levels without a rewrite |

Here `c` is the total length of the names, `r` the number of results in a list, and `s` the total length of the selections.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Show a list and move a highlight through it | `shown` (the list) and `highlight` (a position, or none); one helper, `show(items)`, sets both |
| 2 | Search the names | `names`, kept with their lowercase forms; `search` computes the matches and calls `show` |
| 3 | Typed text and responses that arrive in any order | `text`, `requestsSent` and `awaitedRequest`, the one request whose response may still be shown |
| 4 | `Enter` selects | `selected`, the reported selections; a selection sets `text` and forgets `awaitedRequest` |

The early choice that makes the later levels cheap is the single `show` helper. Every way a list arrives (`resultsArrived`, `search`, the awaited response) goes through it, and so does every way the list empties (a cleared input, a selection), so the rule "new results put the highlight on the first, an empty list highlights nothing" is written once and no later level can break it.

## Approach: event-state (One state updated by every event)

### Intuition

A search box is a state machine: a handful of fields, and events that change them. The bugs in real components come from state that two places update differently, or from an event that acts on state that is no longer current. So keep the state small, give each event one short rule, and make the two invariants explicit: the list is empty exactly when nothing is highlighted, and at most one request is awaited at a time.

### Algorithm

1. Keep `shown`, `highlight` (`-1` for none), `text`, `requestsSent`, `awaitedRequest` (none at first) and `selected`, plus `names` and their lowercase forms.
2. `show(items)` copies `items` into `shown` and sets `highlight` to 0, or to `-1` when `items` is empty.
3. Level 1: `resultsArrived` calls `show`. `keydown` of `ArrowDown` moves to `(highlight + 1) mod n`, and of `ArrowUp` to `(highlight - 1) mod n`, where `mod` never returns a negative number, and only when `n > 0`. Every other key, and every `keyup`, changes nothing. The getters read `shown` and `highlight`.
4. Level 2: `search` trims and lowercases the query. An empty query shows an empty list. Otherwise it shows, in the order of `names`, each name whose lowercase form contains the query as a plain substring.
5. Level 3: `inputChanged` stores `text`. A blank text forgets `awaitedRequest`, shows an empty list and returns `-1`. Any other text increments `requestsSent`, awaits that id and returns it. `responseArrived` calls `show` only when `requestId` equals `awaitedRequest`.
6. Level 4: `keydown` of `Enter` with a highlight appends the highlighted result to `selected`, stores it as `text`, forgets `awaitedRequest` and shows an empty list. With nothing highlighted it does nothing.

### Correctness

Invariant 1: `highlight` is `-1` exactly when `shown` is empty, and otherwise lies in `0 .. n - 1`. Only `show` changes `shown`, and it sets `highlight` to match; the arrow keys change `highlight` only when `n > 0`, and a non-negative remainder modulo `n` stays in range. So `highlightedText` always reads a real result, and the arrow keys can never divide by zero.

Invariant 2: `awaitedRequest` is the id of the latest request, and only while the input has not changed without a request since then. `inputChanged` sets it on every request and forgets it on every clear, and a selection forgets it too; nothing else touches it. A response is shown exactly when its id equals `awaitedRequest`, which is the statement's rule. Comparing for equality, not "newer than the last shown", is what makes an old response stale even when the latest one has not arrived yet.

### Complexity

- Time: O(1) per key event; O(r) per list shown or read; O(c) per search — a key compares strings of at most 20 characters and moves an index; `show` and the getters copy a list of `r` results, so that no caller can change the box's list; `search` runs one substring test per name, which is linear in the name's length for a query of at most 50 characters.
- Space: O(c + r + s) — the names and their lowercase forms, the list shown, and every selection.

### Trade-offs

- Storing the matches' positions in `names` instead of copies of the strings would save memory for long lists, but every getter would then translate positions back. With at most 100 results it only adds code.
- Lowercasing the names once in the constructor makes each search one pass of `contains`. Lowercasing inside the loop is just as correct and costs a little more per search; a case-insensitive `contains` from the library (Kotlin's `ignoreCase = true`) is fine too, as long as it is not a regular expression.
- A real component would also cancel the stale request (an `AbortController`) to save the server's work and the network. That does not remove the id check: a response can already be on its way when the request is aborted, and a server or a cache may answer anyway.
- A reducer, `(state, event) -> state`, is the same design with immutable state, which is how React's `useReducer` would hold it. A class with private fields is shorter here and behaves the same.

### Pitfalls and edge cases

- Level 1, listening to `keyup` for "up". `keyup` is the key coming back up, not the up arrow, and a handler that moves on `keyup`, or on both events, moves twice per press or moves when the user lets go of `ArrowDown`. Hidden case `h2` releases `ArrowUp` and `ArrowDown` on the first result, and holds `ArrowDown` for three repeats before one `keyup`.
- Level 1, `-1 % n`. In TypeScript, Java, Kotlin, Go and Rust, `%` keeps the sign of the dividend, so `(0 - 1) % 4` is `-1`, `highlighted` returns `-1`, and `shown[-1]` is `undefined` in TypeScript and a crash in the others. Python's `%` already returns `3`. Hidden case `h1` presses `ArrowUp` on the first of four results.
- Level 1, the wrap itself. Wrapping when the index passes `n` instead of `n - 1` highlights a position past the end; `h5` wraps a single result onto itself and two results at both ends. `n == 0` must be checked before `% n`, which is `NaN` in TypeScript and a crash in the other languages; `h4` presses both arrows on an empty list.
- Level 1, other keys. `if (key === "ArrowUp") up(); else down();` moves on every key, and `key.includes("Down")` moves on `PageDown`. `h3` presses `ArrowRight`, `PageDown`, the legacy `Down`, `Tab`, letters and a lowercase `arrowdown`.
- Level 2, regular expressions. `new RegExp(query, "i")` or `re.search(query, name, re.I)` throws on `c++`, `*` and `?`, matches `ejs` with `.js`, and matches every name with `a*`, since the empty match counts. `h6` searches all of them. Use `includes` or `contains` on lowercased text.
- Level 2, the empty query. Every string contains the empty string, so `"Bo".includes("")` is `true`, and a blank query that is not handled first shows every name. `h8` searches `"   "` and `""`.
- Level 3, stale state. Keeping the largest id shown so far and accepting anything newer shows request 2 after request 3 was sent; `h10` catches it. Forgetting to drop the awaited request when the input is cleared lets a late response refill a cleared box; `h11` catches it. A component that reads the query in a callback created for an older render has the same bug in another form: a stale closure, as in `debug-stale-closure-callbacks`.
- Level 4, the list that reopens. A selection fills the input without sending a request, so the response to the last typed query is stale. A box that keeps awaiting it reopens the list just after the user chose; `h15` and `h17` catch it.
- Level 4, `Enter` twice. Selecting on `keyup` reports a selection when the user never pressed `Enter` in the box, and not clearing the highlight on selection reports a held `Enter` twice. `h14` covers both, and `Enter` on an empty list.
- Global listeners without cleanup. A component that adds `document.addEventListener("keydown", ...)` on every render, or never removes it, ends up with several handlers: one press moves the highlight several places, or keeps moving it after the list closed. In this model it looks like a double move, or like a highlight on a closed list, which `h2` and `h15` catch. Return a cleanup function from the effect that adds the listener, or put the handler on the input itself.

### Language notes

- Python: `%` is already non-negative for a positive divisor, so `(i - 1) % n` works; `str.lower`, `str.strip` and the `in` operator do the rest. `re.escape` would make a regular expression safe, but a plain `in` is simpler.
- TypeScript: `(i + step + n) % n` keeps the result non-negative. `toLowerCase`, `trim` and `includes` match the other languages for ASCII. Indexing past the end returns `undefined` instead of throwing, which hides a wrap bug until a getter returns it.
- Java: `Math.floorMod(i + step, n)` is the non-negative remainder. `toLowerCase()` uses the default locale, and in a Turkish locale `"I"` becomes a dotless `"ı"`; pass `Locale.ROOT`. `String.strip`, `isBlank` and `contains` cover the rest.
- Kotlin: `(i + step).mod(n)` is the non-negative remainder, where `%` is not. `lowercase()` is locale-independent, unlike Java's `toLowerCase()`.
- Go: `%` keeps the sign of the dividend, so add `n` first. `strings.ToLower`, `strings.TrimSpace` and `strings.Contains` cover the rest. Return a fresh slice from the getters so that a caller cannot change the box's list through it.
- Rust: `rem_euclid` is the non-negative remainder; an `Option<usize>` for the highlight makes "nothing highlighted" a type the compiler checks, and the `-1` appears only in `highlighted`.
