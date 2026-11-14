import threading


class StressGate:
    def __init__(self) -> None:
        self._open = threading.Event()

    def enter(self) -> None:
        self._open.wait()
