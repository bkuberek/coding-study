# Search Box with Keyboard Navigation

## Statement

Build `SearchBox`, the logic behind a search input with a list of results under it: the kind of box that suggests matches while you type and lets you move through them with the arrow keys. The box receives a stream of events, and getters read back its state. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

In a browser, an input fires a `keydown` event when a key goes down and a `keyup` event when it comes back up, and a component reacts in a handler such as React's `onKeyDown`. The event's `key` names the key: `ArrowDown`, `ArrowUp`, `Enter`, `a`, `Shift`. Holding a key down repeats its `keydown`, with one `keyup` at the end. Here there is no browser and no framework: each event is a method call, and the getters return what the component would render.

Every method takes the time of the call as its first argument, `timestamp`. Events arrive in the order of their timestamps, and no rule depends on the value itself.

Aim to finish in 90 minutes. A good split: read the statement in the first 5 minutes, then finish level 1 by about minute 25, level 2 by 40, level 3 by 65 and level 4 by 85, keeping the last minutes for a final run.

## Input

- `SearchBox(names)`: creates a search box over `names`, the list the box can search, in the order given. The box starts with an empty input and an empty list, so nothing is highlighted.
- `timestamp`: the time of the call. Within one test, timestamps never decrease from call to call, and consecutive calls may share a timestamp.
- Each level's section describes the methods it adds and their other parameters.

## Output

Events change the state and return nothing, unless their level says otherwise. Getters return the state. Absence is a sentinel, never an exception: `-1` for a position, `""` for a text and an empty list for a list.

## Level 1: Keyboard navigation

The list shows results, and at most one of them is highlighted.

- `resultsArrived(timestamp, items)`: the list now shows `items`, in that order, in place of what it showed before. The first item is highlighted; when `items` is empty, nothing is.
- `keydown(timestamp, key)`: a key went down. `ArrowDown` moves the highlight to the next result, and from the last result back to the first. `ArrowUp` moves it to the previous result, and from the first result to the last. While the list is empty, they do nothing. No other key moves the highlight.
- `keyup(timestamp, key)`: a key came back up. It never moves the highlight, whatever the key.
- `results(timestamp)`: the results the list shows, in order.
- `highlighted(timestamp)`: the position of the highlighted result in the list, counting from 0, or `-1` when nothing is highlighted.
- `highlightedText(timestamp)`: the highlighted result, or `""` when nothing is highlighted.

### Example 1

<!-- case: ex1 -->

Three results arrive and `apple` is highlighted. `ArrowDown` goes down and comes up, which moves the highlight once, to `banana`. Two more presses reach `cherry` and then wrap around to `apple`.

## Level 2: Matching names

- `search(timestamp, query)`: shows the names that match `query`, as `resultsArrived` would show them: the first match is highlighted, and when nothing matches, the list is empty and nothing is highlighted.
- A name matches when it contains the query, ignoring case. Spaces at both ends of the query are removed first; spaces inside it count.
- Every character of the query stands for itself: `.`, `*`, `+`, `?` and `(` are characters like any other.
- The matches keep the order of `names`, and the list shows all of them.
- A query that is empty once its spaces are removed matches nothing.

### Example 1

<!-- case: ex2 -->

`li` matches four cities, in the order of `names`; `Milan` holds `il` but not `li`. After `ArrowDown`, the search for ` LIN ` drops the spaces, ignores case, and starts again from the first match, `Berlin`. An empty query shows nothing.

## Level 3: Typing and stale responses

Typing in the input sends a search request to a server, and the server's responses can arrive late, in any order, or never.

- `inputChanged(timestamp, text)`: the input now holds `text`, after the user typed or deleted.
  - When `text` is empty or only spaces, the input is cleared: the list becomes empty, nothing is highlighted, no request is sent, and the method returns `-1`.
  - Otherwise the box sends a request and returns its id: 1 for the box's first request, then 2, 3 and so on. A cleared input takes no id. The list keeps what it shows, and the highlight stays, until a response is shown.
- `responseArrived(timestamp, requestId, items)`: the server answered request `requestId` with `items`. The response is shown, as `resultsArrived` would show it, only when its request is the latest one sent and the input has not been cleared since. Any other response is stale and changes nothing.
- `inputText(timestamp)`: the text the input holds, exactly as last set, spaces included; `""` before anything is typed.
- `requestId` is always an id that `inputChanged` returned, and each request gets at most one response.
- `search` and `resultsArrived` keep working as before. They change neither the input's text nor which request is the latest.

### Example 1

<!-- case: ex3 -->

Typing `pa` and then `par` sends requests 1 and 2. The response to request 2 arrives first and is shown. The response to request 1 arrives after it and is stale, so the list keeps the results for `par`.

## Level 4: Selecting with Enter

- `keydown` of `Enter` while a result is highlighted selects that result:
  - the input now holds the selected result, as `inputText` shows;
  - the list closes: it becomes empty, and nothing is highlighted;
  - the selection is reported: it is added to `selections`;
  - the input changed without a new request, so no response sent before the selection is shown.
- `keydown` of `Enter` with nothing highlighted does nothing, and `keyup` of `Enter` never selects.
- `selections(timestamp)`: every result selected so far, oldest first, as an `onSelect` callback would have received them.

### Example 1

<!-- case: ex4 -->

`ArrowDown` highlights `Rotterdam`, and `Enter` selects it: the input holds `Rotterdam`, the list is closed, and the selection is reported once, although `Enter` also came back up.

## Constraints

- At most 1000 calls per test.
- `1 <= timestamp <= 10^9`, never decreasing within a test.
- `names` holds 0 to 1000 names, and a list of `items` 0 to 100 results.
- A name or a result is 1 to 50 printable ASCII characters (space to `~`), and a query or an input text is 0 to 50 of them.
- A `key` is 1 to 20 characters, a key name as a browser reports it, compared exactly: `ArrowDown`, never `arrowdown`.

## Follow-ups

- Rank the matches instead of keeping their order: names that start with the query first, then names where a word starts with it, then the rest, alphabetical within each group, and at most `N` of them.
- Send a request only once the user stops typing for 200 ms. The timestamps are already there.
- Cancel a stale request instead of ignoring its response, as an `AbortController` would. What does that save, and why does the box still need the id check?
- Add `Escape`, which closes the list without selecting, and `Home` and `End`.

## Hints

### Hint 1

Keep the whole state in a few fields: the list, the highlighted position, the input's text and the latest request. Each event is a small change to them.

### Hint 2

Write one helper that shows a list: it replaces the results and puts the highlight on the first, or on nothing when the list is empty. Every way a list arrives calls it, and so does every way the list empties.

### Hint 3

With `n` results, the next position is `(i + 1) % n` and the previous one is `(i - 1 + n) % n`, and both only when `n > 0`. In most languages `-1 % n` is `-1`, not `n - 1`.

### Hint 4

Remember the id of the one request whose response may still be shown, and forget it whenever the input changes without a new request. A response is shown only when its id is that one.
