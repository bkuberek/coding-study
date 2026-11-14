# Stream Windows: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| window-state | optimal | O(1) per event, plus O(w log w) when the watermark moves; O(n h + r log r) per view | O(n) for the log, plus one entry per open or correctable window | default answer; the views group the log on demand, and the stream keeps only the windows it may still change |

Here `n` is the number of events, `h` the number of hopping windows that hold one event (at most `size / slide`, rounded up), `r` the number of rows of a view, and `w` the number of open windows of the stream.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Tumbling windows | an event log; `tumbling` groups it in a map keyed by (start, key) and sorts the map |
| 2 | Hopping and session windows | nothing new: `hopping` puts each event in every window that holds it, `sessions` sorts each key's events by time and merges them in one pass |
| 3 | Watermarks | the stream's `size` and `lateness`, the watermark, a map of open windows, and an output list |
| 4 | Late events | `grace`, a map of the emitted windows that can still be corrected, the side output and two counters |

The choice that keeps the levels apart is to keep the log for the views and a separate state for the stream. The views always see every event, which is what levels 1 and 2 promise and what level 4 relies on when it says that dropped events still count there. The stream never needs the log: once a window is emitted and its grace is over, nothing can change it, so the stream forgets it. A first version that answers the views from the stream's maps would pass level 3 and then lose the dropped events at level 4.

## Approach: window-state (An event log for the views and a map of window totals for the stream)

### Intuition

Every window shape in this problem is a rule that maps one event to the windows that hold it: one window for tumbling, a few for hopping, and for sessions a window that depends on the key's other events. Once each event knows its windows, aggregating is adding to a running count and sum, keyed by the window. The stream adds one question, *when* a window is final, and the watermark answers it: a window is final once the watermark reaches its end, and still changeable for `grace` time after that.

### Algorithm

1. `add` appends the event to the log. After `configure`, it also feeds the stream (step 6).
2. `tumbling(size)`: for each event, the start is `time - time % size` (times are never negative, so this is the floor to a multiple of `size`). Add the event to the entry `(start, key)` of a map, then sort the entries; sorting the pairs orders by start and then key.
3. `hopping(size, slide)`: the latest start that can hold an event is `time - time % slide`. Add the event to that window and to the windows one slide earlier, again and again, while the start is greater than `time - size`. A slide larger than the size makes the first candidate fail already, and the event is in no window. The loop may go below 0, which is how the windows that start before 0 appear.
4. `sessions(gap)`: group the events by key and sort each group by time. Walk through a group keeping the current session `[start, end)`: an event with `time < end` joins it and sets `end = time + gap`; any other event starts a new session `[time, time + gap)`. Sort all the sessions by start, then key.
5. `configure(size, lateness)` stores both values; `allowUpdates(grace)` stores `grace`.
6. For each event of the stream, compute `start` and `end` of its tumbling window. If `end > W`, the window is open: add the event to its entry in `open`. Otherwise the event is late: if `W < end + grace`, correct the window (step 7); if not, append `[key, time, value]` to the side output.
7. To correct a window, look it up in `closed`, the map of emitted windows that are still correctable. If it is there, emit the retraction of the stored result (count and sum negated), add the event to the stored result, and emit the new result; count an update. If it is not there, store `[1, value]`, emit it, and count a first result.
8. Move the watermark to `max(W, time - lateness)`. If it moved, take every window with `end <= W` out of `open`, sort them by start and key, emit them in that order into the output list and into `closed`, and count first results. Then remove from `closed` every window with `end + grace <= W`.
9. `poll` hands over the output list and starts a new one; `pending` sorts `open`; `dropped` copies the side output; `stats` reads the counters and the length of the side output.

### Correctness

Tumbling: the start `time - time % size` is the largest multiple of `size` not greater than `time`, and `time < start + size`, so the event is in exactly that window. Hopping: a window `[s, s + size)` with `s` a multiple of `slide` holds `time` exactly when `time - size < s <= time`; the loop starts at the largest multiple at or below `time` and walks down through every multiple while `s > time - size`, so it visits exactly those windows. Sessions: in a key's events sorted by time, the windows `[t, t + gap)` overlap only when they are near in this order, and the current session's end is `gap` after its latest event, so an event overlaps the session exactly when `time < end`. Merging in one pass therefore gives the same windows as merging overlapping windows until none overlap, and a window that only touches the session (`time == end`) starts a new one.

The stream: the watermark only goes up, and windows are emitted the moment it reaches their end, so at any time `open` holds exactly the windows with an event and an end after `W`. A late event has `end <= W`; since `time < end`, it also has `time - lateness < W`, so it cannot move the watermark, and its handling never interacts with the emissions of the same call. A window in `closed` has `end <= W < end + grace`, and step 8 removes it as soon as `W` reaches `end + grace`, so "in `closed`" means "emitted and still correctable". A late, correctable window that is not in `closed` was never emitted: had it been, its grace would not be over, and it would still be there. Every correction emits the negation of the row emitted last for that window and then the new row, so the rows of a window always add up to its current result.

### Complexity

- Time: O(1) per event, plus O(w log w) when the watermark moves; O(n h + r log r) per view — placing an event is a few map operations. When the watermark moves, one pass over the `w` open windows finds the due ones, and sorting them costs at most O(w log w); the pass over `closed` is bounded the same way by the windows emitted within the grace. A view visits each event once per window that holds it and sorts its `r` rows; `sessions` also sorts each key's events, which is within the same bound.
- Space: O(n) for the log, plus one entry per open or correctable window — the views rebuild their maps on each call, and the stream drops a window once its grace is over.

### Trade-offs

- The views rebuild everything from the log on each call. An engine that answers the same view many times would keep a running map per view instead; this one keeps the log because each call may ask for a different size.
- Scanning all open windows when the watermark moves is simple and fast enough here. A stream with many keys would keep the open windows ordered by end (a heap or a sorted map), so that each move of the watermark touches only the windows it emits.
- `closed` is the price of corrections: every emitted window is kept for `grace` time units of watermark. A larger grace corrects more late events and keeps more state, and a smaller one drops more events. Keeping only the retraction-free latest row would save nothing, since the next correction needs the old totals either way.

### Pitfalls and edge cases

- A window that includes its end: an event at time 10 is in `[10, 20)`, not in `[0, 10)` (`h1`).
- Sorting rows by key first: the rows are ordered by start, then key (`h2`, `h16`, `h18`).
- Hopping windows that start before 0 are real windows: with `size` 10 and `slide` 4, time 0 is in the windows that start at -8, -4 and 0 (`h9`). Counting `size / slide` windows per event with integer division gives two of them, not three.
- A slide larger than the size: an event in a gap is in no window, not in the nearest one (`h8`).
- Sessions merged when they only touch, or measured from the session's first event instead of its last (`ex4`, `h11`), or built in arrival order (`h10`).
- A watermark computed from the latest event instead of the largest time seen, or allowed below 0 (`h14`).
- Emitting a window only when the watermark passes beyond its end: it is emitted when `W >= end` (`h15`).
- Treating every event behind the watermark as late. Lateness belongs to the window: an event at 12 behind a watermark of 15 still joins the open window `[10, 20)` (`h20`, `h25`).
- `poll` that does not empty its list (`h17`), and `pending` that keeps emitted windows (`h18`).
- A correction without a retraction, or a retraction of the first result instead of the last one (`ex8`, `h22`).
- The grace boundary: a window is correctable while `W < end + grace`; at `W == end + grace` the event is dropped (`h21`).
- A late event for a window that was never emitted is a first result, with no retraction, and counts as emitted (`ex8`, `h23`).
- A side output that is emptied by `dropped`, or views that forget the dropped events (`h24`, `ex7`, `h27`).

### Language notes

- Python and TypeScript key the window maps by the pair (start, key): Python with a tuple, TypeScript with a string built from both numbers. Java and Kotlin pack the pair into one `long` (the start shifted left, plus the key), Go uses a struct as the map key, and Rust a tuple `(i32, i32)`.
- Every language sorts the rows it returns. Python sorts tuples and lists directly; the others sort by start and then key with a comparator.
- `poll` swaps the output list for a new one. In Rust that is `std::mem::take`, and in Go a reassignment to `nil`, which still encodes as `[]`.
- All the arithmetic stays within 32 bits: times and sizes are at most 10^8, so an end plus a grace is at most 3 * 10^8.

## Further reading

- T. Akidau, R. Bradshaw, C. Chambers, S. Chernyak, R. J. Fernández-Moctezuma, R. Lax, S. McVeety, D. Mills, F. Perry, E. Schmidt and S. Whittle, "The Dataflow Model: A Practical Approach to Balancing Correctness, Latency, and Cost in Massive-Scale, Unbounded, Out-of-Order Data Processing", Proceedings of the VLDB Endowment 8(12), 2015, pages 1792 to 1803, [doi:10.14778/2824032.2824076](https://doi.org/10.14778/2824032.2824076): event time and processing time, fixed (tumbling), sliding and session windows, sessions built by giving each event a window that extends a timeout gap past it and merging the windows that overlap, watermarks as a lower bound on the event times processed, data that arrives behind the watermark, and the accumulating and retracting mode, in which a window that fires again first emits a retraction of its previous value.
