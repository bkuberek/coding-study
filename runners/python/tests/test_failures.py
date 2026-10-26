from collections.abc import Callable

from cs_runner.failures import MAX_TRACE_LINES, describe

USER_FILE = "/workspace/python/practice/user_code.py"
RECURSIVE_SOURCE = """
def recurse(depth):
    if depth == 0:
        raise ValueError("bottom")
    return recurse(depth - 1)
"""


def user_function(source: str, name: str) -> Callable[..., object]:
    namespace: dict[str, object] = {}
    exec(compile(source, USER_FILE, "exec"), namespace)
    function = namespace[name]
    assert callable(function)
    return function


def raised_by(function: Callable[[], object]) -> BaseException:
    try:
        function()
    except BaseException as error:
        return error
    raise AssertionError("expected an exception")


def recursion_error(depth: int) -> BaseException:
    recurse = user_function(RECURSIVE_SOURCE, "recurse")
    return raised_by(lambda: recurse(depth))


def test_names_the_exception_type():
    assert describe(recursion_error(0), USER_FILE).type == "ValueError"


def test_keeps_the_exception_message():
    assert describe(recursion_error(0), USER_FILE).message == "bottom"


def test_trace_lists_user_frames_only():
    assert describe(recursion_error(0), USER_FILE).trace == "user_code.py:4 in recurse"


def test_trace_keeps_the_innermost_frames():
    lines = describe(recursion_error(20), USER_FILE).trace.splitlines()
    assert lines == ["user_code.py:5 in recurse"] * (MAX_TRACE_LINES - 1) + [
        "user_code.py:4 in recurse"
    ]


def test_trace_points_at_a_syntax_error_in_the_user_file():
    error = raised_by(lambda: compile("x = (\n", USER_FILE, "exec"))
    assert describe(error, USER_FILE).trace == "user_code.py:1"


def test_trace_is_empty_without_user_frames():
    assert describe(raised_by(lambda: int("x")), USER_FILE).trace == ""
