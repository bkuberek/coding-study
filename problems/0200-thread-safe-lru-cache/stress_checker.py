"""Value invariant for the thread-safe-lru-cache stress cases.

Every value the stress cases put encodes its key: `value // 1_000_000 == key`.
"""

KEY_STRIDE = 1_000_000
MISS = -1
SHOWN = 3


def check(name: str, scenario: dict, run: dict) -> str | None:
    """Return None when the run record satisfies invariant `name`, else a one-line reason."""
    if name == "values-match-keys":
        return _values_match_keys(run)
    return f"unknown invariant {name!r}"


def _values_match_keys(run: dict) -> str | None:
    """A hit returns a value that some worker put for exactly that key."""
    ops = _ops(run)
    put = {(op["args"][0], op["args"][1]) for op in ops if op["op"] == "put"}
    wrong = [
        f"get({op['args'][0]}) returned {op['output']}"
        for op in ops
        if op["op"] == "get" and op["output"] != MISS and (op["args"][0], op["output"]) not in put
    ]
    if not wrong:
        return None
    shown = ", ".join(wrong[:SHOWN])
    more = f" and {len(wrong) - SHOWN} more" if len(wrong) > SHOWN else ""
    return f"{shown}{more}: never put for that key (values encode their key as value // {KEY_STRIDE})"


def _ops(run: dict) -> list[dict]:
    worker_ops = [op for worker in run["workers"] for op in worker["ops"]]
    return [*run["setup"], *worker_ops, *run["final"]]
