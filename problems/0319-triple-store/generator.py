"""Seeded operation sequences for triple-store.

`n` is the number of triples recorded. The sequence builds, in this order:

- a chain of n // 5 nodes joined by `next`, closed into a cycle at the end, which is what a path
  walk that recurses once per hop cannot survive and one without a visited set never finishes;
- the rest of the triples at random: `knows`, `likes`, `livesIn` and `worksAt` between n // 3 nodes
  and a few places, each recorded by one of four sources at a time that only grows, with a few
  repeats of the same triple by another source;
- removals of one triple in twenty and a record of some of them again, at later times;
- matches of each shape, joins of two and three patterns, paths from a bound start and to a bound
  end, and answers as of earlier times with their sources, all on names that exist.

validate checks the shape of the calls and the promises of the statement: arities, printable
ASCII, terms that do not start with `?` or end with `+`, and times that never go down.
"""

import random

MAX_TERM_LENGTH = 30
MAX_TIME = 10**15
SOURCES = ["crm", "import", "web", "manual"]
PREDICATES = ["knows", "likes", "livesIn", "worksAt"]
REMOVED_SHARE = 0.05
AGAIN_SHARE = 0.4
REPEAT_SHARE = 0.03
PROBES = 8
ARITY = {
    "add": 3,
    "remove": 3,
    "size": 0,
    "match": 3,
    "query": 2,
    "record": 5,
    "retract": 4,
    "queryAsOf": 3,
    "sourcesAsOf": 3,
}


def generate(rng: random.Random, n: int) -> dict:
    count = max(n, 20)
    chain = count // 5
    nodes = max(count // 3, 10)
    ops: list[str] = ["TripleStore"]
    args: list[list] = [[]]

    def call(op: str, *arguments) -> None:
        ops.append(op)
        args.append(list(arguments))

    clock = _load(rng, call, count, chain, nodes)
    clock = _churn(rng, call, count, chain, nodes, clock)
    _probe_current(rng, call, nodes, chain)
    _probe_history(rng, call, nodes, chain, clock)
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "TripleStore", "the first op must be the constructor"
    assert args[0] == [], "the constructor takes nothing"
    clock = 0
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert ARITY.get(op) == len(arguments), f"bad call {op}{arguments}"
        if op in ("record", "retract"):
            assert 0 <= arguments[-1] <= MAX_TIME, "time out of range"
            assert arguments[-1] >= clock, "times never go down"
            clock = arguments[-1]
            _check_terms(arguments[:3])
        if op in ("add", "remove"):
            _check_terms(arguments)
        if op in ("query", "queryAsOf", "sourcesAsOf"):
            for pattern in arguments[0]:
                assert len(pattern) == 3, "a pattern has three positions"
            assert arguments[1], "name at least one column"


def _check_terms(terms: list) -> None:
    for term in terms:
        assert term and len(term) <= MAX_TERM_LENGTH, "terms are not empty and short"
        assert not term.startswith("?") and not term.endswith("+"), "bad term"
        assert all(33 <= ord(ch) <= 126 for ch in term), "printable ASCII, no space"


def _load(rng, call, count: int, chain: int, nodes: int) -> int:
    clock = 0
    for index in range(chain):
        call("record", f"c{index}", "next", f"c{index + 1}", "import", clock)
        clock += 1
    for _ in range(count - chain):
        subject, predicate, place = _random_triple(rng, nodes)
        call("record", subject, predicate, place, rng.choice(SOURCES), clock)
        if rng.random() < REPEAT_SHARE:
            call("record", subject, predicate, place, rng.choice(SOURCES), clock)
        clock += 1
    call("record", f"c{chain}", "next", "c0", "manual", clock)
    return clock + 1


def _random_triple(rng, nodes: int) -> tuple[str, str, str]:
    predicate = rng.choice(PREDICATES)
    subject = f"n{rng.randrange(nodes)}"
    if predicate == "livesIn":
        return subject, predicate, f"place{rng.randrange(max(nodes // 50, 3))}"
    return subject, predicate, f"n{rng.randrange(nodes)}"


def _churn(rng, call, count: int, chain: int, nodes: int, clock: int) -> int:
    for _ in range(max(int(count * REMOVED_SHARE), 1)):
        index = rng.randrange(chain)
        call("retract", f"c{index}", "next", f"c{index + 1}", clock)
        clock += 1
        if rng.random() < AGAIN_SHARE:
            call("record", f"c{index}", "next", f"c{index + 1}", "web", clock)
            clock += 1
    for _ in range(max(int(count * REMOVED_SHARE), 1)):
        subject, predicate, place = _random_triple(rng, nodes)
        call("retract", subject, predicate, place, clock)
        call("record", subject, predicate, place, "web", clock)
        clock += 1
    return clock


def _probe_current(rng, call, nodes: int, chain: int) -> None:
    call("size")
    call("match", "?", "next", f"c{rng.randrange(1, chain)}")
    for _ in range(PROBES):
        node = f"n{rng.randrange(nodes)}"
        call("match", node, "?", "?")
        call("match", "?", "?", node)
        call("match", node, "knows", "?")
        call("query", [["?a", "knows", node], ["?a", "likes", "?b"]], ["?a", "?b"])
        call(
            "query",
            [[node, "knows", "?b"], ["?b", "knows", "?c"], ["?c", "livesIn", "?d"]],
            ["?d"],
        )
        call("query", [[node, "knows+", "?x"], ["?x", "likes", "?y"]], ["?y"])
    call("query", [["c0", "next+", "?x"]], ["?x"])
    call("query", [["?x", "next+", f"c{chain // 2}"]], ["?x"])
    call("query", [[f"c{chain // 3}", "next+", f"c{chain // 3}"], ["c1", "next", "?y"]], ["?y"])
    call(
        "query",
        [["?p", "livesIn", "place0"], ["?q", "livesIn", "place0"], ["?p", "knows", "?q"]],
        ["?p", "?q"],
    )


def _probe_history(rng, call, nodes: int, chain: int, clock: int) -> None:
    for _ in range(PROBES):
        when = rng.randrange(clock)
        node = f"n{rng.randrange(nodes)}"
        patterns = [[node, "knows", "?b"], ["?b", "likes", "?c"]]
        call("queryAsOf", patterns, ["?b", "?c"], when)
        call("sourcesAsOf", patterns, ["?b", "?c"], when)
        call("queryAsOf", [["?x", "next", f"c{rng.randrange(1, chain)}"]], ["?x"], when)
        call("sourcesAsOf", [["?x", "livesIn", "place1"]], ["?x"], when)
