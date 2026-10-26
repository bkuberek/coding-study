import threading
import time


class ReadWriteLock:
    def __init__(self) -> None:
        self._writers = threading.Lock()
        self._writing = False
        self._readers = 0

    def acquire_read(self) -> None:
        while self._writing:
            time.sleep(0)
        self._readers += 1

    def release_read(self) -> None:
        self._readers -= 1

    def acquire_write(self) -> None:
        self._writers.acquire()
        while self._readers > 0:
            time.sleep(0)
        self._writing = True

    def release_write(self) -> None:
        self._writing = False
        self._writers.release()

    def try_acquire_read(self) -> bool:
        if self._writing:
            return False
        self._readers += 1
        return True

    def try_acquire_write(self) -> bool:
        if not self._writers.acquire(blocking=False):
            return False
        if self._readers > 0:
            self._writers.release()
            return False
        self._writing = True
        return True
