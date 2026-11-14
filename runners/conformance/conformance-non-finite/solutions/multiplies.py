"""Conformance reference: 1e308 * 10 overflows to infinity, an invalid double output."""


def scale(value: float, factor: float) -> float:
    return value * factor
