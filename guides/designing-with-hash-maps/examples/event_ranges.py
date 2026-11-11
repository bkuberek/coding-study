"""Page views per user, and the views of one user inside a time window.

A hash map finds the user's list in O(1). Views arrive in time order, so each list is already
sorted, and two binary searches find where the window starts and ends: O(log h) for a list of h
views, however long the window is.
"""

from bisect import bisect_left


class ViewLog:
    def __init__(self) -> None:
        self.views: dict[str, list[tuple[int, str]]] = {}

    def record(self, user: str, minute: int, page: str) -> None:
        history = self.views.setdefault(user, [])
        if history and minute < history[-1][0]:
            raise ValueError("views must arrive in time order")
        history.append((minute, page))

    def between(self, user: str, start: int, end: int) -> list[tuple[int, str]]:
        """The user's views with start <= minute < end."""
        history = self.views.get(user, [])
        first = bisect_left(history, start, key=lambda view: view[0])
        stop = bisect_left(history, end, key=lambda view: view[0])
        return history[first:stop]


log = ViewLog()
for minute, page in ((3, "home"), (8, "pricing"), (8, "signup"), (15, "docs"), (42, "home")):
    log.record("ana", minute, page)
log.record("ben", 5, "home")
print("ana, minutes 5 to 15:", log.between("ana", 5, 15))
print("ana, minutes 8 to 9:", log.between("ana", 8, 9))
print("ana, minutes 16 to 40:", log.between("ana", 16, 40))
print("cy, who never visited:", log.between("cy", 0, 60))
