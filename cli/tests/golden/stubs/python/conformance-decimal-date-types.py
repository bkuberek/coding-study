"""Conformance: decimal and date round-trip. Statement: .statements/conformance-decimal-date-types.md. Run: cstudy test conformance-decimal-date-types"""

from datetime import date
from decimal import Decimal


class TypeEcho:
    def __init__(self, label: str) -> None:
        pass

    def echo_decimal(self, value: Decimal) -> Decimal:
        raise NotImplementedError

    def echo_date(self, value: date) -> date:
        raise NotImplementedError

    def echo_decimal_array(self, value: list[Decimal]) -> list[Decimal]:
        raise NotImplementedError

    def echo_date_array(self, value: list[date]) -> list[date]:
        raise NotImplementedError

    def echo_decimal_matrix(self, value: list[list[Decimal]]) -> list[list[Decimal]]:
        raise NotImplementedError

    def echo_date_matrix(self, value: list[list[date]]) -> list[list[date]]:
        raise NotImplementedError

    def echo_decimal_list(self, value: list[Decimal]) -> list[Decimal]:
        raise NotImplementedError

    def echo_date_list(self, value: list[date]) -> list[date]:
        raise NotImplementedError
