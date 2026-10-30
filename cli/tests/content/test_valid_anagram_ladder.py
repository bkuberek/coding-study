"""valid-anagram's generator must give every ladder size the same kind of input: a sort costs far
less on 3 distinct letters than on 26, so one size with a small alphabet bent the sorting
approach's curve away from n log n in Go and Java."""

import importlib.util
import random

import pytest
import yaml

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0005-valid-anagram"
SEEDS = range(1, 21)
FULL_ALPHABET = 26


def ladder() -> list[int]:
    meta = yaml.safe_load((PROBLEM / "meta.yaml").read_text())
    return meta["perf"]["size_ladder"]


def generator():
    spec = importlib.util.spec_from_file_location(
        "valid_anagram_generator", PROBLEM / "generator.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("size", ladder())
@pytest.mark.parametrize("seed", SEEDS)
def test_every_ladder_size_uses_the_whole_alphabet(size, seed):
    case_input = generator().generate(random.Random(seed), size)
    assert len(set(case_input["s"])) == FULL_ALPHABET
