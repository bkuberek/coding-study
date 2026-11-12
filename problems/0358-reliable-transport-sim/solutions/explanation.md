# Reliable Transport Sim: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| timer-and-windows | optimal | O(k) per receive of k bytes; O(s) per sender call over s segments | O(b + s) for b held bytes and s segments | default answer; each level adds one limit or one reaction to the same sender |

Here `k` is the length of a received segment, `b` the number of bytes the receiver holds early, and `s` the number of segments the sender knows. A sender call scans its segments to find the next one to send and the oldest outstanding one; a production sender keeps pointers instead and does constant work per segment.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Reorder and deduplicate | the next expected byte and a map from position to the bytes held early |
| 2 | ACKs and retransmission | the segments with a "transmitted" flag, `una` and `nxt`, the estimator (`srtt`, `rttvar`, `rto`), the timer deadline and the timed segment |
| 3 | Flow control | the advertised window, unlimited until the first `ackWindow` |
| 4 | Congestion control | `cwnd`, `ssthresh`, the bytes counted in congestion avoidance, the count of duplicate ACKs, the fast recovery flag and the trace |

Two choices keep the levels independent. Every sender call first runs the expiries that are due, so the clock moves in one place and an ACK never races a timeout. And every call ends by transmitting whatever now fits under one limit, `una + min(window, cwnd)`, so levels 3 and 4 only change what that limit is.

## Approach: timer-and-windows (Segment list with una and nxt marks, one retransmission timer and two windows)

### Intuition

Each mechanism answers one way the network can fail:

- **Sequence numbers** answer reordering and duplication: a byte's number says where it goes, so the receiver can put early bytes aside and drop bytes it already has.
- **Cumulative ACKs** answer lost acknowledgements: each ACK repeats everything the ones before it said, so losing one costs nothing once the next arrives.
- **The retransmission timer** answers lost data: a segment that is not acknowledged in time is sent again.
- **The RTO estimator** answers the fact that paths differ: a timeout of a fixed length is either too eager on a slow path or too lazy on a fast one, so the sender measures round trips and keeps a smoothed mean (`srtt`) and a smoothed deviation (`rttvar`), and waits for the mean plus four deviations.
- **Karn's algorithm** answers the ambiguity of an ACK for a resent segment: it could answer either copy, so such a sample is not taken.
- **Backoff** answers persistent loss: doubling the timeout after each expiry stops a sender from hammering a path that is down or congested.
- **Flow control** answers a slow receiver: the advertised window says how much it can still accept.
- **Congestion control** answers a crowded network: `cwnd` starts small, grows quickly while ACKs flow (slow start), then slowly (congestion avoidance), and shrinks when loss signals congestion: to one segment after a timeout, to half the flight after duplicate ACKs.
- **Fast retransmit and fast recovery** answer the cost of waiting for a timer: three duplicate ACKs say that one segment is missing while later ones arrive, so the sender resends it at once, and keeps sending new data at a reduced rate instead of starting over from one segment.

### Algorithm

1. **Receiver.** For each byte of a segment at or above the next expected number, keep it unless it is already held. Then, while the next expected byte is held, remove it, append it to the result and move on. `buffered()` is the number of bytes held; `ackNumber()` is the next expected number.
2. **Segments.** `send` cuts its bytes into segments of 1000 and a shorter last one, numbered after the previous bytes, and adds them, not yet transmitted, to the list.
3. **Clock.** At the start of every sender call, while the timer is on and its deadline `T` is at or before `now`: with congestion control, set `ssthresh = max((nxt - una) / 2, 2000)`, `cwnd = 1000` and leave fast recovery; retransmit the oldest outstanding segment; double the RTO up to 60000; set the deadline to `T + rto`; add a trace row at `T` if the congestion state changed.
4. **ACK.** Ignore it if `ackNo < una` or `ackNo > nxt`. If `ackNo > una`: set `una`; if it covers the timed segment, take the sample and update `rttvar`, `srtt` and `rto` in that order with floor division and the bounds; restart the timer at `now + rto`, or turn it off when nothing is outstanding; reset the duplicate count; then with congestion control, deflate (`cwnd = ssthresh`) if in fast recovery, else add `min(N, 1000)` in slow start, else count `N` and add 1000 when the count reaches `cwnd`. If `ackNo == una`, data is outstanding and the window is unchanged, it is a duplicate: in fast recovery add 1000; on the third, set `ssthresh = max((nxt - una) / 2, 2000)`, `cwnd = ssthresh + 3000`, enter fast recovery and retransmit the oldest outstanding segment. Then take the ACK's window, and add a trace row if the congestion state changed.
5. **Transmit.** While the next untransmitted segment satisfies `seq + length <= una + min(window, cwnd)`, transmit it, move `nxt` past it, start timing it if nothing is timed, and start the timer if it is off.
6. **Retransmit.** Every retransmission stops the RTT timing, and is not limited by either window.

### Correctness

Receiver: by induction on the segments, every byte below `ackNumber()` has been delivered exactly once and in order, and every byte held is at or above it. A byte is delivered only when every byte before it was delivered, and once delivered it is below `ackNumber()` and every later copy is dropped by rule 2, so nothing is delivered twice. Since a segment's content never differs between copies, the delivered stream is the sender's stream.

Sender, timer: the timer is on exactly when data is outstanding. It starts with the first transmission while it is off, an ACK turns it off when `una` reaches `nxt`, and an expiry always restarts it. So every outstanding byte is eventually covered: if no ACK ever covers it, the timer expires and resends the oldest segment, which is the one that blocks `una`. Running due expiries before anything else makes a call's result depend only on the time and the order of calls, never on how often `tick` is called in between, and the backoff is measured from the expiry time, so a late `tick` changes nothing.

Estimator: with non-negative integers and floor division, every language computes the same values; the bounds keep the RTO between one second and one minute, as RFC 6298 requires and allows. Karn's rule makes every sample unambiguous: timing stops on any retransmission, and a new segment can only be timed once every earlier timed segment is resolved.

Windows: a segment goes out only when its last byte is at most `una + min(window, cwnd)`, so the sender never has more than `min(window, cwnd)` bytes beyond `una`, which is RFC 5681's rule for both windows at once. Since segments go out strictly in order, `nxt` only moves forward and the flight size `nxt - una` is exactly the outstanding data.

### Complexity

- Time: O(k) per receive of k bytes; O(s) per sender call over s segments — the receiver touches each byte of a segment once, plus each byte it releases, which is paid for by the byte's arrival; the sender scans its list for the next segment to send and the oldest outstanding one, and runs at most a few expiries per call in practice.
- Space: O(b + s) for b held bytes and s segments — the receiver holds each early byte once; the sender keeps one small record per segment, plus constant state for the estimator, the timer and the windows.

### Trade-offs

- Holding early bytes in a map by position is simple and handles any overlap. A real receiver keeps a list of byte ranges, merging neighbours, so memory grows with the number of gaps rather than the number of bytes.
- Retransmitting only the oldest segment on a timeout, as RFC 6298 says, recovers one loss per backed-off timeout. RFC 5681 describes recovery after a timeout as slow start from one segment, and notes that slow-start-based recovery can cause spurious retransmissions; the selective acknowledgement (SACK) option it cites lets a receiver say exactly which ranges arrived.
- Timing one segment per round trip is what RFC 6298 calls the traditional way. With the TCP timestamp option, RFC 6298 notes, every ACK can give a sample, including the ACK of a retransmitted segment, since the timestamp says which copy it answers.
- Counting bytes in congestion avoidance needs one more variable than adding `MSS * MSS / cwnd` per ACK, which RFC 5681 also allows. Counting is robust against a receiver that splits its ACKs, and against delayed ACKs that would otherwise slow growth.
- Fast recovery as RFC 5681 states it ends at the first ACK of new data. With several losses in one window, that ACK is partial and the next loss waits for three more duplicates or a timeout. RFC 5681 says this does not recover efficiently from multiple losses, recommends an advanced loss recovery algorithm, and describes algorithms that use such partial acknowledgements, or SACK, to repair every loss of a window in one recovery.
- RFC 5681 holds `ssthresh` constant when the same segment times out a second time. Here the flight size cannot change between two such timeouts (no ACK moved `una`, and `cwnd` is one segment, so nothing new was sent), so recomputing it gives the same value and the rule can be left out without changing any result.

### Pitfalls and edge cases

- Level 1, overlaps. A segment can start below the next expected byte, fill the gap and run into bytes already held; only its new bytes count, and each position is held once, however many copies arrive (`h2`, `h4`). Bytes below the next expected one are duplicates even when held bytes exist above (`h3`).
- Level 2, the order of the estimator. `rttvar` uses the old `srtt`, so it must be computed first; doing it the other way, or rounding instead of truncating, gives different numbers within two samples (`h5`). The first sample sets `rttvar` to half of it. The one-second minimum applies after each computation (`h11`), and backoff stops at 60 seconds (`h6`).
- Level 2, Karn's algorithm. After a retransmission, the next ACK gives no sample, so the backed-off RTO stays until a new segment is timed; that sample then brings it back down (`ex4`, `h8`).
- Level 2, one timed segment. A segment sent while another is timed is never timed, even if its ACK arrives later (`h11`).
- Level 2, the timer. A send while the timer runs does not move it; any ACK of new data restarts it from the ACK's time with the current RTO; an ACK that acknowledges nothing does not touch it (`h7`, `h9`).
- Level 2, the clock. A single call runs every expiry that is due, each from its own deadline (`h10`, `h12`), and an expiry due at exactly the time of a call runs first (`h28`).
- Level 2, which ACKs count. An ACK above `nxt` would acknowledge bytes never sent and is ignored; an old one is ignored too (`h9`).
- Level 3, the window's base. It is measured from `una`, not from `nxt`: measured from `nxt`, the sender would keep a full window of new data in flight beyond what is unacknowledged (`h13`). A segment must fit entirely (`h13`), a window update alone can release segments (`h14`), and an ignored ACK changes no window (`h15`).
- Level 3, `ack` and the window. An ACK without a window keeps the last one, which slides with `una` (`h16`). A shrinking window takes nothing back, and a retransmission still goes out when the window is closed (`h17`).
- Level 3, timing a segment that waited. Timing starts when a segment is transmitted, not when it was handed over (`h18`).
- Level 4, slow start. One ACK adds at most one segment (`h20`). At `cwnd == ssthresh` the sender is in congestion avoidance (`h29`), and slow start may overshoot `ssthresh` (`h25`).
- Level 4, congestion avoidance. The count subtracts the old `cwnd`, and a row is added only when a value changes (`h19`).
- Level 4, loss. After a timeout `ssthresh` is half the flight, not half of `cwnd`, which differ during fast recovery (`h26`), and never below two segments (`h22`). A duplicate needs outstanding data and the same window; a window change is not a duplicate (`h23`). Fast recovery inflates `cwnd` on each further duplicate but still respects the receiver's window (`h24`), deflates on the next new ACK (`ex8`), and a partial ACK ends it, so three more duplicates start another (`h27`).

### Language notes

- Python: a `dict` from position to character holds early bytes, and `setdefault` keeps the first copy. Integer `//` is floor division and never overflows. The trace compares a `(cwnd, ssthresh)` tuple before and after each event.
- TypeScript: `Math.floor` after each division keeps the arithmetic integral, and every value stays far below 2^53, so `number` is exact. A `Map<number, string>` holds the early bytes.
- Java: `int` division truncates toward zero, which equals floor division for these non-negative values; times are `long`. The window and `cwnd` are boxed `Integer`s with `null` for unlimited.
- Kotlin: the same JVM integer division; nullable `Int?` fields stand for an unlimited window or congestion window, and `listOfNotNull(window, cwnd).minOrNull()` picks the limit.
- Go: integer division truncates, which is floor division here. `-1` stands for an unlimited window or congestion window, and the result slices start empty and non-nil.
- Rust: `i64` holds times and `i32` the values the signature declares; `Option<i32>` holds the window and `cwnd`. Division truncates toward zero, which is floor division for non-negative values.

## Further reading

- [RFC 9293, Transmission Control Protocol](https://www.rfc-editor.org/rfc/rfc9293.html): sequence numbers for every octet, cumulative acknowledgement, `SND.UNA` and `SND.NXT`, and acceptable ACKs (section 3.4); shrinking windows and retransmitting beyond the right edge of the window (section 3.8.6); zero-window probing (section 3.8.6.1); ignoring old ACKs and ACKs of unsent data, and the send window as an offset from `SND.UNA` (section 3.10.7.4).
- [RFC 6298, Computing TCP's Retransmission Timer](https://www.rfc-editor.org/rfc/rfc6298.html): the initial RTO of one second, SRTT and RTTVAR with alpha 1/8 and beta 1/4 in that order, the one-second minimum and the optional maximum of at least 60 seconds (section 2); Karn's algorithm and one measurement per round trip (section 3); clock granularity (section 4); managing the timer, backing off, and collapsing the RTO after a new measurement (section 5).
- [RFC 5681, TCP Congestion Control](https://www.rfc-editor.org/rfc/rfc5681.html): definitions of cwnd, rwnd, flight size and duplicate ACKs (section 2); the initial window, slow start with `min(N, SMSS)`, congestion avoidance by counting bytes, and the response to a timeout (section 3.1); fast retransmit and fast recovery (section 3.2); loss recovery for several losses in one window, with partial acknowledgements or SACK (section 4.3).
