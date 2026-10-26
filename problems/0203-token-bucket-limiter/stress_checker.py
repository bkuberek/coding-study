"""Token accounting invariants for the token-bucket-limiter stress cases.

Both read only the run record. A granted request is a `tryAcquire` whose output is `true`; its
second argument is the number of tokens it took.
"""


def check(name: str, scenario: dict, run: dict) -> str | None:
    """Return None when the run record satisfies invariant `name`, else a one-line reason."""
    if name == "conserved":
        return _conserved(run)
    if name == "burst":
        return _burst(run)
    return f"unknown invariant {name!r}"


def _conserved(run: dict) -> str | None:
    """Granted plus remaining tokens equal the capacity plus everything refilled up to the latest timestamp.

    The bucket starts full at timestamp 0, and the scenario keeps it far below its capacity after
    setup, so no refill is ever cut off and every elapsed second adds exactly `refillPerSecond`.
    """
    capacity, rate = run["setup"][0]["args"]
    latest = max(op["args"][0] for op in _calls(run))
    granted = _granted(run)
    remaining = run["final"][-1]["output"]
    supplied = capacity + rate * latest
    if granted + remaining == supplied:
        return None
    return (
        f"granted {granted} + remaining {remaining} = {granted + remaining} tokens, but the bucket "
        f"held {capacity} and refilled {rate * latest} by timestamp {latest}"
    )


def _burst(run: dict) -> str | None:
    """Requests at one instant on a full bucket get exactly its capacity."""
    capacity = run["setup"][0]["args"][0]
    granted = _granted(run)
    if granted == capacity:
        return None
    return f"granted {granted} tokens at one instant from a full bucket of {capacity}"


def _calls(run: dict) -> list[dict]:
    """Every method call after the constructor, in record order."""
    worker_ops = [op for worker in run["workers"] for op in worker["ops"]]
    calls = [*run["setup"][1:], *worker_ops, *run["final"]]
    return [op for op in calls if op["op"] in ("tryAcquire", "available")]


def _granted(run: dict) -> int:
    return sum(op["args"][1] for op in _calls(run) if op["op"] == "tryAcquire" and op["output"] is True)
