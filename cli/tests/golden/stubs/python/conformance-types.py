"""Conformance: every DSL type round-trips. Statement: .statements/conformance-types.md. Run: cstudy test conformance-types"""

from datetime import date
from decimal import Decimal

from cs_support import GraphNode, ListNode, TreeNode


class TypeEcho:
    def __init__(self, label: str) -> None:
        pass

    def echo_int(self, value: int) -> int:
        raise NotImplementedError

    def echo_long(self, value: int) -> int:
        raise NotImplementedError

    def echo_double(self, value: float) -> float:
        raise NotImplementedError

    def echo_bool(self, value: bool) -> bool:
        raise NotImplementedError

    def echo_string(self, value: str) -> str:
        raise NotImplementedError

    def echo_char(self, value: str) -> str:
        raise NotImplementedError

    def echo_int_array(self, value: list[int]) -> list[int]:
        raise NotImplementedError

    def echo_long_array(self, value: list[int]) -> list[int]:
        raise NotImplementedError

    def echo_double_array(self, value: list[float]) -> list[float]:
        raise NotImplementedError

    def echo_bool_array(self, value: list[bool]) -> list[bool]:
        raise NotImplementedError

    def echo_char_array(self, value: list[str]) -> list[str]:
        raise NotImplementedError

    def echo_string_array(self, value: list[str]) -> list[str]:
        raise NotImplementedError

    def echo_int_matrix(self, value: list[list[int]]) -> list[list[int]]:
        raise NotImplementedError

    def echo_long_matrix(self, value: list[list[int]]) -> list[list[int]]:
        raise NotImplementedError

    def echo_double_matrix(self, value: list[list[float]]) -> list[list[float]]:
        raise NotImplementedError

    def echo_bool_matrix(self, value: list[list[bool]]) -> list[list[bool]]:
        raise NotImplementedError

    def echo_char_matrix(self, value: list[list[str]]) -> list[list[str]]:
        raise NotImplementedError

    def echo_string_matrix(self, value: list[list[str]]) -> list[list[str]]:
        raise NotImplementedError

    def echo_int_list(self, value: list[int]) -> list[int]:
        raise NotImplementedError

    def echo_long_list(self, value: list[int]) -> list[int]:
        raise NotImplementedError

    def echo_double_list(self, value: list[float]) -> list[float]:
        raise NotImplementedError

    def echo_bool_list(self, value: list[bool]) -> list[bool]:
        raise NotImplementedError

    def echo_char_list(self, value: list[str]) -> list[str]:
        raise NotImplementedError

    def echo_string_list(self, value: list[str]) -> list[str]:
        raise NotImplementedError

    def echo_int_array_list(self, value: list[list[int]]) -> list[list[int]]:
        raise NotImplementedError

    def echo_int_list_list(self, value: list[list[int]]) -> list[list[int]]:
        raise NotImplementedError

    def echo_string_list_list(self, value: list[list[str]]) -> list[list[str]]:
        raise NotImplementedError

    def echo_int_list_list_list(
        self, value: list[list[list[int]]]
    ) -> list[list[list[int]]]:
        raise NotImplementedError

    def echo_list_node(self, value: ListNode | None) -> ListNode | None:
        raise NotImplementedError

    def echo_tree_node(self, value: TreeNode | None) -> TreeNode | None:
        raise NotImplementedError

    def echo_graph_node(self, value: GraphNode | None) -> GraphNode | None:
        raise NotImplementedError

    def echo_list_node_array(
        self, value: list[ListNode | None]
    ) -> list[ListNode | None]:
        raise NotImplementedError

    def echo_tree_node_list(
        self, value: list[TreeNode | None]
    ) -> list[TreeNode | None]:
        raise NotImplementedError

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

    def noop(self, value: int) -> None:
        raise NotImplementedError
