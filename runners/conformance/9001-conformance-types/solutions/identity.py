"""Conformance reference: every echo method returns its argument unchanged."""

from cs_support import GraphNode, ListNode, TreeNode


class TypeEcho:
    def __init__(self, label: str) -> None:
        pass

    def echo_int(self, value: int) -> int:
        return value

    def echo_long(self, value: int) -> int:
        return value

    def echo_double(self, value: float) -> float:
        return value

    def echo_bool(self, value: bool) -> bool:
        return value

    def echo_string(self, value: str) -> str:
        return value

    def echo_char(self, value: str) -> str:
        return value

    def echo_int_array(self, value: list[int]) -> list[int]:
        return value

    def echo_long_array(self, value: list[int]) -> list[int]:
        return value

    def echo_double_array(self, value: list[float]) -> list[float]:
        return value

    def echo_bool_array(self, value: list[bool]) -> list[bool]:
        return value

    def echo_char_array(self, value: list[str]) -> list[str]:
        return value

    def echo_string_array(self, value: list[str]) -> list[str]:
        return value

    def echo_int_matrix(self, value: list[list[int]]) -> list[list[int]]:
        return value

    def echo_long_matrix(self, value: list[list[int]]) -> list[list[int]]:
        return value

    def echo_double_matrix(self, value: list[list[float]]) -> list[list[float]]:
        return value

    def echo_bool_matrix(self, value: list[list[bool]]) -> list[list[bool]]:
        return value

    def echo_char_matrix(self, value: list[list[str]]) -> list[list[str]]:
        return value

    def echo_string_matrix(self, value: list[list[str]]) -> list[list[str]]:
        return value

    def echo_int_list(self, value: list[int]) -> list[int]:
        return value

    def echo_long_list(self, value: list[int]) -> list[int]:
        return value

    def echo_double_list(self, value: list[float]) -> list[float]:
        return value

    def echo_bool_list(self, value: list[bool]) -> list[bool]:
        return value

    def echo_char_list(self, value: list[str]) -> list[str]:
        return value

    def echo_string_list(self, value: list[str]) -> list[str]:
        return value

    def echo_int_array_list(self, value: list[list[int]]) -> list[list[int]]:
        return value

    def echo_int_list_list(self, value: list[list[int]]) -> list[list[int]]:
        return value

    def echo_string_list_list(self, value: list[list[str]]) -> list[list[str]]:
        return value

    def echo_int_list_list_list(
        self, value: list[list[list[int]]]
    ) -> list[list[list[int]]]:
        return value

    def echo_list_node(self, value: ListNode | None) -> ListNode | None:
        return value

    def echo_tree_node(self, value: TreeNode | None) -> TreeNode | None:
        return value

    def echo_graph_node(self, value: GraphNode | None) -> GraphNode | None:
        return value

    def echo_list_node_array(
        self, value: list[ListNode | None]
    ) -> list[ListNode | None]:
        return value

    def echo_tree_node_list(
        self, value: list[TreeNode | None]
    ) -> list[TreeNode | None]:
        return value

    def noop(self, value: int) -> None:
        return None
