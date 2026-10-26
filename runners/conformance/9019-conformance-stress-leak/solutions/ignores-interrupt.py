import time


class StressLeak:
    def __init__(self) -> None:
        pass

    def spin(self) -> None:
        while True:
            time.sleep(0.001)

    def fail(self) -> None:
        raise RuntimeError("leak")

    def noop(self) -> None:
        pass
