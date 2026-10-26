"""Conformance reference: loops forever on a negative value."""


def wait_for(value: int) -> int:
    while value < 0:
        pass
    return value
