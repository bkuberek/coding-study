# Reliable Transport Sim

## Statement

Build `ReliableTransport`, the two halves of a reliable byte stream in the style of TCP: a receiver that puts arriving data back in order, and a sender that numbers its data, retransmits what is lost, and paces itself so that it overwhelms neither the receiver nor the network. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**Why a transport protocol is needed.** A network moves data in small units called **packets**, and makes no promises about them: a packet can be lost, delivered twice, or overtaken by a packet sent after it. An application that sends a file wants the opposite: every byte, once, in order. A transport protocol builds that promise on top of the unreliable network.

**Segments, sequence numbers and acknowledgements.** The sender cuts its byte stream into **segments**, each carried by one packet. Every byte has a **sequence number**, its position in the stream, starting at 0, and a segment is described by the sequence number of its first byte and its length. The segment `[seq 1000, length 500]` carries bytes 1000 to 1499. The receiver answers with **acknowledgements** (ACKs). In this problem, as in TCP, an ACK is **cumulative**: an ACK number of `X` means "I have every byte before `X`; send me `X` next". One number therefore summarizes everything received in order, and a lost ACK is repaired by the next one.

**A worked example.** The sender sends `Hel` as seq 0, `lo ` as seq 3 and `World` as seq 6. The network loses nothing but delivers them as seq 0, seq 6, seq 3. The receiver delivers `Hel` at once and acknowledges 3; it holds `World`, since bytes 3 to 5 are missing, and acknowledges 3 again; when seq 3 arrives it delivers `lo World` and acknowledges 11.

The simulation has no real network. The receiver's methods are called with the segments that arrive. The sender's methods are called with the ACKs that arrive and with the current time, and they return the segments the sender transmits. Time is a virtual clock in milliseconds, given to every sender method as `now`.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, finish level 1 by about minute 25, level 2 by 65, level 3 by 80 and level 4 by 115.

## Input

- `ReliableTransport()`: creates one endpoint with an empty receiver and an empty sender.
- Sequence numbers, lengths and windows are integers counted in bytes. Times `now` are integers in milliseconds.
- Each level's section describes the methods it adds and their parameters.

## Output

- The receiver's methods return text or numbers, as each level says.
- The sender's methods return the segments transmitted during the call, in the order they were transmitted, each as `[seq, length, retransmitted]`, where `retransmitted` is `1` when the segment had been transmitted before and `0` otherwise.

## Level 1: Putting bytes back in order

- `receive(seq, data)`: a segment arrives: its bytes are `data`, one character per byte, and the first has sequence number `seq`. Returns the bytes that this segment lets the receiver deliver to the application, in order, as one string (possibly empty).
- `buffered()`: the number of bytes the receiver holds that it cannot deliver yet.
- `ackNumber()`: the sequence number of the next byte the receiver expects, which is the number its cumulative ACK carries. Before anything is delivered it is 0.

**The rules:**

1. The receiver delivers bytes in sequence order, each exactly once. The next byte to deliver is the one numbered `ackNumber()`.
2. A byte with a number below `ackNumber()` was delivered already: a duplicate, ignored.
3. A byte at or above `ackNumber()` is kept until it can be delivered. A byte the receiver already holds is not kept twice, so `buffered()` counts positions, not arrivals.
4. After a segment arrives, every byte from `ackNumber()` onward that is now held without a gap is delivered and returned, and `ackNumber()` moves past it.

A segment may overlap bytes already delivered, bytes already held, or both; only its new bytes count. The network may duplicate and reorder segments but never changes their content: two segments never carry different bytes for the same number.

### Example 1

<!-- case: ex1 -->

The worked example: `World` waits for the gap at bytes 3 to 5, and `lo ` fills it, releasing `lo World`.

### Example 2

<!-- case: ex2 -->

The repeated `abc` is a duplicate. `cdef` overlaps one delivered byte and adds three new ones. `kl` and `ijk` both arrive early and overlap at byte 10, so four positions are held, and `gh` releases all of them.

## Level 2: Acknowledgements and retransmission

The sender's side. A segment that is lost is never acknowledged, so the sender waits a while and then transmits it again. The art is in how long to wait: too short and it resends data that was only slow, adding load to a network that is already struggling; too long and a lost segment stalls the stream. RFC 6298 sets the rules this level follows.

- `send(length, now)`: the application hands the sender `length` more bytes. They are numbered after the bytes handed over before, and cut into segments of at most **1000 bytes** (the maximum segment size, MSS): full segments first and then a shorter one if bytes remain. Segments are never merged or split again later. Then the sender transmits what it may (at this level, everything). Returns the segments transmitted.
- `ack(ackNo, now)`: a cumulative ACK with number `ackNo` arrives. Returns the segments transmitted.
- `tick(now)`: time passes. Returns the segments transmitted.
- `timerState()`: `[srtt, rttvar, rto, deadline]` as defined below, with `-1` for `srtt` and `rttvar` before the first measurement and for `deadline` while the timer is off.

**Time comes first.** Every sender method first runs, in time order, each expiry of the retransmission timer that is due at or before `now`, each one at its own time, and only then does its own work. An expiry due at exactly `now` runs before the call's work.

**Measuring the round trip.** The sender times one segment at a time. When it transmits a segment for the first time while no segment is being timed, it starts timing that segment. When an ACK arrives whose number is at least the end of the timed segment (its `seq + length`), the time since that segment was sent is a **round-trip sample** `R`, and timing stops. Any retransmission stops the timing without a sample: once a segment has been sent twice, an ACK cannot tell which copy it answers. This is **Karn's algorithm**, which RFC 6298 requires.

**The retransmission timeout (RTO)**, in whole milliseconds, with every division rounding down:

1. Before any sample, `rto = 1000`.
2. On the first sample: `srtt = R` and `rttvar = R / 2`.
3. On each later sample, in this order: `rttvar = (3 * rttvar + |srtt - R|) / 4`, then `srtt = (7 * srtt + R) / 8`. That is RFC 6298's update with alpha = 1/8 and beta = 1/4, with the old `srtt` in the first formula.
4. After each sample: `rto = srtt + max(1, 4 * rttvar)`, then raised to 1000 if it is below 1000 and lowered to 60000 if it is above. The `1` is the clock granularity of one millisecond.

`srtt` (smoothed RTT) follows the typical round trip, and `rttvar` how much it varies, so a path that is slow but steady gets a timeout close to its round trip, and a jittery one gets a margin.

**The timer.** One retransmission timer covers the oldest outstanding segment. A segment is **outstanding** from its transmission until an ACK covers its last byte.

1. Whenever a segment is transmitted and the timer is off, it starts: `deadline = now + rto`.
2. An ACK that acknowledges new data (its number is above the oldest unacknowledged byte) restarts the timer, `deadline = now + rto` with the `rto` after any sample this ACK gave, or turns it off if nothing is outstanding any more.
3. When the timer expires at time `T`: retransmit the oldest outstanding segment, double the RTO (`rto = min(2 * rto, 60000)`, which RFC 6298 calls backing off), and restart the timer at `deadline = T + rto`. Only that one segment is resent.

**Which ACKs count.** Let `una` be the oldest unacknowledged byte and `nxt` the byte after the last one transmitted. An ACK with `una < ackNo <= nxt` acknowledges new data: `una` becomes `ackNo`. An ACK with `ackNo == una` acknowledges nothing new, and one below `una` is old; neither changes anything at this level. An ACK above `nxt` acknowledges bytes never sent and is ignored. In the cases, an ACK number never falls inside a segment that was sent: it is 0, the end of a sent segment, or above `nxt`.

### Example 1

<!-- case: ex3 -->

2,500 bytes become two full segments and one of 500, all transmitted at time 0; the first is timed, and the timer is set for `0 + 1000`. The ACK at 400 covers the timed segment: a sample of 400 gives `srtt = 400`, `rttvar = 200` and `rto = 400 + 800 = 1200`, and the timer restarts at `400 + 1200`. The last ACK covers everything, so the timer turns off.

### Example 2

<!-- case: ex4 -->

Nothing comes back. At 1000 the timer expires: the segment is resent and the RTO doubles to 2000; at 3000 it expires again and the RTO becomes 4000. The ACK at 3500 gives no sample, because the segment was retransmitted, so the backed-off RTO stays.

## Level 3: The sliding window

A receiver has limited room. With each ACK it **advertises a window**: how many bytes, starting at the ACK number, it is ready to accept. The sender must not send beyond that edge. This is **flow control**: it keeps a fast sender from overrunning a slow receiver.

- `ackWindow(ackNo, window, now)`: an ACK with number `ackNo` that also advertises `window` bytes. It is processed as `ack` is, and then the advertised window becomes `window`. An ACK that is ignored (below `una` or above `nxt`) changes the window neither.

**The rules:**

1. The window is measured from `una`: the sender may transmit a segment only if its last byte is within the window, that is if `seq + length <= una + window`. A segment that does not fit entirely waits, and so does every segment after it.
2. `ack(ackNo, now)` is an ACK that advertises the same window as the last one. As `una` moves forward, the window slides forward with it, which is what makes it a sliding window.
3. Before any `ackWindow`, the window is unlimited, as at level 2.
4. After each `send`, ACK and expiry, the sender transmits every waiting segment that now fits, in order. An ACK that only changes the window can therefore release segments.
5. Retransmissions are not limited by the window: RFC 9293 lets a sender retransmit data beyond the right edge of the window.
6. A segment that waited is timed, and starts the timer, when it is finally transmitted, following the rules of level 2.

A window can shrink so that data already in flight is beyond its edge. Nothing is taken back; the sender only stops sending new data until the window allows it.

### Example 1

<!-- case: ex5 -->

With a 2,000-byte window, only the first two segments go out. Each ACK slides the window: at 300 the edge is `1000 + 2000`, releasing one more segment; at 600 the window shrinks to 1,000 bytes from `una = 3000`, and at 900 it grows to 3,000, which releases the last segment.

### Example 2

<!-- case: ex6 -->

A zero window lets nothing out, so no timer runs. An ACK that only opens the window to 1,500 bytes releases the first segment but not the second, whose last byte would be byte 2,000. The next ACK slides the window far enough.

## Level 4: Congestion control

The receiver's window protects the receiver; nothing so far protects the network between the two. If every sender sent as fast as its receiver allowed, the routers of a busy path would queue packets and then drop them, and the retransmissions would add to the load. RFC 6298 notes that the Internet relies on correct retransmission timers and on RFC 5681's algorithms to avoid congestion collapse. RFC 5681 defines TCP's defense: a **congestion window** (`cwnd`) that the sender keeps for itself, probing for capacity while ACKs come back and backing off when segments are lost.

- `enableCongestionControl(ssthresh, now)`: turns congestion control on, with `cwnd = 4000` (the initial window, 4 segments, which RFC 5681 allows for a segment size up to 1,095 bytes) and the slow start threshold `ssthresh` given. A case calls it at most once, right after the constructor, possibly after an `ackWindow`. Before it is called, there is no congestion window.
- `congestionTrace()`: the history of the congestion state as rows `[time, cwnd, ssthresh]`: one row when congestion control is turned on, and one more each time an event changes `cwnd` or `ssthresh`, with the values after the event. An event is a call's own work at its `now` (an ACK) or a timer expiry at its own time.

**The rules** (RFC 5681, simplified as stated):

1. **The limit.** A segment may be transmitted only if `seq + length <= una + min(cwnd, window)`, with the window unlimited if none was advertised.
2. **Slow start**, while `cwnd < ssthresh`: each ACK of new data adds `min(N, 1000)` to `cwnd`, where `N` is the number of bytes it newly acknowledges. One ACK adds at most one segment, however much it acknowledges, which RFC 5681 recommends so that a receiver cannot inflate `cwnd` by splitting its ACKs. When every segment is acknowledged, `cwnd` roughly doubles every round trip, and it may end above `ssthresh`.
3. **Congestion avoidance**, while `cwnd >= ssthresh`: the sender counts the bytes newly acknowledged. When the count reaches `cwnd`, it subtracts `cwnd` (the value before the increase) from the count and adds 1000 to `cwnd`, at most once per ACK. `cwnd` then grows by about one segment per round trip. The count starts at 0 and returns to 0 after any loss.
4. **Timeout.** When the retransmission timer expires, a segment was very likely lost to congestion: `ssthresh = max(F / 2, 2000)`, where `F` is the flight size `nxt - una` at that moment, and `cwnd = 1000`. Slow start then rebuilds `cwnd` from one segment.
5. **Duplicate ACKs.** An ACK is a **duplicate** when data is outstanding, its number equals `una`, and the window it advertises equals the current one; RFC 5681 defines it this way, so an ACK that only changes the window is not a duplicate. A receiver sends a duplicate for each segment that arrives after a gap, so a run of them says that one segment is missing while later ones are getting through. Any ACK of new data resets the count of duplicates to 0.
6. **Fast retransmit.** On the third duplicate in a row: `ssthresh = max(F / 2, 2000)`, retransmit the oldest outstanding segment without waiting for the timer, and set `cwnd = ssthresh + 3000`. The sender is now in **fast recovery**. (RFC 5681 suggests also sending new data on the first two duplicates; this problem does not.)
7. **Fast recovery.** Each further duplicate adds 1000 to `cwnd`, since each one means another segment has left the network, and new segments go out when the limit allows. The next ACK of new data ends fast recovery and sets `cwnd = ssthresh`, which RFC 5681 calls deflating the window; that ACK makes no other change to `cwnd`. A timeout during fast recovery ends it too, with rule 4.

Retransmissions are not limited by `cwnd`. The timer, the RTO and Karn's algorithm work as at level 2, so a fast retransmit stops the timing of a segment.

### Example 1

<!-- case: ex7 -->

Slow start: 4 segments go out, and each ACK adds one segment to `cwnd` and lets two segments go, one for the segment that left and one for the growth. The ACK at 120 acknowledges 2,000 bytes but adds only 1,000.

### Example 2

<!-- case: ex8 -->

The segment at 1000 is lost. The three ACKs that repeat 1000 are duplicates; the third triggers a fast retransmit with `ssthresh = 5000 / 2` and `cwnd = 2500 + 3000`. The fourth inflates `cwnd` to 6,500, which releases a new segment. The ACK of 7000 ends fast recovery and deflates `cwnd` to `ssthresh`.

## Constraints

- At most 2,000 calls per test.
- `0 <= seq`, `seq + data.length <= 10^6`, and `data` has at most 1,000 characters.
- `1 <= length <= 10^5` for `send`, and the bytes handed to the sender total at most 10^6.
- `0 <= window <= 10^6` and `2000 <= ssthresh <= 10^6`.
- `0 <= now <= 10^9`, and `now` never decreases from one sender call to the next.

## Follow-ups

- Real sequence numbers are 32 bits and wrap around, and RFC 9293 compares them modulo 2^32. Which comparisons in your sender would break after 4 GiB, and how would you write them?
- When the advertised window is zero and the ACK that reopens it is lost, both sides wait forever. RFC 9293 requires the sender to probe a zero window. When should the first probe go out, and what should it carry?
- RFC 5681 holds `ssthresh` constant when the same segment times out a second time. Why does that make no difference in this simulation, and when would it in a real sender?
- After one fast retransmit, this sender recovers only one lost segment per round trip at best. What extra information would let a sender repair several losses from one window at once?
- RFC 6298 allows clearing `srtt` and `rttvar` after several backoffs. Why might the old estimates be wrong at that point?

## Hints

### Hint 1

For the receiver, a map from sequence number to character is enough: put each new byte at or above the next expected number into it, then pop characters from the next expected number for as long as they are there.

### Hint 2

For the sender, keep the list of segments with a flag for "transmitted", and two numbers: `una`, the oldest unacknowledged byte, and `nxt`, the byte after the last one transmitted. Everything else (what is outstanding, the flight size, what may go next) follows from them.

### Hint 3

Write one helper that runs every timer expiry due at or before a time, and call it at the start of every sender method. Write another that transmits the waiting segments that fit; call it at the end of every method that can change what fits.

### Hint 4

Keep the timed segment and its send time as one optional value. Set it when you transmit a segment for the first time and it is empty; clear it on any retransmission and when its sample is taken.

### Hint 5

For level 4, look up the congestion state before and after handling each ACK or expiry, and add a trace row only when it changed. Fast recovery needs one flag and a count of duplicates in a row.
