"""Two threads that take two locks in opposite orders deadlock; one order for everyone does not.

In the first run, T1 takes R1 then R2 and T2 takes R2 then R1. A barrier makes each thread wait
until the other holds its first lock, so the deadlock happens on every run. The second lock is
tried with a timeout, so the program reports the deadlock instead of hanging, and a second barrier
keeps both first locks held until both tries have ended. In the second run both threads take the
locks in the same order, R1 before R2, and both finish.
"""

import threading


def opposite_orders() -> dict[str, bool]:
    r1, r2 = threading.Lock(), threading.Lock()
    both_hold, both_tried = threading.Barrier(2), threading.Barrier(2)
    got: dict[str, bool] = {}

    def task(name: str, first: threading.Lock, second: threading.Lock) -> None:
        with first:
            both_hold.wait()
            got[name] = second.acquire(timeout=0.5)
            both_tried.wait()
            if got[name]:
                second.release()

    threads = [
        threading.Thread(target=task, args=("T1", r1, r2)),
        threading.Thread(target=task, args=("T2", r2, r1)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return got


def one_order() -> list[str]:
    locks = {"R1": threading.Lock(), "R2": threading.Lock()}
    finished: list[str] = []

    def task(name: str, wanted: list[str]) -> None:
        first, second = sorted(wanted)  # every thread takes R1 before R2
        with locks[first], locks[second]:
            finished.append(name)

    threads = [
        threading.Thread(target=task, args=("T1", ["R1", "R2"])),
        threading.Thread(target=task, args=("T2", ["R2", "R1"])),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return sorted(finished)


got = opposite_orders()
print(f"opposite orders: T1 got R2: {got['T1']}, T2 got R1: {got['T2']}")
print(f"one order, R1 before R2: finished {one_order()}")
