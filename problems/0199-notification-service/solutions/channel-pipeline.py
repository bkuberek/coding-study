import heapq
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Protocol

CHANNEL_ORDER = ("EMAIL", "SMS", "PUSH")
MAX_RETRIES = 3
BASE_RETRY_DELAY = 1000
PLACEHOLDER = re.compile(r"\{([^{}]*)\}")


class Channel(Protocol):
    def format(self, address: str, text: str) -> str: ...


class EmailChannel:
    def format(self, address: str, text: str) -> str:
        return f"{address}: {text}"


class TruncatingChannel:
    """A channel with a length limit: a longer text is cut so that it ends in `...` and fits."""

    def __init__(self, limit: int) -> None:
        self._limit = limit

    def format(self, address: str, text: str) -> str:
        if len(text) > self._limit:
            text = text[: self._limit - 3] + "..."
        return f"{address}: {text}"


class Template:
    def __init__(self, body: str) -> None:
        self._body = body

    def render(self, params: list[str]) -> str:
        values = dict(param.split("=", 1) for param in params if "=" in param)
        return PLACEHOLDER.sub(lambda match: values.get(match.group(1), ""), self._body)


class SlidingWindowLimiter:
    """At most `limit` accepted notifications per user in any `window` milliseconds."""

    def __init__(self, limit: int, window: int) -> None:
        self._limit, self._window = limit, window
        self._accepted: dict[str, deque[int]] = {}

    def try_acquire(self, user_id: str, now: int) -> bool:
        times = self._accepted.setdefault(user_id, deque())
        while times and times[0] <= now - self._window:
            times.popleft()
        if len(times) >= self._limit:
            return False
        times.append(now)
        return True


@dataclass(slots=True)
class ChannelState:
    channel: Channel
    limiter: SlidingWindowLimiter | None = None
    outage: tuple[int, int] | None = None
    delivered: int = 0
    retries: int = 0
    dropped: int = 0
    rate_limited: int = 0

    def is_down(self, now: int) -> bool:
        return self.outage is not None and self.outage[0] <= now < self.outage[1]

    def stats(self) -> list[int]:
        return [self.delivered, self.retries, self.dropped, self.rate_limited]


@dataclass(slots=True)
class _Contact:
    address: str
    enabled: bool = True


@dataclass(order=True, slots=True)
class _Attempt:
    due: int
    sequence: int
    user_id: str = field(compare=False)
    channel: str = field(compare=False)
    payload: str = field(compare=False)
    retries_left: int = field(compare=False)


class NotificationService:
    def __init__(self) -> None:
        self._channels = {
            "EMAIL": ChannelState(EmailChannel()),
            "SMS": ChannelState(TruncatingChannel(20)),
            "PUSH": ChannelState(TruncatingChannel(30)),
        }
        self._contacts: dict[tuple[str, str], _Contact] = {}
        self._templates: dict[str, Template] = {}
        self._retries: list[_Attempt] = []  # min-heap by (due, sequence)
        self._sequence = 0
        self._inbox: dict[tuple[str, str], list[str]] = {}

    def add_contact(self, user_id: str, channel: str, address: str) -> bool:
        if channel not in self._channels:
            return False
        self._contacts[(user_id, channel)] = _Contact(address)
        return True

    def set_preference(self, user_id: str, channel: str, enabled: bool) -> bool:
        contact = self._contacts.get((user_id, channel))
        if contact is None:
            return False
        contact.enabled = enabled
        return True

    def add_template(self, template_id: str, body: str) -> bool:
        if template_id in self._templates:
            return False
        self._templates[template_id] = Template(body)
        return True

    def set_rate_limit(self, channel: str, limit: int, window_ms: int) -> bool:
        state = self._channels.get(channel)
        if state is None:
            return False
        state.limiter = SlidingWindowLimiter(limit, window_ms)
        return True

    def set_outage(self, channel: str, start: int, end: int) -> bool:
        state = self._channels.get(channel)
        if state is None:
            return False
        state.outage = (start, end)
        return True

    def send(self, timestamp: int, user_id: str, template_id: str, params: list[str]) -> int:
        self._process_retries(timestamp)
        template = self._templates.get(template_id)
        if template is None:
            return -1
        text = template.render(params)
        accepted = 0
        for name in CHANNEL_ORDER:
            contact = self._contacts.get((user_id, name))
            if contact is None or not contact.enabled:
                continue
            state = self._channels[name]
            if state.limiter is not None and not state.limiter.try_acquire(user_id, timestamp):
                state.rate_limited += 1
                continue
            accepted += 1
            payload = state.channel.format(contact.address, text)
            self._attempt(self._new_attempt(timestamp, user_id, name, payload, MAX_RETRIES))
        return accepted

    def delivered(self, timestamp: int, user_id: str, channel: str) -> list[str]:
        self._process_retries(timestamp)
        return list(self._inbox.get((user_id, channel), []))

    def stats(self, timestamp: int, channel: str) -> list[int]:
        self._process_retries(timestamp)
        state = self._channels.get(channel)
        return [] if state is None else state.stats()

    def _new_attempt(self, due: int, user_id: str, channel: str, payload: str, retries_left: int) -> _Attempt:
        self._sequence += 1
        return _Attempt(due, self._sequence, user_id, channel, payload, retries_left)

    def _attempt(self, attempt: _Attempt) -> None:
        """Deliver now, or schedule the next retry with an exponentially growing delay."""
        state = self._channels[attempt.channel]
        if not state.is_down(attempt.due):
            state.delivered += 1
            self._inbox.setdefault((attempt.user_id, attempt.channel), []).append(attempt.payload)
        elif attempt.retries_left == 0:
            state.dropped += 1
        else:
            retry_number = MAX_RETRIES - attempt.retries_left + 1
            due = attempt.due + BASE_RETRY_DELAY * 2 ** (retry_number - 1)
            retry = self._new_attempt(due, attempt.user_id, attempt.channel, attempt.payload, attempt.retries_left - 1)
            heapq.heappush(self._retries, retry)

    def _process_retries(self, now: int) -> None:
        while self._retries and self._retries[0].due <= now:
            attempt = heapq.heappop(self._retries)
            self._channels[attempt.channel].retries += 1
            self._attempt(attempt)
