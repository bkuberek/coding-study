"""Steps against a declared state, each run twice, and two idempotent actions whose sequence is not.

A host is a dictionary from a file's path to its lines. The script appends lines, whatever is
there; the tasks say which lines a file must hold, and change only what differs.
"""

WANTED = [("/etc/hosts", "10.0.0.5 db"), ("/etc/motd", "welcome")]


def append_line(host: dict[str, list[str]], path: str, line: str) -> str:
    host.setdefault(path, []).append(line)
    return "changed"


def ensure_line(host: dict[str, list[str]], path: str, line: str) -> str:
    lines = host.setdefault(path, [])
    if line in lines:
        return "ok"
    lines.append(line)
    return "changed"


for step in (append_line, ensure_line):
    host = {"/etc/hosts": ["127.0.0.1 localhost"]}
    for run in (1, 2):
        statuses = [step(host, path, line) for path, line in WANTED]
        print(f"{step.__name__}, run {run}: {statuses}")
    print(f"  /etc/hosts now holds {host['/etc/hosts']}")


# Two actions on a state of two settings, each idempotent on its own.
def p(state: dict[str, int]) -> str:
    """If x is 1, make y 2."""
    if state["x"] == 1 and state["y"] != 2:
        state["y"] = 2
        return "changed"
    return "ok"


def q(state: dict[str, int]) -> str:
    """Make x 1."""
    if state["x"] != 1:
        state["x"] = 1
        return "changed"
    return "ok"


for action in (p, q):
    state = {"x": 0, "y": 0}
    print(f"{action.__name__} alone, twice: {[action(state), action(state)]}")

state = {"x": 0, "y": 0}
for run in (1, 2, 3):
    statuses = [p(state), q(state)]
    print(f"p then q, run {run}: {statuses} -> {state}")
