"""The completion items a session's server wrote, which the page may resolve
(docs/specs/web-ui.md#completion-items).

A server trusts the `data` of an item it is asked to resolve: basedpyright reads the file and the
module to document from it, so an item the page made up would make it document any file it can
read. The page therefore never holds an item's `data`. Each item of an answer reaches the page
with a token of this session in its place, a resolve names the item by that token, and the server
is sent the item as it wrote it.
"""

from collections import deque
from typing import Any, cast

TOKEN_PREFIX = "cstudy-item-"
ANSWERS_KEPT = 4
"""How many of the latest completion answers have items the page may still resolve: an editor
resolves the items of the list it shows, and a request that is answered late is not the latest."""

type Fields = dict[str, Any]


class CompletionItems:
    """The items of the latest completion answers, each under the token the page holds."""

    def __init__(self) -> None:
        self._answers: deque[dict[str, Fields]] = deque(maxlen=ANSWERS_KEPT)
        self._numbered = 0

    def issued(self, result: Any) -> Any:
        """`result`, the server's answer to a completion request, with each item's `data`
        replaced by a token of its own, whether or not the item had any. What is not an item
        passes through."""
        if isinstance(result, list):
            return self._issued_items(cast(list[object], result))
        fields = _fields(result)
        if isinstance(fields.get("items"), list):
            return {**fields, "items": self._issued_items(cast(list[object], fields["items"]))}
        return result

    def named_by(self, item: object) -> tuple[str, Fields] | None:
        """The token in the `data` of `item`, the page's item to resolve, and the item the
        server wrote under it; None if no answer of the latest ones carried such a token."""
        token = _fields(item).get("data")
        if not isinstance(token, str):
            return None
        for answer in reversed(self._answers):
            if token in answer:
                return token, answer[token]
        return None

    def _issued_items(self, items: list[object]) -> list[object]:
        self._numbered += 1
        kept: dict[str, Fields] = {}
        issued: list[object] = []
        for position, item in enumerate(items):
            if isinstance(item, dict):
                written = cast(Fields, item)
                token = f"{TOKEN_PREFIX}{self._numbered}.{position}"
                kept[token] = written
                issued.append({**written, "data": token})
            else:
                issued.append(item)
        self._answers.append(kept)
        return issued


def with_token(token: str | None, resolved: Any) -> Any:
    """The server's resolved item with the token in place of its `data`, so the page can resolve
    it again; anything else the server answered goes back as it is."""
    if token is None or not isinstance(resolved, dict):
        return resolved
    return {**cast(Fields, resolved), "data": token}


def _fields(value: object) -> Fields:
    return cast(Fields, value) if isinstance(value, dict) else {}
