class StressFailer:
    def __init__(self) -> None:
        pass

    def step(self, index: int) -> int:
        if index == 100:
            raise RuntimeError("failed at 100")
        return index
