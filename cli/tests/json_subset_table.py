"""What a JSON subset holds, one table for both of its implementations: the mock server's, which
matches a route on a request body, and the grader's, which narrows a log assertion. The mock server
runs alone in its container, on the standard library, so it cannot share the grader's code; this
table keeps the two the same."""

from typing import Any

CONTAINED: list[tuple[Any, Any]] = [
    ({"model": "m", "stream": True}, {"stream": True}),
    ({"a": {"b": 1, "c": 2}}, {"a": {"b": 1}}),
    ({"a": 1}, {}),
    ([{"role": "user", "content": "hi"}], [{"role": "user"}]),
    (1, 1.0),
    ("text", "text"),
    (None, None),
    (False, False),
]
NOT_CONTAINED: list[tuple[Any, Any]] = [
    ({"stream": False}, {"stream": True}),
    ({}, {"stream": True}),
    ({"stream": 1}, {"stream": True}),
    ({"n": True}, {"n": 1}),
    ({"n": 0}, {"n": False}),
    ([1, 2], [1]),
    ([1], [1, 2]),
    ({"a": [1]}, {"a": 1}),
    ("1", 1),
    (None, {}),
    ({"a": None}, {"a": "null"}),
]
