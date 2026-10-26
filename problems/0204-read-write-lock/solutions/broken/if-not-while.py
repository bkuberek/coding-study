import threading


class ReadWriteLock:
    def __init__(self) -> None:
        self._changed = threading.Condition()
        self._readers = 0
        self._writing = False
        self._waiting_writers = 0

    def acquire_read(self) -> None:
        with self._changed:
            while self._writing or self._waiting_writers > 0:
                self._changed.wait()
            self._readers += 1

    def release_read(self) -> None:
        with self._changed:
            self._readers -= 1
            if self._readers == 0:
                self._changed.notify_all()

    def acquire_write(self) -> None:
        with self._changed:
            self._waiting_writers += 1
            if self._writing or self._readers > 0:
                self._changed.wait()
            self._waiting_writers -= 1
            self._writing = True

    def release_write(self) -> None:
        with self._changed:
            self._writing = False
            self._changed.notify_all()

    def try_acquire_read(self) -> bool:
        with self._changed:
            if self._writing or self._waiting_writers > 0:
                return False
            self._readers += 1
            return True

    def try_acquire_write(self) -> bool:
        with self._changed:
            if self._writing or self._readers > 0:
                return False
            self._writing = True
            return True
