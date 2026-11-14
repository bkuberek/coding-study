"""A model-based test of a small key-value store, with random command sequences and shrinking.

The store counts its keys as they come and go. It has a bug that no single call shows: it
remembers every key it has ever stored, to avoid counting one twice, and forgets to forget a key
when it is deleted. A plain dictionary is the model. The test runs the same commands on both and
compares every answer.
"""

import random


class CountingStore:
    def __init__(self):
        self.values, self.seen, self.count = {}, set(), 0

    def put(self, key, value):
        if key not in self.seen:  # bug: "seen" should be "currently stored"
            self.seen.add(key)
            self.count += 1
        self.values[key] = value
        return "ok"

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        del self.values[key]
        self.count -= 1
        return "ok"

    def size(self):
        return self.count


def below(rng: random.Random, n: int) -> int:
    return int(rng.random() * n)


def apply_to_model(model: dict, command: tuple):
    name, *args = command
    if name == "put":
        model[args[0]] = args[1]
        return "ok"
    if name == "get":
        return model.get(args[0])
    if name == "delete":
        del model[args[0]]
        return "ok"
    return len(model)


def valid(commands: list[tuple]) -> bool:
    """The precondition: delete only a key that is stored. Checked on the model."""
    model = {}
    for command in commands:
        if command[0] == "delete" and command[1] not in model:
            return False
        apply_to_model(model, command)
    return True


def generate(rng: random.Random) -> list[tuple]:
    model, commands = {}, []
    for _ in range(1 + below(rng, 12)):
        names = ["put", "get", "size"] + (["delete"] if model else [])
        name = names[below(rng, len(names))]
        key = "ab"[below(rng, 2)] if name != "delete" else sorted(model)[below(rng, len(model))]
        command = {"put": ("put", key, below(rng, 10)), "get": ("get", key),
                   "delete": ("delete", key), "size": ("size",)}[name]
        apply_to_model(model, command)
        commands.append(command)
    return commands


def fails(commands: list[tuple]) -> bool:
    model, store = {}, CountingStore()
    for name, *args in commands:
        if getattr(store, name)(*args) != apply_to_model(model, (name, *args)):
            return True
    return False


def candidates(commands: list[tuple]):
    for i in range(len(commands)):  # drop one command
        yield commands[:i] + commands[i + 1:]
    for i, command in enumerate(commands):  # make one stored value 0
        if command[0] == "put" and command[2] != 0:
            yield commands[:i] + [("put", command[1], 0)] + commands[i + 1:]


def shrink(commands: list[tuple]) -> list[tuple]:
    while True:
        simpler = next((c for c in candidates(commands) if valid(c) and fails(c)), None)
        if simpler is None:
            return commands
        commands = simpler


def show(commands: list[tuple]) -> str:
    return ", ".join(" ".join(map(str, command)) for command in commands)


rng = random.Random(11)
for run in range(1, 201):
    commands = generate(rng)
    if fails(commands):
        print(f"run {run} fails after {len(commands)} commands:\n  {show(commands)}")
        small = shrink(commands)
        print(f"shrunk to {len(small)} commands:\n  {show(small)}")
        model, store = {}, CountingStore()
        answers = [(getattr(store, c[0])(*c[1:]), apply_to_model(model, c)) for c in small]
        print(f"last answer: store says {answers[-1][0]}, model says {answers[-1][1]}")
        break
