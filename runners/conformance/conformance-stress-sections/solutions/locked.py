import threading


class StressMutex:
    def __init__(self) -> None:
        self._mutex = threading.Lock()

    def lock(self) -> None:
        self._mutex.acquire()

    def unlock(self) -> None:
        self._mutex.release()
