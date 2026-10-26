"""Conformance reference: raises with the given message."""


def fail_with(message: str) -> int:
    raise RuntimeError(message)
