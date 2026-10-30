"""Keyword Names. Statement: .statements/keyword-names.md. Run: cstudy test keyword-names"""


class Robot:
    def __init__(self, ref: int) -> None:
        pass

    def move(self, steps: int) -> int:
        raise NotImplementedError

    def loop(self, match: int) -> None:
        raise NotImplementedError
