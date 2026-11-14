# Stream Reassembler

## Statement

A chat product shows a model's answer as it is written, one small fragment of text at a time. The fragments come through a relay that can deliver them out of order, deliver them twice, or drop the connection partway. The screen must show the text in the right order as soon as it can, and the product must never store a cut-off answer as if it were whole.

The stream has three invented kinds of event. Each fragment carries a `sequence`, counted from 0. A `finish` event says which sequence is the last one. And the connection can close at any moment, whether or not the stream was done. Implement `StreamReassembler`:

- `delta(sequence, fragment)`: a fragment has arrived. It returns the text that this call **releases**. Text is released in sequence order, as soon as every earlier fragment has arrived, so the call returns the fragment followed by any held fragments that it unblocks, or `""` when it unblocks nothing. It is ignored, and returns `""`, in each of these cases:
  - that sequence has already arrived, whatever its text: the first text wins,
  - a `finish` has been recorded and `sequence` is above its last sequence,
  - the connection has closed.
- `finish(lastSequence)`: records that `lastSequence` is the stream's last fragment. It returns `true`, or `false` and changes nothing, when the connection has closed, a `finish` was already recorded, or a fragment above `lastSequence` has already arrived. A stream with no fragments at all finishes with `lastSequence` of `-1`.
- `close()`: the connection is gone, and nothing arrives after this.
- `status()`: `"complete"` when a `finish` has been recorded and every fragment through its last sequence has arrived, whether or not the connection has closed. Otherwise `"truncated"` if the connection has closed, and otherwise `"streaming"`.
- `text()`: all the text released so far. On a truncated stream this is what you may show, labelled as cut off: the text up to the first gap, and nothing beyond it.
- `missing()`: in ascending order, the sequences that have not arrived, from 0 up to the last sequence when a `finish` has been recorded, and otherwise up to the highest sequence that has arrived.

A fragment may be the empty string, which is a real fragment: it fills its place like any other.

## Input

- `sequence`: the fragment's place in the stream, counted from 0.
- `fragment`: the text. It is kept exactly as it came, with its spaces and line breaks.
- `lastSequence`: the sequence of the stream's last fragment, or `-1` when there are none.

Each test is a sequence of calls: the constructor first, then the other calls in order.

## Output

One result per call: `null` for the constructor and for `close`, a string for `delta`, `status` and `text`, a boolean for `finish`, and an integer array for `missing`.

## Examples

### Example 1

<!-- case: ex1 -->

Fragment 1 arrives first and has to wait, so its call releases nothing. Fragment 0 then releases itself and fragment 1 together. Fragment 2 goes straight out. After `finish(2)` the stream is complete.

### Example 2

<!-- case: ex2 -->

`finish` arrives before the fragments are all in, which is allowed: fragment 2 still gets held, and the stream stays `"streaming"` with sequence 1 missing. The second copy of fragment 0 is ignored, even though it has different text. Fragment 1 then releases both.

### Example 3

<!-- case: ex3 -->

Nothing is out of order and nothing is known to be missing, but `finish` never came. The connection closed in the middle of the stream, and the answer may simply stop halfway through a sentence. So this is `"truncated"`.

### Example 4

<!-- case: ex4 -->

A gap at sequence 1 holds fragment 2 back, so the text stops at `"a"`. `finish(3)` makes sequence 3 known too, so both are missing when the connection closes.

## Constraints

- `0 <= sequence < 10^4` and `-1 <= lastSequence < 10^4`.
- A fragment is at most 1000 characters long.
- At most `10^4` calls.

## Follow-ups

- Bound the memory: what should happen when the fragments held behind a gap pass a limit?
- A retry can ask the relay to resend from a given sequence. How does `missing()` become that request, and when is it worth it over starting again?
- A stream can carry several blocks at once, such as text and the arguments of a tool call. Add a block id. Which state is per block, and which is per stream?
- When a tool call's arguments are fragments of JSON, when is it safe to parse them?

## Hints

### Hint 1

Keep the released fragments in a list, and the next sequence to release is that list's length.

### Hint 2

Ask whether a fragment **is there**, not whether its text is truthy.

### Hint 3

`status` has an order. Work out what a closed stream with every fragment and a `finish` should say.
