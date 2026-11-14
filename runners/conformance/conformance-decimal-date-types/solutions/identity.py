"""Conformance reference: every echo method returns its decimal or date argument unchanged."""

from datetime import date
from decimal import Decimal


class TypeEcho:
    def __init__(self, label: str) -> None:
        pass

    def echo_decimal(self, value: Decimal) -> Decimal:
        return value

    def echo_date(self, value: date) -> date:
        return value

    def echo_decimal_array(self, value: list[Decimal]) -> list[Decimal]:
        return value

    def echo_date_array(self, value: list[date]) -> list[date]:
        return value

    def echo_decimal_matrix(self, value: list[list[Decimal]]) -> list[list[Decimal]]:
        return value

    def echo_date_matrix(self, value: list[list[date]]) -> list[list[date]]:
        return value

    def echo_decimal_list(self, value: list[Decimal]) -> list[Decimal]:
        return value

    def echo_date_list(self, value: list[date]) -> list[date]:
        return value
