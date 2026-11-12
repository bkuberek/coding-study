"""reliable-transport-sim promises that its hidden cases catch the classic mistakes of building a
reliable byte stream: delivering out of order or twice, counting held bytes per arrival, the
RFC 6298 estimator updated in the wrong order or rounded the wrong way, Karn's algorithm left out,
a timer restarted at the wrong moments or backed off from the wrong time, go-back-N on timeout,
windows measured from the wrong edge or forgotten, and congestion control with the wrong
increase, the wrong loss response, duplicate ACKs miscounted or fast recovery left unfinished.
These tests replay every case against a model of the endpoint written from the statement, which
must give every expected output, and against that model with one mistake planted at a time, which
some hidden case must fail.

The model keeps the received stream as a list of characters with a fill marker, the sender's
segments in a dict keyed by sequence number, and runs the clock through a queue of timer events,
so it shares no structure with the reference solutions."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0358-reliable-transport-sim"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

MSS = 1000
NONE = -1


class Model:
    """The endpoint as the statement words it. Each mistake below overrides one method."""

    def __init__(self) -> None:
        self.stream: list[str | None] = []
        self.next_byte = 0
        self.lengths: dict[int, int] = {}
        self.transmitted: set[int] = set()
        self.queued_end = 0
        self.una = 0
        self.nxt = 0
        self.srtt = NONE
        self.rttvar = NONE
        self.rto = 1000
        self.expires = NONE
        self.timing: tuple[int, int] | None = None
        self.window: int | None = None
        self.cwnd: int | None = None
        self.ssthresh = 0
        self.counted = 0
        self.dups = 0
        self.in_recovery = False
        self.history: list[list[int]] = []

    # --- level 1
    def keep(self, position: int, char: str) -> None:
        while len(self.stream) <= position:
            self.stream.append(None)
        if position >= self.next_byte and self.stream[position] is None:
            self.stream[position] = char

    def receive(self, seq: int, data: str) -> str:
        for i, char in enumerate(data):
            self.keep(seq + i, char)
        start = self.next_byte
        while self.next_byte < len(self.stream) and self.stream[self.next_byte] is not None:
            self.next_byte += 1
        return "".join(self.stream[start : self.next_byte])  # type: ignore[arg-type]

    def buffered(self) -> int:
        return sum(char is not None for char in self.stream[self.next_byte :])

    def ack_number(self) -> int:
        return self.next_byte

    # --- level 2: the estimator
    def first_sample(self, sample: int) -> None:
        self.srtt, self.rttvar = sample, sample // 2

    def later_sample(self, sample: int) -> None:
        self.rttvar = (3 * self.rttvar + abs(self.srtt - sample)) // 4
        self.srtt = (7 * self.srtt + sample) // 8

    def bound(self, rto: int) -> int:
        return min(max(rto, 1000), 60000)

    def sample(self, value: int) -> None:
        if self.srtt == NONE:
            self.first_sample(value)
        else:
            self.later_sample(value)
        self.rto = self.bound(self.srtt + max(1, 4 * self.rttvar))

    def backed_off(self) -> int:
        return min(2 * self.rto, 60000)

    # --- level 2: segments, timer and ACKs
    def send(self, length: int, now: int) -> list[list[int]]:
        out = self.run_clock(now)
        while length > 0:
            size = min(MSS, length)
            self.lengths[self.queued_end] = size
            self.queued_end += size
            length -= size
        return out + self.push(now)

    def due(self, now: int) -> bool:
        return self.expires != NONE and self.expires <= now

    def run_clock(self, now: int) -> list[list[int]]:
        out: list[list[int]] = []
        while self.due(now):
            out += self.expire(self.expires, now)
        return out

    def oldest(self) -> int:
        return self.una

    def resend(self, seq: int) -> list[int]:
        self.timing = None
        return [seq, self.lengths[seq], 1]

    def expiry_time(self, at: int, now: int) -> int:
        return at

    def expire(self, at: int, now: int) -> list[list[int]]:
        snapshot = (self.cwnd, self.ssthresh)
        if self.cwnd is not None:
            self.on_timeout_congestion()
        out = self.timeout_resends()
        self.rto = self.backed_off()
        self.expires = self.expiry_time(at, now) + self.rto
        self.record(self.trace_time(at, now), snapshot)
        return out + self.push(at)

    def timeout_resends(self) -> list[list[int]]:
        return [self.resend(self.oldest())]

    def trace_time(self, at: int, now: int) -> int:
        return at

    def on_timeout_congestion(self) -> None:
        self.ssthresh = max(self.flight_for_timeout() // 2, 2 * MSS)
        self.cwnd = MSS
        self.in_recovery = False
        self.dups = 0
        self.counted = 0

    def flight_for_timeout(self) -> int:
        return self.nxt - self.una

    def accepted(self, ack_no: int) -> bool:
        return self.una <= ack_no <= self.nxt

    def ack(self, ack_no: int, now: int) -> list[list[int]]:
        return self.incoming(ack_no, self.window, now)

    def ack_window(self, ack_no: int, window: int, now: int) -> list[list[int]]:
        return self.incoming(ack_no, window, now)

    def window_after(self, ack_no: int, window: int | None) -> int | None:
        return window

    def incoming(self, ack_no: int, window: int | None, now: int) -> list[list[int]]:
        out = self.run_clock(now)
        if not self.accepted(ack_no):
            return out
        snapshot = (self.cwnd, self.ssthresh)
        if ack_no > self.una:
            self.advance(ack_no, now)
        elif self.is_duplicate(window):
            out += self.on_duplicate(now)
        self.window = self.window_after(ack_no, window)
        self.record(now, snapshot)
        return out + self.push(now)

    def is_duplicate(self, window: int | None) -> bool:
        return window == self.window and self.nxt > self.una

    def takes_sample(self, ack_no: int) -> bool:
        return self.timing is not None and ack_no >= self.timing[0] + self.lengths[self.timing[0]]

    def restart_timer(self, now: int) -> None:
        self.expires = NONE if self.una == self.nxt else now + self.rto

    def advance(self, ack_no: int, now: int) -> None:
        newly = ack_no - self.una
        self.una = ack_no
        if self.takes_sample(ack_no):
            self.sample(now - self.timing[1])  # type: ignore[index]
            self.timing = None
        self.restart_timer(now)
        self.dups = self.reset_dups()
        if self.cwnd is not None:
            self.grow(newly)

    def reset_dups(self) -> int:
        return 0

    # --- level 3: what may go out
    def edge(self) -> int | None:
        limits = [x for x in (self.window, self.cwnd) if x is not None]
        return self.una + min(limits) if limits else None

    def fits(self, seq: int) -> bool:
        edge = self.edge()
        return edge is None or seq + self.lengths[seq] <= edge

    def start_timing(self, seq: int, now: int) -> None:
        if self.timing is None:
            self.timing = (seq, now)

    def start_timer(self, now: int) -> None:
        if self.expires == NONE:
            self.expires = now + self.rto

    def push(self, now: int) -> list[list[int]]:
        out = []
        seq = self.nxt
        while seq in self.lengths and seq not in self.transmitted and self.fits(seq):
            self.transmitted.add(seq)
            self.nxt = seq + self.lengths[seq]
            self.start_timing(seq, now)
            self.start_timer(now)
            out.append([seq, self.lengths[seq], 0])
            seq = self.nxt
        return out

    def tick(self, now: int) -> list[list[int]]:
        return self.run_clock(now)

    def timer_state(self) -> list[int]:
        return [self.srtt, self.rttvar, self.rto, self.expires]

    # --- level 4
    def enable_congestion_control(self, ssthresh: int, now: int) -> None:
        self.run_clock(now)
        self.cwnd, self.ssthresh = 4 * MSS, ssthresh
        self.history.append([now, self.cwnd, self.ssthresh])

    def in_slow_start(self) -> bool:
        return self.cwnd < self.ssthresh  # type: ignore[operator]

    def slow_start_step(self, newly: int) -> int:
        return min(newly, MSS)

    def avoidance(self, newly: int) -> None:
        self.counted += newly
        if self.counted >= self.cwnd:  # type: ignore[operator]
            self.counted -= self.cwnd  # type: ignore[operator]
            self.cwnd += MSS  # type: ignore[operator]

    def grow(self, newly: int) -> None:
        if self.in_recovery:
            self.leave_recovery()
        elif self.in_slow_start():
            self.cwnd += self.slow_start_step(newly)  # type: ignore[operator]
        else:
            self.avoidance(newly)

    def leave_recovery(self) -> None:
        self.cwnd = self.ssthresh
        self.in_recovery = False

    def fast_retransmit_cwnd(self) -> int:
        return self.ssthresh + 3 * MSS

    def inflate(self) -> None:
        self.cwnd += MSS  # type: ignore[operator]

    def threshold_reached(self) -> bool:
        return self.dups == 3

    def on_duplicate(self, now: int) -> list[list[int]]:
        if self.cwnd is None:
            return []
        self.dups += 1
        if self.in_recovery:
            self.inflate()
            return []
        if not self.threshold_reached():
            return []
        self.ssthresh = max((self.nxt - self.una) // 2, 2 * MSS)
        self.cwnd = self.fast_retransmit_cwnd()
        self.in_recovery = True
        self.counted = 0
        return [self.resend(self.una)]

    def changed(self, snapshot: tuple[int | None, int]) -> bool:
        return snapshot != (self.cwnd, self.ssthresh)

    def record(self, at: int, snapshot: tuple[int | None, int]) -> None:
        if self.cwnd is not None and self.changed(snapshot):
            self.history.append([at, self.cwnd, self.ssthresh])

    def congestion_trace(self) -> list[list[int]]:
        return [list(row) for row in self.history]


# --- level 1 mistakes
class DeliversOnArrival(Model):
    """Hands every new byte to the application as soon as it arrives."""

    def receive(self, seq: int, data: str) -> str:
        fresh = "".join(char for i, char in enumerate(data) if seq + i >= self.next_byte)
        self.next_byte = max(self.next_byte, seq + len(data))
        return fresh


class CountsArrivals(Model):
    """Counts every byte that arrived early, repeats included."""

    def __init__(self) -> None:
        super().__init__()
        self.arrivals: list[int] = []

    def keep(self, position: int, char: str) -> None:
        super().keep(position, char)
        if position >= self.next_byte:
            self.arrivals.append(position)

    def buffered(self) -> int:
        return sum(position >= self.next_byte for position in self.arrivals)


class DuplicatesDeliveredAgain(Model):
    """Delivers the part of a segment below the next expected byte again."""

    def receive(self, seq: int, data: str) -> str:
        old = "".join(char for i, char in enumerate(data) if seq + i < self.next_byte)
        return old + super().receive(seq, data)


class AckNumberIsTheHighestByteSeen(Model):
    """Acknowledges up to the highest byte received, gaps and all."""

    def __init__(self) -> None:
        super().__init__()
        self.highest = 0

    def receive(self, seq: int, data: str) -> str:
        self.highest = max(self.highest, seq + len(data))
        return super().receive(seq, data)

    def ack_number(self) -> int:
        return max(self.highest, self.next_byte)


# --- level 2 mistakes
class SrttUpdatedFirst(Model):
    """Updates SRTT before RTTVAR, so RTTVAR uses the new SRTT."""

    def later_sample(self, sample: int) -> None:
        self.srtt = (7 * self.srtt + sample) // 8
        self.rttvar = (3 * self.rttvar + abs(self.srtt - sample)) // 4


class RoundsHalfUp(Model):
    """Rounds the divisions to the nearest integer instead of down."""

    def later_sample(self, sample: int) -> None:
        self.rttvar = (3 * self.rttvar + abs(self.srtt - sample) + 2) // 4
        self.srtt = (7 * self.srtt + sample + 4) // 8


class FirstRttvarIsTheSample(Model):
    """Starts RTTVAR at the sample instead of half of it."""

    def first_sample(self, sample: int) -> None:
        self.srtt = self.rttvar = sample


class NoMinimumRto(Model):
    """Lets the RTO fall below one second."""

    def bound(self, rto: int) -> int:
        return min(rto, 60000)


class NoMaximumRto(Model):
    """Lets the RTO grow past 60 seconds."""

    def bound(self, rto: int) -> int:
        return max(rto, 1000)

    def backed_off(self) -> int:
        return 2 * self.rto


class NoKarn(Model):
    """Takes a sample from a segment that was retransmitted."""

    def resend(self, seq: int) -> list[int]:
        return [seq, self.lengths[seq], 1]


class EverySegmentTimed(Model):
    """Times every segment, so every ACK that ends a segment sent once gives a sample."""

    def __init__(self) -> None:
        super().__init__()
        self.sent_at: dict[int, int] = {}
        self.resent: set[int] = set()

    def start_timing(self, seq: int, now: int) -> None:
        self.sent_at.setdefault(seq, now)
        super().start_timing(seq, now)

    def resend(self, seq: int) -> list[int]:
        self.resent.add(seq)
        return super().resend(seq)

    def takes_sample(self, ack_no: int) -> bool:
        ends = [s for s in self.sent_at if s + self.lengths[s] == ack_no and s not in self.resent]
        if ends:
            self.timing = (ends[0], self.sent_at[ends[0]])
        return bool(ends)


class TimerRestartedOnEverySend(Model):
    """Restarts the timer whenever a segment goes out."""

    def start_timer(self, now: int) -> None:
        self.expires = now + self.rto


class TimerKeptOnNewAck(Model):
    """Keeps the old deadline when an ACK acknowledges new data."""

    def restart_timer(self, now: int) -> None:
        if self.una == self.nxt:
            self.expires = NONE


class BackoffForgotten(Model):
    """Restarts the timer with the old RTO instead of doubling it."""

    def backed_off(self) -> int:
        return self.rto


class BackoffFromTheCall(Model):
    """Restarts the timer from the time of the call instead of the time it expired."""

    def expiry_time(self, at: int, now: int) -> int:
        return now


class OneExpiryPerCall(Model):
    """Runs at most one expiry per call."""

    def run_clock(self, now: int) -> list[list[int]]:
        return self.expire(self.expires, now) if self.due(now) else []


class CallBeforeTimer(Model):
    """Lets an ACK at the deadline arrive before the expiry at the same time."""

    def due(self, now: int) -> bool:
        return self.expires != NONE and self.expires < now

    def tick(self, now: int) -> list[list[int]]:
        out = super().tick(now)
        if self.expires == now:
            out += self.expire(now, now)
        return out


class GoBackN(Model):
    """Resends every outstanding segment on a timeout."""

    def timeout_resends(self) -> list[list[int]]:
        out = []
        seq = self.una
        while seq < self.nxt:
            out.append(self.resend(seq))
            seq += self.lengths[seq]
        return out


class AckOfUnsentDataAccepted(Model):
    """Takes an ACK above anything sent as acknowledging everything."""

    def accepted(self, ack_no: int) -> bool:
        return ack_no >= self.una

    def advance(self, ack_no: int, now: int) -> None:
        super().advance(min(ack_no, self.nxt), now)


class RepeatedAckRestartsTimer(Model):
    """Restarts the timer on an ACK that acknowledges nothing new."""

    def on_duplicate(self, now: int) -> list[list[int]]:
        self.restart_timer(now)
        return super().on_duplicate(now)


# --- level 3 mistakes
class WindowIgnored(Model):
    """Never looks at the advertised window."""

    def window_after(self, ack_no: int, window: int | None) -> int | None:
        return None


class WindowFromNxt(Model):
    """Measures the window from the next byte to send instead of the oldest unacknowledged."""

    def edge(self) -> int | None:
        limits = [x for x in (self.window, self.cwnd) if x is not None]
        return self.nxt + min(limits) if limits else None


class SegmentMayStartInTheWindow(Model):
    """Sends a segment whose first byte is inside the window, even if it does not fit."""

    def fits(self, seq: int) -> bool:
        edge = self.edge()
        return edge is None or seq < edge


class RetransmissionsRespectTheWindow(Model):
    """Holds back a retransmission that is outside the window."""

    def timeout_resends(self) -> list[list[int]]:
        return [self.resend(self.una)] if self.fits(self.una) else []


class AckForgetsTheWindow(Model):
    """Treats an ACK without a window as unlimited."""

    def ack(self, ack_no: int, now: int) -> list[list[int]]:
        self.window = None
        return self.incoming(ack_no, None, now)


class IgnoredAckChangesTheWindow(Model):
    """Takes the window of an ACK that is otherwise ignored."""

    def incoming(self, ack_no: int, window: int | None, now: int) -> list[list[int]]:
        if not self.accepted(ack_no):
            self.window = window
        return super().incoming(ack_no, window, now)


class TimedWhenQueued(Model):
    """Starts timing a segment when the application hands it over, not when it is sent."""

    def send(self, length: int, now: int) -> list[list[int]]:
        first = self.queued_end
        out = super().send(length, now)
        if self.timing is None and first in self.lengths and first not in self.transmitted:
            self.timing = (first, now)
        return out


class WindowOnlyWithNewData(Model):
    """Takes a new window only from an ACK that acknowledges new data."""

    def incoming(self, ack_no: int, window: int | None, now: int) -> list[list[int]]:
        self.before = self.una
        return super().incoming(ack_no, window, now)

    def window_after(self, ack_no: int, window: int | None) -> int | None:
        return window if ack_no > self.before or self.window is None else self.window


# --- level 4 mistakes
class SlowStartAddsEveryByte(Model):
    """Adds every newly acknowledged byte to cwnd in slow start."""

    def slow_start_step(self, newly: int) -> int:
        return newly


class AvoidancePerAck(Model):
    """Adds MSS*MSS/cwnd on every ACK in congestion avoidance."""

    def avoidance(self, newly: int) -> None:
        self.cwnd += max(1, MSS * MSS // self.cwnd)  # type: ignore[operator]


class AvoidanceSubtractsTheNewCwnd(Model):
    """Subtracts the increased cwnd from the count of acknowledged bytes."""

    def avoidance(self, newly: int) -> None:
        self.counted += newly
        if self.counted >= self.cwnd:  # type: ignore[operator]
            self.cwnd += MSS  # type: ignore[operator]
            self.counted -= self.cwnd  # type: ignore[operator]


class SlowStartWhileEqual(Model):
    """Stays in slow start when cwnd equals ssthresh."""

    def in_slow_start(self) -> bool:
        return self.cwnd <= self.ssthresh  # type: ignore[operator]


class TimeoutHalvesCwnd(Model):
    """Halves cwnd instead of the flight size on a timeout."""

    def flight_for_timeout(self) -> int:
        return self.cwnd  # type: ignore[return-value]


class TimeoutKeepsCwnd(Model):
    """Lowers ssthresh on a timeout but keeps cwnd."""

    def on_timeout_congestion(self) -> None:
        cwnd = self.cwnd
        super().on_timeout_congestion()
        self.cwnd = cwnd


class NoSsthreshFloor(Model):
    """Lets ssthresh fall below two MSS."""

    def on_timeout_congestion(self) -> None:
        super().on_timeout_congestion()
        self.ssthresh = (self.nxt - self.una) // 2


class DuplicateWithoutOutstandingData(Model):
    """Counts a repeated ACK as a duplicate even when nothing is outstanding."""

    def is_duplicate(self, window: int | None) -> bool:
        return window == self.window


class WindowChangeIsADuplicate(Model):
    """Counts an ACK that only changes the window as a duplicate."""

    def is_duplicate(self, window: int | None) -> bool:
        return self.nxt > self.una


class FastRetransmitOnTheSecond(Model):
    """Retransmits on the second duplicate."""

    def threshold_reached(self) -> bool:
        return self.dups == 2


class NoInflation(Model):
    """Leaves cwnd alone on further duplicates during fast recovery."""

    def inflate(self) -> None:
        pass


class NoDeflation(Model):
    """Keeps the inflated cwnd when fast recovery ends."""

    def leave_recovery(self) -> None:
        self.in_recovery = False


class RecoveryIgnoresTheWindow(Model):
    """Sends during fast recovery as cwnd allows, past the receiver's window."""

    def edge(self) -> int | None:
        if self.in_recovery and self.cwnd is not None:
            return self.una + self.cwnd
        return super().edge()


class DuplicatesNeverReset(Model):
    """Keeps counting duplicates across ACKs of new data."""

    def reset_dups(self) -> int:
        return self.dups


class TimeoutLeavesRecoveryOn(Model):
    """Stays in fast recovery after a timeout."""

    def on_timeout_congestion(self) -> None:
        recovering = self.in_recovery
        super().on_timeout_congestion()
        self.in_recovery = recovering


class TraceOnEveryAck(Model):
    """Adds a trace row for every ACK and expiry, changed or not."""

    def changed(self, snapshot: tuple[int | None, int]) -> bool:
        return True


class TraceAtTheCallTime(Model):
    """Stamps an expiry's trace row with the time of the call that ran it."""

    def trace_time(self, at: int, now: int) -> int:
        return now


class CwndIsSsthreshOnFastRetransmit(Model):
    """Sets cwnd to ssthresh on a fast retransmit, without the three segments."""

    def fast_retransmit_cwnd(self) -> int:
        return self.ssthresh


class PartialAckKeepsRecovery(Model):
    """Stays in fast recovery until every byte sent before it is acknowledged."""

    def __init__(self) -> None:
        super().__init__()
        self.recover = 0

    def on_duplicate(self, now: int) -> list[list[int]]:
        was = self.in_recovery
        out = super().on_duplicate(now)
        if self.in_recovery and not was:
            self.recover = self.nxt
        return out

    def grow(self, newly: int) -> None:
        if self.in_recovery and self.una < self.recover:
            return
        super().grow(newly)


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, RecursionError):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_sender_time_never_goes_back():
    timed = ("send", "ack", "tick", "ackWindow", "enableCongestionControl")
    for case in CASES:
        times = [
            args[-1] for op, args in zip(case["ops"], case["args"], strict=True) if op in timed
        ]
        assert times == sorted(times), case["id"]
