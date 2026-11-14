"""A countdown latch built from a condition variable: wait until every worker has reported.

The latch holds a count. Each worker computes a result, then counts the latch down; the main
thread waits until the count reaches zero. The count is shared state, so it is read and changed
only while holding the condition variable's lock, and the waiting thread checks it again each
time it wakes up.
"""

import threading


class Latch:
    def __init__(self, count: int) -> None:
        self._count = count
        self._changed = threading.Condition()  # a condition variable with a lock of its own

    def count_down(self) -> None:
        with self._changed:  # take the lock
            self._count -= 1
            if self._count == 0:
                self._changed.notify_all()  # wake every waiting thread

    def wait(self) -> None:
        with self._changed:
            while self._count > 0:  # a wake-up says "look again", not "it is done"
                self._changed.wait()  # releases the lock while asleep, retakes it on waking


results: dict[int, int] = {}
latch = Latch(3)


def worker(n: int) -> None:
    results[n] = n * n
    latch.count_down()


for n in (1, 2, 3):
    threading.Thread(target=worker, args=(n,)).start()
latch.wait()
print("every worker reported:", sorted(results.items()))
