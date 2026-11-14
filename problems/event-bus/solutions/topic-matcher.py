from collections import deque
from dataclasses import dataclass, field
from functools import cache

NO_SUBSCRIBER = "-"


@dataclass(frozen=True, slots=True)
class TopicPattern:
    """Dot-separated segments; `*` matches exactly one segment and `#` zero or more."""

    segments: tuple[str, ...]

    @classmethod
    def parse(cls, text: str) -> "TopicPattern":
        return cls(tuple(text.split(".")))

    def matches(self, topic: str) -> bool:
        pattern, words = self.segments, topic.split(".")

        @cache
        def match(p: int, w: int) -> bool:
            if p == len(pattern):
                return w == len(words)
            if pattern[p] == "#":
                return match(p + 1, w) or (w < len(words) and match(p, w + 1))
            if w == len(words):
                return False
            return pattern[p] in ("*", words[w]) and match(p + 1, w + 1)

        return match(0, 0)


@dataclass(frozen=True, slots=True)
class Event:
    topic: str
    payload: str

    def render(self) -> str:
        return f"{self.topic}:{self.payload}"


@dataclass(slots=True)
class Subscriber:
    subscriber_id: str
    patterns: dict[str, TopicPattern] = field(default_factory=dict)  # subscription order
    inbox: deque[Event] = field(default_factory=deque)
    limit: int | None = None

    def wants(self, topic: str) -> bool:
        return any(pattern.matches(topic) for pattern in self.patterns.values())

    def offer(self, event: Event) -> bool:
        """Accept the event unless the inbox is full."""
        if self.limit is not None and len(self.inbox) >= self.limit:
            return False
        self.inbox.append(event)
        return True

    def take(self, count: int) -> list[str]:
        taken = []
        while self.inbox and len(taken) < count:
            taken.append(self.inbox.popleft().render())
        return taken


class DeadLetterQueue:
    def __init__(self) -> None:
        self._letters: deque[str] = deque()

    def add(self, subscriber_id: str, event: Event) -> None:
        self._letters.append(f"{subscriber_id}:{event.render()}")

    def drain(self, count: int) -> list[str]:
        drained = []
        while self._letters and len(drained) < count:
            drained.append(self._letters.popleft())
        return drained


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, Subscriber] = {}
        self._dead_letters = DeadLetterQueue()

    def subscribe(self, subscriber_id: str, pattern: str) -> bool:
        subscriber = self._subscribers.setdefault(subscriber_id, Subscriber(subscriber_id))
        if pattern in subscriber.patterns:
            return False
        subscriber.patterns[pattern] = TopicPattern.parse(pattern)
        return True

    def unsubscribe(self, subscriber_id: str, pattern: str) -> bool:
        subscriber = self._subscribers.get(subscriber_id)
        if subscriber is None or pattern not in subscriber.patterns:
            return False
        del subscriber.patterns[pattern]
        return True

    def publish(self, topic: str, payload: str) -> int:
        event = Event(topic, payload)
        interested = sorted(
            (subscriber for subscriber in self._subscribers.values() if subscriber.wants(topic)),
            key=lambda subscriber: subscriber.subscriber_id,
        )
        if not interested:
            self._dead_letters.add(NO_SUBSCRIBER, event)
        delivered = 0
        for subscriber in interested:
            if subscriber.offer(event):
                delivered += 1
            else:
                self._dead_letters.add(subscriber.subscriber_id, event)
        return delivered

    def poll(self, subscriber_id: str, max_events: int) -> list[str]:
        subscriber = self._subscribers.get(subscriber_id)
        return [] if subscriber is None else subscriber.take(max_events)

    def pending(self, subscriber_id: str) -> int:
        subscriber = self._subscribers.get(subscriber_id)
        return -1 if subscriber is None else len(subscriber.inbox)

    def set_inbox_limit(self, subscriber_id: str, limit: int) -> bool:
        subscriber = self._subscribers.get(subscriber_id)
        if subscriber is None:
            return False
        subscriber.limit = limit
        return True

    def dead_letters(self, max_events: int) -> list[str]:
        return self._dead_letters.drain(max_events)
