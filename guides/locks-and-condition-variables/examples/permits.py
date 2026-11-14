"""A counting semaphore with 2 permits lets at most 2 of 6 workers in at a time.

Each worker takes a permit, records how many workers are inside, works briefly and gives the
permit back. The largest number seen inside is checked against the limit; how many actually
overlap depends on timing, so the program prints only whether the limit held.
"""

import threading
import time

PERMITS = 2
permits = threading.Semaphore(PERMITS)
count_lock = threading.Lock()
inside = 0
most_inside = 0


def worker() -> None:
    global inside, most_inside
    with permits:  # acquire: take a permit, or wait for one; release on the way out
        with count_lock:
            inside += 1
            most_inside = max(most_inside, inside)
        time.sleep(0.01)
        with count_lock:
            inside -= 1


workers = [threading.Thread(target=worker) for _ in range(6)]
for thread in workers:
    thread.start()
for thread in workers:
    thread.join()
print(f"6 workers, {PERMITS} permits: never more than {PERMITS} inside: {most_inside <= PERMITS}")

one = threading.Semaphore(1)
print("first acquire:", one.acquire())
print("second acquire without waiting:", one.acquire(blocking=False))
one.release()
print("after a release:", one.acquire(blocking=False))
