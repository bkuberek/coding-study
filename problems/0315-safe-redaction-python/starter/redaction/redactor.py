"""The class that `cstudy submit` and the tests drive."""


class Redactor:
    def redact(self, text: str, starts: list[int], ends: list[int], labels: list[str]) -> str:
        raise NotImplementedError
