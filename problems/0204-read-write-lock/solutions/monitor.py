import threading


class ReadWriteLock:
    def __init__(self) -> None:
        lock = threading.Lock()
        self._lock = lock
        self._readable = threading.Condition(lock)
        self._writable = threading.Condition(lock)
        self._readers = 0
        self._writing = False
        self._waiting_writers = 0

    def acquire_read(self) -> None:
        with self._lock:
            while self._writing or self._waiting_writers > 0:
                self._readable.wait()
            self._readers += 1

    def release_read(self) -> None:
        with self._lock:
            self._readers -= 1
            if self._readers == 0:
                self._writable.notify()

    def acquire_write(self) -> None:
        with self._lock:
            self._waiting_writers += 1
            while self._writing or self._readers > 0:
                self._writable.wait()
            self._waiting_writers -= 1
            self._writing = True

    def release_write(self) -> None:
        with self._lock:
            self._writing = False
            if self._waiting_writers > 0:
                self._writable.notify()
            else:
                self._readable.notify_all()

    def try_acquire_read(self) -> bool:
        with self._lock:
            if self._writing or self._waiting_writers > 0:
                return False
            self._readers += 1
            return True

    def try_acquire_write(self) -> bool:
        with self._lock:
            if self._writing or self._readers > 0:
                return False
            self._writing = True
            return True
