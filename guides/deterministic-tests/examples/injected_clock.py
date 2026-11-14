"""A session that expires after 15 minutes of inactivity, tested without waiting 15 minutes.

The session asks a clock function for the time instead of reading the system clock itself. In
production that function is time.monotonic; in the test it is a manual clock that moves only when
the test moves it, so the test is exact, repeatable and instant.
"""

import time


class ManualClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class Session:
    def __init__(self, idle_limit: float, clock=time.monotonic):
        self.idle_limit, self.clock = idle_limit, clock
        self.last_seen = clock()

    def touch(self) -> None:
        self.last_seen = self.clock()

    def expired(self) -> bool:
        return self.clock() - self.last_seen >= self.idle_limit


started = time.monotonic()
clock = ManualClock()
session = Session(idle_limit=15 * 60, clock=clock)
checks = []
clock.advance(899)
checks.append(("after 899 s", session.expired(), False))
clock.advance(1)
checks.append(("after 900 s", session.expired(), True))
session.touch()
clock.advance(600)
checks.append(("600 s after a touch", session.expired(), False))
for label, actual, expected in checks:
    print(f"{label:<20} expired={actual!s:<5} {'ok' if actual == expected else 'WRONG'}")
print("real time spent under one second:", time.monotonic() - started < 1)
