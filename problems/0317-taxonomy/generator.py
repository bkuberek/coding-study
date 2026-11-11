"""Seeded operation sequences for taxonomy.

`n` is the number of concepts in the main scheme `a`. The sequence builds, in this order:

- scheme `a`: n concepts in a random hierarchy, one in ten with a second parent, one in ten with
  an alternative label;
- scheme `d`: a chain of n // 2 concepts, which is what a solution that recurses once per level
  cannot survive, questioned only through the calls whose answers stay small (the full list of
  ancestors is asked once);
- scheme `b`: n // 4 concepts, with exact matches to scheme `a` that map several concepts to one
  and one concept to several;
- a mix of links (some of which would make a cycle), lowest common ancestors, label searches, facet
  expansions, renames, replacements (some of which are refused) and translations of a sample of
  concepts, all of them on ids that exist, so that the answers depend on the structure.

validate checks the shape of the calls and the promises of the statement: id and label lengths,
printable ASCII, no space in an id and the limit on the number of calls.
"""

import random

MAX_CALLS = 300_000
MAX_ID_LENGTH = 20
MAX_LABEL_LENGTH = 40
SECOND_PARENT_SHARE = 0.1
ALT_LABEL_SHARE = 0.1
SAMPLE = 1000
PROBES = 10
CHAIN_LINKS = 3
ARITY = {
    "addConcept": 3,
    "addBroader": 2,
    "prefLabel": 1,
    "broader": 1,
    "narrower": 1,
    "ancestors": 1,
    "descendants": 1,
    "roots": 0,
    "lowestCommonAncestors": 2,
    "addAltLabel": 2,
    "altLabels": 1,
    "findByLabel": 1,
    "expand": 1,
    "rename": 2,
    "removeBroader": 2,
    "deprecate": 2,
    "resolve": 1,
    "addExactMatch": 2,
    "translate": 2,
    "unmapped": 2,
}


def generate(rng: random.Random, n: int) -> dict:
    main = max(n, 8)
    chain = main // 2
    second = main // 4
    ops: list[str] = ["Taxonomy"]
    args: list[list] = [[]]

    def call(op: str, *arguments) -> None:
        ops.append(op)
        args.append(list(arguments))

    _scheme(rng, call, "a", main, "Concept {}", True)
    _scheme(rng, call, "b", second, "Concepto {}", False)
    _chain(call, chain)
    _alt_labels(rng, call, main)
    _matches(rng, call, main, second)
    _probes(rng, call, main, second, chain)
    _changes(rng, call, main, second)
    _sample_translations(rng, call, main, second)
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert len(ops) <= MAX_CALLS, "too many calls"
    assert ops[0] == "Taxonomy", "the first op must be the constructor"
    assert args[0] == [], "the constructor takes nothing"
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert ARITY.get(op) == len(arguments), f"bad call {op}{arguments}"
        for value in arguments:
            for text in value if isinstance(value, list) else [value]:
                assert isinstance(text, str), "arguments are text or lists of text"
                assert all(32 <= ord(ch) <= 126 for ch in text), "printable ASCII only"
        if op in ("addConcept", "translate", "unmapped"):
            _check_ids(op, arguments)


def _check_ids(op: str, arguments: list) -> None:
    if op == "addConcept":
        assert arguments[0] and " " not in arguments[0], "ids are not empty and hold no space"
        assert len(arguments[0]) <= MAX_ID_LENGTH, "id too long"
        assert len(arguments[1]) <= MAX_LABEL_LENGTH, "label too long"
        assert all(" " not in parent for parent in arguments[2]), "ids hold no space"
    else:
        assert all(" " not in concept for concept in arguments[0]), "ids hold no space"


def _scheme(rng, call, scheme: str, count: int, label: str, extra_parents: bool) -> None:
    for index in range(count):
        parents: list[str] = []
        if index:
            parents.append(f"{scheme}:c{rng.randrange(index)}")
            if extra_parents and index > 1 and rng.random() < SECOND_PARENT_SHARE:
                other = f"{scheme}:c{rng.randrange(index)}"
                if other not in parents:
                    parents.append(other)
        call("addConcept", f"{scheme}:c{index}", label.format(index), parents)


def _chain(call, length: int) -> None:
    for index in range(length):
        call("addConcept", f"d:k{index}", f"Link {index}", [f"d:k{index - 1}"] if index else [])


def _alt_labels(rng, call, count: int) -> None:
    for index in range(count):
        if rng.random() < ALT_LABEL_SHARE:
            call("addAltLabel", f"a:c{index}", f"  Synonym {index % 100} ")


def _matches(rng, call, main: int, second: int) -> None:
    for index in range(second):
        call("addExactMatch", f"b:c{index}", f"a:c{rng.randrange(main)}")
        if rng.random() < SECOND_PARENT_SHARE:
            call("addExactMatch", f"b:c{index}", f"a:c{rng.randrange(main)}")


def _probes(rng, call, main: int, second: int, chain: int) -> None:
    call("roots")
    call("ancestors", f"d:k{chain - 1}")
    call("descendants", "d:k0")
    call("lowestCommonAncestors", f"d:k{chain - 1}", f"d:k{chain // 2}")
    for _ in range(CHAIN_LINKS):
        call("addBroader", "d:k0", f"d:k{chain - 1}")
    call("descendants", "a:c0")
    call("expand", ["concept 0"])
    call("expand", ["SYNONYM 7 ", "concept   3"])
    for _ in range(PROBES):
        first, other = f"a:c{rng.randrange(main)}", f"a:c{rng.randrange(main)}"
        call("ancestors", first)
        call("lowestCommonAncestors", first, other)
        call("addBroader", first, other)
        call("addBroader", other, first)
        call("findByLabel", f"synonym {rng.randrange(100)}")
        call("expand", [f"Concept {rng.randrange(main)}"])
        call("descendants", f"b:c{rng.randrange(second)}")


def _changes(rng, call, main: int, second: int) -> None:
    for _ in range(PROBES):
        old, new = rng.randrange(1, main), rng.randrange(1, main)
        call("rename", f"a:c{new}", f"Renamed {new}")
        call("deprecate", f"a:c{old}", f"a:c{new}")
        call("resolve", f"a:c{old}")
        call("ancestors", f"a:c{old}")
        call("findByLabel", f"concept {old}")
    for _ in range(PROBES):
        call("removeBroader", f"b:c{rng.randrange(1, second)}", f"b:c{rng.randrange(second)}")
        call("deprecate", f"b:c{rng.randrange(1, second)}", f"b:c{rng.randrange(second)}")


def _sample_translations(rng, call, main: int, second: int) -> None:
    sample = min(SAMPLE, main)
    mine = [f"a:c{rng.randrange(main)}" for _ in range(sample)]
    theirs = [f"b:c{rng.randrange(second)}" for _ in range(min(SAMPLE, second))]
    call("translate", mine, "b")
    call("unmapped", mine, "b")
    call("translate", theirs, "a")
    call("unmapped", theirs, "a")
    call("translate", mine + theirs, "")
