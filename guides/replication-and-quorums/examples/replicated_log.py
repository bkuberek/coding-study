"""Replicas that apply the same log of commands, in the same order, end in the same state.

Each replica is a deterministic state machine over one number. The leader's log orders the
commands; a follower that has applied only a prefix of the log is behind, not different. Two
replicas that apply the same commands in different orders disagree.
"""

LOG = ["set 5", "add 3", "double", "add 1"]


def apply(state: int, command: str) -> int:
    op, *arg = command.split()
    if op == "set":
        return int(arg[0])
    if op == "add":
        return state + int(arg[0])
    return state * 2  # double


def run(commands: list[str]) -> int:
    state = 0
    for command in commands:
        state = apply(state, command)
    return state


print("leader, whole log:     ", run(LOG))
print("follower, whole log:   ", run(LOG))
print("follower, first 2 only:", run(LOG[:2]), "(behind, and catches up by applying the rest)")
print("other order:           ", run(["set 5", "double", "add 3", "add 1"]), "(a different state)")
