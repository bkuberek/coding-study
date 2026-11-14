# Stream Reassembler: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| release-contiguous | optimal | O(1 + r) per delta, O(g) per missing, O(s) per text | O(s) | default answer |

`r` is the number of fragments a delta releases, `g` the distance from the first gap to the highest known sequence, and `s` the size of the stream so far.

## Approach: release-contiguous (Release the contiguous prefix and hold everything above the first gap)

### Intuition

Think of the sequence numbers as seats. Text can be shown only from the front row back, with no empty seat between, so all the state you need is where the first empty seat is, and what has already sat down behind it. The moment that seat fills, everything behind it up to the next empty seat goes out together.

Then there are two separate questions, and many streaming bugs come from answering only one of them. "What may I show now?" is the contiguous prefix. "Is it whole?" needs positive evidence: a `finish` event and every fragment through it. A connection closing is not that evidence. An answer that stops mid-sentence looks a lot like a short answer, and if you store it as complete nobody will notice until a user does.

### Algorithm

1. Keep a list of released fragments, whose length is the next sequence to release, and a map of held fragments above the gap.
2. `delta`: ignore it if the connection has closed, if it is above a recorded last sequence, or if the sequence has arrived already. Otherwise hold it, then move fragments from the map to the list as long as the next sequence is in the map, and return what moved.
3. `finish`: refuse it if the connection has closed, a `finish` is already recorded, or a higher fragment has already arrived. Otherwise record it.
4. `status`: complete when a `finish` is recorded and the list has reached its last sequence. Otherwise it depends on whether the connection has closed.
5. `missing`: from the length of the list up to the last known sequence, every sequence not in the map.

### Correctness

A fragment reaches the list only when its sequence equals the list's length, so `released[i]` is always fragment `i`, and the list is contiguous from 0 by construction. A sequence below the length or in the map has arrived, so the duplicate check needs nothing more and the first text stays. The loop runs until the next sequence is not in the map, so no fragment is ever held while everything before it has arrived. `status` says `"complete"` exactly when the list holds every fragment through the last sequence. `finish` cannot name a last sequence below one that has arrived, so every fragment in the list or map stays in range, and `missing` lists exactly the absent sequences in range: everything below the list's length has arrived.

### Complexity

- Time: O(1 + r) per delta, O(g) per missing, O(s) per text — a delta does map operations and moves `r` fragments, and `missing` walks from the first gap to the end. `finish`, `close` and `status` are O(1).
- Space: O(s) — the fragments, released or held.

### Trade-offs

Sorting all fragments when the stream ends is shorter, but it shows nothing until then, which is the point of streaming, and it gives you no way to say what is safe to show. A min-heap of held fragments would also work, at O(log n) per fragment, and it needs a separate duplicate check, while a map answers both questions at once.

Accepting a `finish` that comes early costs a little state, and the alternative, treating `finish` as the end of everything, silently drops whatever is still in flight on a channel that reorders.

Holding fragments costs memory the sender controls. A real implementation bounds it, and gives up on a stream whose gap does not close in time, which is what the follow-ups ask about.

### Pitfalls and edge cases

- **Appending in arrival order.** It works in every test until the first reorder (`ex1`, `h1`).
- **Treating a closed connection as the end.** A stream that closes with no `finish` is truncated even with no gap at all (`ex3`, `h7`). This is the bug that stores half an answer as a whole one.
- **Treating `finish` as the end.** Fragments can still arrive after it (`ex2`, `h2`).
- **An empty fragment is falsy.** `while held.get(next):` stops at `""`, so the stream sticks forever and the text behind it never comes out (`h3`). Test for presence.
- **Zero and -1 are real values.** `if last_sequence:` skips a stream of one fragment (`h9`), and a stream with no fragments finishes with `-1` (`h10`).
- **Overwriting a held fragment.** A map write makes the last copy win, but only while the fragment is held, so the behaviour depends on timing (`h4`).
- **Assuming the stream starts where the first fragment does.** If fragment 0 never arrives, nothing may be released (`h5`).
- **Showing text beyond a gap.** The text of a truncated stream stops at the first gap (`ex4`, `h6`).
- **Letting events revive a closed stream.** A delta after `close` is ignored, even one that would fill the gap, and a `finish` after `close` is refused (`h8`).
- **`complete` and closing.** A complete stream stays complete when the connection closes (`h11`).
- **Contradicting a `finish`.** A fragment above the last sequence is ignored, a second `finish` is refused, and a `finish` below an arrived fragment is refused (`h12`, `h13`, `h14`).
- **What `missing` can know.** Without a `finish` it can only see gaps below the highest arrival, and it says nothing about what may come after it (`ex3`, `h15`).
- **Editing the text.** Fragments are kept exactly: stripping one loses the space between two words (`h16`).

### Language notes

- Python: `len(self._released) in self._held` is the presence check, and `dict.pop` moves a fragment in one step. `"".join` builds the result without repeated copying.
- TypeScript: `Map.has` is the presence check. `map.get(key)` returns `undefined` for an absent key, which a truthiness test would confuse with `""` in the same way. Strings are UTF-16 here and fragments are joined whole, so a character split across two fragments would still come out right, as long as the relay hands over text and not bytes.
