MSS = 1000
INITIAL_RTO = 1000
MIN_RTO = 1000
MAX_RTO = 60000
GRANULARITY = 1
INITIAL_WINDOW = 4 * MSS
DUPLICATE_THRESHOLD = 3


class Segment:
    def __init__(self, seq: int, length: int) -> None:
        self.seq = seq
        self.length = length
        self.sent = False
        self.timed_out = False

    @property
    def end(self) -> int:
        return self.seq + self.length


class ReliableTransport:
    """The receiver keeps the bytes that arrive ahead of the next expected one and releases
    them once the gap before them fills. The sender keeps its segments in order with two
    marks, the oldest unacknowledged byte and the next byte to send; one retransmission timer
    covers the oldest outstanding segment, with its timeout estimated from measured round
    trips. Every call first runs the timer expiries that are due, so the virtual clock moves
    forward in one place. Sending is limited by the smaller of the receiver's window and the
    congestion window, each of which is unlimited until it is set.
    """

    def __init__(self) -> None:
        # Receiver
        self._delivered = 0
        self._held: dict[int, str] = {}
        # Sender
        self._segments: list[Segment] = []
        self._una = 0
        self._nxt = 0
        self._rto = INITIAL_RTO
        self._srtt = -1
        self._rttvar = -1
        self._deadline = -1
        self._timed: tuple[Segment, int] | None = None
        self._window: int | None = None
        # Congestion control
        self._cwnd: int | None = None
        self._ssthresh = 0
        self._acked_in_avoidance = 0
        self._duplicates = 0
        self._recovering = False
        self._trace: list[list[int]] = []

    # Level 1
    def receive(self, seq: int, data: str) -> str:
        for offset, char in enumerate(data):
            position = seq + offset
            if position >= self._delivered:
                self._held.setdefault(position, char)
        released = []
        while self._delivered in self._held:
            released.append(self._held.pop(self._delivered))
            self._delivered += 1
        return "".join(released)

    def buffered(self) -> int:
        return len(self._held)

    def ack_number(self) -> int:
        return self._delivered

    # Level 2
    def send(self, length: int, now: int) -> list[list[int]]:
        sent = self._expire(now)
        end = self._segments[-1].end if self._segments else 0
        while length > 0:
            size = min(length, MSS)
            self._segments.append(Segment(end, size))
            end += size
            length -= size
        return sent + self._transmit_new(now)

    def ack(self, ack_no: int, now: int) -> list[list[int]]:
        return self._acknowledge(ack_no, self._window, now)

    def tick(self, now: int) -> list[list[int]]:
        return self._expire(now)

    def timer_state(self) -> list[int]:
        return [self._srtt, self._rttvar, self._rto, self._deadline]

    # Level 3
    def ack_window(self, ack_no: int, window: int, now: int) -> list[list[int]]:
        return self._acknowledge(ack_no, window, now)

    # Level 4
    def enable_congestion_control(self, ssthresh: int, now: int) -> None:
        self._expire(now)
        self._cwnd = INITIAL_WINDOW
        self._ssthresh = ssthresh
        self._trace.append([now, self._cwnd, self._ssthresh])

    def congestion_trace(self) -> list[list[int]]:
        return [list(row) for row in self._trace]

    # The sender
    def _expire(self, now: int) -> list[list[int]]:
        sent: list[list[int]] = []
        while self._deadline != -1 and self._deadline <= now:
            sent += self._timeout(self._deadline)
        return sent

    def _timeout(self, at: int) -> list[list[int]]:
        before = self._congestion()
        oldest = self._oldest_unacked()
        if self._cwnd is not None:
            # RFC 5681 holds ssthresh when the timer resends a segment it has resent before.
            if not oldest.timed_out:
                self._ssthresh = max((self._nxt - self._una) // 2, 2 * MSS)
            self._cwnd = MSS
            self._recovering = False
            self._duplicates = 0
            self._acked_in_avoidance = 0
        oldest.timed_out = True
        sent = [self._retransmit(oldest)]
        self._rto = min(2 * self._rto, MAX_RTO)
        self._deadline = at + self._rto
        self._note(at, before)
        return sent + self._transmit_new(at)

    def _acknowledge(self, ack_no: int, window: int | None, now: int) -> list[list[int]]:
        sent = self._expire(now)
        if ack_no < self._una or ack_no > self._nxt:
            return sent
        before = self._congestion()
        if ack_no > self._una:
            self._new_data(ack_no, now)
        elif window == self._window and self._nxt > self._una:
            sent += self._duplicate()
        self._window = window
        self._note(now, before)
        return sent + self._transmit_new(now)

    def _new_data(self, ack_no: int, now: int) -> None:
        newly = ack_no - self._una
        self._una = ack_no
        if self._timed is not None and ack_no >= self._timed[0].end:
            self._measure(now - self._timed[1])
            self._timed = None
        self._deadline = -1 if self._una == self._nxt else now + self._rto
        self._duplicates = 0
        if self._cwnd is None:
            return
        if self._recovering:
            self._cwnd = self._ssthresh
            self._recovering = False
        elif self._cwnd < self._ssthresh:
            self._cwnd += min(newly, MSS)
        else:
            self._acked_in_avoidance += newly
            if self._acked_in_avoidance >= self._cwnd:
                self._acked_in_avoidance -= self._cwnd
                self._cwnd += MSS

    def _duplicate(self) -> list[list[int]]:
        if self._cwnd is None:
            return []
        self._duplicates += 1
        if self._recovering:
            self._cwnd += MSS
            return []
        if self._duplicates != DUPLICATE_THRESHOLD:
            return []
        self._ssthresh = max((self._nxt - self._una) // 2, 2 * MSS)
        self._cwnd = self._ssthresh + 3 * MSS
        self._recovering = True
        self._acked_in_avoidance = 0
        return [self._retransmit(self._oldest_unacked())]

    def _measure(self, sample: int) -> None:
        if self._srtt == -1:
            self._srtt = sample
            self._rttvar = sample // 2
        else:
            self._rttvar = (3 * self._rttvar + abs(self._srtt - sample)) // 4
            self._srtt = (7 * self._srtt + sample) // 8
        rto = self._srtt + max(GRANULARITY, 4 * self._rttvar)
        self._rto = min(max(rto, MIN_RTO), MAX_RTO)

    def _oldest_unacked(self) -> Segment:
        return next(segment for segment in self._segments if segment.end > self._una)

    def _retransmit(self, segment: Segment) -> list[int]:
        self._timed = None  # Karn: a retransmitted segment can no longer be timed
        return [segment.seq, segment.length, 1]

    def _limit(self) -> int | None:
        limits = [limit for limit in (self._window, self._cwnd) if limit is not None]
        return min(limits) if limits else None

    def _transmit_new(self, now: int) -> list[list[int]]:
        sent = []
        for segment in self._segments:
            if segment.sent:
                continue
            limit = self._limit()
            if limit is not None and segment.end > self._una + limit:
                break
            segment.sent = True
            self._nxt = segment.end
            if self._timed is None:
                self._timed = (segment, now)
            if self._deadline == -1:
                self._deadline = now + self._rto
            sent.append([segment.seq, segment.length, 0])
        return sent

    def _congestion(self) -> tuple[int | None, int]:
        return self._cwnd, self._ssthresh

    def _note(self, at: int, before: tuple[int | None, int]) -> None:
        if self._cwnd is not None and before != self._congestion():
            self._trace.append([at, self._cwnd, self._ssthresh])
