# Stream Windows

## Statement

Build `StreamWindows`, a small engine that counts and adds up **events** in **windows** of time. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is an event?** An *event* is a record that something happened: a page was viewed, a sensor took a reading, a payment went through. Here every event has three numbers: a **key** (who or what it is about, such as a user id or a sensor id), a **time** (when it happened) and a **value** (what it measured, such as an amount or a reading). Events that keep arriving, one after another with no planned end, form a *stream*.

**What is a window?** A question about a stream almost always has a time range in it: "how many views did each page get per minute?", "what did each sensor read in total per hour?". A *window* is such a range of time, and *aggregating* a window means combining the events of one key that fall in it into a few numbers. Here the numbers are the **count** of the events and the **sum** of their values. A window is written `[start, end)`: it holds the times `t` with `start <= t < end`. The square bracket includes `start`, and the round one leaves `end` out, so a window `[0, 10)` and the next one `[10, 20)` share no moment.

**Two clocks.** Each event carries the time at which it *happened*. That is its *event time*, and it is the only time this problem reads: the class never looks at a clock. Events can reach you late and out of order, so the order of the calls is a second clock, the order in which you *see* the events. Levels 1 and 2 group a set of events that has already arrived. Levels 3 and 4 treat the calls as a live stream, where you must decide when a window is complete enough to report.

Aim to finish in 90 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 25, level 2 by 45, level 3 by 65 and level 4 by 85, keeping the last minutes for a final run.

## Input

- `StreamWindows()`: creates an engine with no events.
- A **key** is an integer from `0` to `10^6`, a **time** an integer from `0` to `10^8`, and a **value** an integer from `-10^4` to `10^4`. Two events may share a key, a time, or both.
- Each level's section describes the methods it adds and their parameters.

## Output

A window's result is a row of five integers, `[key, start, end, count, sum]`: the key, the window `[start, end)`, the number of events of that key in the window, and the sum of their values. A window that holds no event of a key has no row for that key. Each method says in which order its rows come.

## Level 1: Tumbling windows

- `add(key, time, value)`: records an event. Events can be added in any order of time.
- `tumbling(size)`: the results of the **tumbling windows** of length `size` over every event added so far. Tumbling windows lie end to end with no gap and no overlap: `[0, size)`, `[size, 2 * size)`, `[2 * size, 3 * size)`, and so on. An event at time `t` is in exactly one of them, the one whose start is the largest multiple of `size` that is not greater than `t`. The rows are sorted by `start`, and rows with the same start by `key`.

Each call of `tumbling` describes all the events so far, so calling it again after more `add` calls, or with another `size`, gives a new answer. Tumbling windows are also called *fixed* windows.

### Example 1

<!-- case: ex1 -->

With `size` 10, key 1 has the events at times 3 and 9 in `[0, 10)`, with values 5 and 4, so its row is `[1, 0, 10, 2, 9]`. The event of key 2 at time 10 is not in `[0, 10)`: the window leaves its end out, so time 10 starts `[10, 20)`. The rows come sorted by start, then key. With `size` 5 the same events fall into five windows.

### Example 2

<!-- case: ex2 -->

Before any event the answer is empty. The events arrive out of order (20, 0, 19, 10), and each lands in its window all the same. A value can be negative.

## Level 2: Hopping and session windows

Tumbling windows cut time into separate pieces. Two other shapes are common.

- `hopping(size, slide)`: the results of the **hopping windows** of length `size` that start every `slide` time units: one window starts at every multiple of `slide`, `[k * slide, k * slide + size)` for every integer `k`, *negative ones included*. When `slide` is smaller than `size` the windows overlap and an event is in several of them; when `slide` equals `size` they are the tumbling windows; when `slide` is larger than `size` there are gaps between them, and an event in a gap is in no window. A window is listed for a key only when it holds at least one of that key's events, so a window that starts before 0 appears whenever it reaches an event at a small time. Rows are sorted by `start`, then by `key`. Hopping windows are often called *sliding* windows.
- `sessions(gap)`: the results of the **session windows** with inactivity `gap`, for each key separately. A session is a burst of activity: give every event at time `t` its own window `[t, t + gap)`, and merge two windows of the same key into one whenever they *overlap*, until no two windows of a key overlap. The merged window starts at its first event and ends `gap` after its last one. Two windows that only touch, where one ends exactly where the next starts, do not overlap and stay apart. Events of the same key at the same time are in the same session. Rows are sorted by `start`, then by `key`.

All three views describe every event added so far, whatever the order in which they arrived.

### Example 1

<!-- case: ex3 -->

With `size` 10 and `slide` 5, a window starts at every multiple of 5. The event at time 3 is in `[-5, 5)` and `[0, 10)`; the one at time 8 in `[0, 10)` and `[5, 15)`; the one of key 2 at time 12 in `[5, 15)` and `[10, 20)`. The window `[0, 10)` of key 1 holds two events. The tumbling windows of length 10 are the hopping windows that start at multiples of 10.

### Example 2

<!-- case: ex4 -->

With `gap` 5, key 1's events at 1 and 3 have the windows `[1, 6)` and `[3, 8)`, which overlap and merge into `[1, 8)`. The event at 10 starts a new session, and 14 joins it: `[10, 19)`. The event at 19 has the window `[19, 24)`, which only touches `[10, 19)`, so it is a session of its own. Key 2 has one event, so one session.

## Level 3: Watermarks

So far the answers describe events that have all arrived. A stream never ends, so a live system must report each window at some point, without knowing whether more events for it are still on the way. It decides with a **watermark**: a time `W` behind which it treats event time as complete, so that a window whose end is at or behind `W` can be reported.

- `configure(size, lateness)`: from this call on, every `add` also feeds a **stream** of tumbling windows of length `size`. `lateness` is the watermark's **out-of-orderness bound**: how many time units the watermark trails the newest event. Cases that use the methods of this level call `configure` once, right after the constructor.
- The watermark starts at `0`. After each event at time `t` is placed in its window, the watermark becomes `max(W, t - lateness)`: the latest event time seen so far, minus the bound, and never lower than before. So an event whose time is at most `lateness` behind the largest event time seen so far is guaranteed to be on time; an event further behind can still be on time, as long as its window is open.
- A window of the stream is **open** until the watermark reaches its end. When an event moves the watermark so that `W >= end` for some open windows, those windows are **emitted**: their rows go to the output, sorted by `start` and then `key`, and they are open no more.
- An event whose time is behind the watermark, `t < W`, still joins its window while that window is open: the watermark promises only that windows ending at or behind it are complete.
- `watermark()`: the current watermark.
- `pending()`: the rows of the open windows, with their counts and sums so far, sorted by `start`, then `key`.
- `poll()`: the rows emitted since the previous `poll` (or since `configure`), in the order they were emitted. A row is handed over by one `poll` only.

At this level no event arrives for a window that has already been emitted. The batch views of levels 1 and 2 keep working and still describe every event.

### Example 1

<!-- case: ex5 -->

With a bound of 0 the watermark is the latest event time: after the event at 9 it is 9, and both windows `[0, 10)` are still open. The event at 11 moves it to 11, which reaches the end 10, so both are emitted, key 1 first. The window `[10, 20)` stays open.

### Example 2

<!-- case: ex6 -->

With a bound of 5, the event at 12 moves the watermark to 7. The events at 8 and 6 arrive after it, and both still join `[0, 10)`, even the one at 6, which is behind the watermark: their window has not been emitted. The event at 15 moves the watermark to 10 and emits the two windows `[0, 10)`.

## Level 4: Late events

A watermark is a guess. Events can arrive further behind than any bound allows: a phone that was offline uploads its readings, a network delays a batch. The two clocks of the statement are now far apart: an event's *event time* is when it happened, but the system sees it at its *processing time*, which here is the moment of its `add` call. An event is **late** when its window's end is at or behind the watermark at the moment it arrives: its window has already been reported, or would have been. The engine has two ways to treat it.

- `allowUpdates(grace)`: after its end, a window stays **correctable** until the watermark reaches `end + grace`. Cases that use it call it once, right after `configure`. Without it, `grace` is `0`, and no window is ever correctable. Some engines call this extra time *allowed lateness*; it is not the `lateness` of `configure`, which only delays the watermark.
- A late event whose window is correctable, `W < end + grace`, joins the window, and the window is emitted again at once:
  - if the window was emitted before, the output gets two rows, first a **retraction** of the result emitted last, which is that row with its count and sum negated, `[key, start, end, -count, -sum]`, and then the new result. Adding up every row emitted for a window gives its current result, and that is why a retraction comes first.
  - if the window was never emitted (no event of that key fell in it before), the output gets just its first result.
- A late event whose window is no longer correctable, `W >= end + grace`, is **dropped**: it changes no window and goes to the **side output** as a row `[key, time, value]`.
- A late event never moves the watermark, since its time is behind it.
- `dropped()`: the side output, every dropped event so far in the order of arrival.
- `stats()`: `[emitted, updated, dropped]`: the number of first results of windows, of corrections (a retraction and its new result count as one), and of dropped events.

The views of levels 1 and 2 still see every event, dropped ones included: they describe the complete data, which the stream can only approximate.

### Example 1

<!-- case: ex7 -->

There is no grace. The event at 12 moves the watermark to 12 and emits `[0, 10)` of key 1. The event at 8 is late, and its window cannot be corrected, so it is dropped. So is the event of key 2 at time 3: its window was never emitted, but its end, 10, is behind the watermark. The batch view still counts both.

### Example 2

<!-- case: ex8 -->

With a grace of 10, `[0, 10)` stays correctable until the watermark reaches 20. The late event at 7 retracts the result `[1, 0, 10, 1, 2]` and replaces it with `[1, 0, 10, 2, 5]`. The late event of key 2 gives its window a first result. The event at 21 emits `[10, 20)` and ends the grace of `[0, 10)`, so the event at 6 that follows is dropped. Three windows got a first result, one was corrected, and one event was dropped.

## Constraints

- At most 2 * 10^4 calls per test.
- `1 <= size, gap, slide <= 10^8`, and `size <= 100 * slide` in `hopping`.
- `0 <= lateness, grace <= 10^8`.
- Every count and sum fits in a 32-bit signed integer.

## Follow-ups

- `hopping` places each event in up to `size / slide` windows. How could you keep one total per slide-long piece of time instead, and add up the pieces of each window when it is asked for?
- A session window can grow and merge with its neighbour when a late event fills the gap between them. What would a stream of session windows need to emit when two sessions that were reported apart become one?
- Here the watermark trails the newest event by a fixed amount. What if each key, or each source of events, had a watermark of its own, and the stream's watermark were the smallest of them? What would one silent source do to it?
- A retraction lets a reader that adds rows up stay correct. Which readers can live without retractions, and simply keep the latest row per window?

## Hints

### Hint 1

For level 1, think about one event first. If windows are 10 long and the event happened at time 23, which window holds it? The windows start at 0, 10, 20, 30 and so on, so it is the one that starts at 20. How can you get 20 from 23 and 10 with integer arithmetic?

### Hint 2

Keep a dictionary whose key is the pair (window start, event key) and whose value is a running count and sum. Go through the events once, add each one to its entry, and sort the entries at the end. Sorting the pairs puts the start first and the key second, which is the order the rows need.

### Hint 3

For hopping windows, find the latest window start that is not after the event: the largest multiple of `slide` at or below its time. That window holds the event if its end is after the event's time, and so do the windows that start one, two, three slides earlier, as long as their ends are still after the event. Stop at the first one whose end is not.

### Hint 4

For sessions, the order of the events by time matters, and the order of arrival does not. Sort the events of one key by time, and walk through them while keeping the session you are building: the next event either falls before its end, and extends it, or does not, and starts a new one.

### Hint 5

For the stream, keep a map from (start, key) to the running count and sum of each open window. After placing an event, compute the new watermark. If it moved, every open window whose end is now at or behind it is emitted: take those out of the map, sort them, and put their rows in an output list that `poll` hands over and empties.

### Hint 6

A late event is easy to recognize: compute its window's end and compare it with the watermark before anything else. Keep a second map for the windows that were emitted and can still be corrected, with the result emitted last for each, and remove a window from it once the watermark reaches its end plus the grace. A late event whose window is in this map is a correction; one whose window is not there but would still be correctable is a first result; any other late event is dropped.
