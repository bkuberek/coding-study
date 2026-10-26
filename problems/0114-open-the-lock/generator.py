"""Seeded dead ends and targets for open-the-lock.

`n` is the number of dead ends (1 to 5000). The target is a random setting; the dead ends are
distinct random settings other than the target. On some inputs the dead ends also box in the
target (all eight neighbors), box in the start, or include the start, so the answer is -1; on
some the target is the start itself. With thousands of dead ends, the remaining settings break
into pockets and long detours.
"""

import random

MAX_DEADENDS = 5000
START = "0000"


def _neighbors(setting: str) -> list[str]:
    result = []
    for wheel in range(4):
        digit = int(setting[wheel])
        for turn in (1, 9):
            result.append(setting[:wheel] + str((digit + turn) % 10) + setting[wheel + 1 :])
    return result


def generate(rng: random.Random, n: int) -> dict:
    count = min(max(n, 1), MAX_DEADENDS)
    kind = rng.random()
    target = START if kind < 0.03 else f"{rng.randrange(10**4):04d}"
    forced: list[str] = []
    if kind > 0.97:
        forced = [START] if target != START else []
    elif kind > 0.92:
        forced = [s for s in _neighbors(target) if s != START] if target != START else []
    elif kind > 0.87:
        forced = [s for s in _neighbors(START) if s != target]
    deadends = forced[:count]
    chosen = set(deadends)
    while len(deadends) < count:
        setting = f"{rng.randrange(10**4):04d}"
        if setting != target and setting not in chosen:
            chosen.add(setting)
            deadends.append(setting)
    rng.shuffle(deadends)
    return {"deadends": deadends, "target": target}


def validate(case_input: dict) -> None:
    deadends, target = case_input["deadends"], case_input["target"]
    assert 1 <= len(deadends) <= MAX_DEADENDS, "dead end count out of range"
    assert len(set(deadends)) == len(deadends), "dead ends repeat"
    for setting in [*deadends, target]:
        assert len(setting) == 4 and setting.isdigit(), "a setting is not four digits"
    assert target not in deadends, "the target is a dead end"
