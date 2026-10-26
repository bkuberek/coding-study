from pathlib import Path

import pytest

from coding_study.adapters.content_code_loader import ContentCodeLoader
from coding_study.domain.errors import ContentError

GENERATOR = """\
import random


def generate(rng: random.Random, n: int) -> dict:
    return {"nums": [rng.randrange(100) for _ in range(n)], "pair": (1, 2)}


def validate(case_input: dict) -> None:
    assert len(case_input["nums"]) < 5, "too many numbers"
"""


@pytest.fixture
def loader(tmp_path: Path) -> ContentCodeLoader:
    return ContentCodeLoader(tmp_path)


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / "problems" / "0001-two-sum" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_generate_is_deterministic_per_seed(loader, tmp_path):
    generator = loader.generator(write(tmp_path, "generator.py", GENERATOR))
    assert generator.generate(3, 7) == generator.generate(3, 7)


def test_generate_uses_the_seed(loader, tmp_path):
    generator = loader.generator(write(tmp_path, "generator.py", GENERATOR))
    assert generator.generate(10, 1) != generator.generate(10, 2)


def test_generated_values_are_canonical_json(loader, tmp_path):
    generator = loader.generator(write(tmp_path, "generator.py", GENERATOR))
    assert generator.generate(1, 1)["pair"] == [1, 2]


def test_validate_accepts_valid_inputs(loader, tmp_path):
    generator = loader.generator(write(tmp_path, "generator.py", GENERATOR))
    assert generator.validate({"nums": [1]}) is None


def test_validate_reports_the_assertion_message(loader, tmp_path):
    generator = loader.generator(write(tmp_path, "generator.py", GENERATOR))
    assert generator.validate({"nums": [1] * 9}) == "too many numbers"


def test_validate_reports_an_assertion_without_message(loader, tmp_path):
    text = "def generate(rng, n):\n    return {}\n\ndef validate(case_input):\n    assert False\n"
    generator = loader.generator(write(tmp_path, "generator.py", text))
    assert generator.validate({}) == "validate() rejected the input"


def test_validate_is_optional(loader, tmp_path):
    text = "def generate(rng, n):\n    return {}\n"
    assert loader.generator(write(tmp_path, "generator.py", text)).validate({}) is None


def test_generator_that_does_not_import_is_a_content_error(loader, tmp_path):
    with pytest.raises(ContentError, match=r"problems/0001-two-sum/generator\.py"):
        loader.generator(write(tmp_path, "generator.py", "import nonexistent_module\n"))


def test_generator_without_generate_is_a_content_error(loader, tmp_path):
    with pytest.raises(ContentError, match="no generate"):
        loader.generator(write(tmp_path, "generator.py", "x = 1\n"))


def test_generate_that_raises_is_a_content_error(loader, tmp_path):
    text = "def generate(rng, n):\n    raise ValueError('n too small')\n"
    generator = loader.generator(write(tmp_path, "generator.py", text))
    with pytest.raises(ContentError, match=r"generate\(n=1, seed=2\) raised ValueError"):
        generator.generate(1, 2)


def test_generate_must_return_an_object(loader, tmp_path):
    text = "def generate(rng, n):\n    return [1]\n"
    generator = loader.generator(write(tmp_path, "generator.py", text))
    with pytest.raises(ContentError, match="JSON object"):
        generator.generate(1, 1)


def test_generate_must_return_json_values(loader, tmp_path):
    text = "def generate(rng, n):\n    return {'s': {1, 2}}\n"
    generator = loader.generator(write(tmp_path, "generator.py", text))
    with pytest.raises(ContentError, match="JSON"):
        generator.generate(1, 1)


def test_checker_is_the_check_function(loader, tmp_path):
    text = "def check(case_input, output, expected):\n    return None if output else 'empty'\n"
    check = loader.checker(write(tmp_path, "checker.py", text))
    assert check({}, [], None) == "empty"


def test_checker_without_check_is_a_content_error(loader, tmp_path):
    with pytest.raises(ContentError, match="no check"):
        loader.checker(write(tmp_path, "checker.py", "x = 1\n"))


def test_modules_with_the_same_file_name_stay_separate(loader, tmp_path):
    first = write(tmp_path, "generator.py", "def generate(rng, n):\n    return {'a': 1}\n")
    other = tmp_path / "problems" / "0002-other" / "generator.py"
    other.parent.mkdir(parents=True)
    other.write_text("def generate(rng, n):\n    return {'a': 2}\n")
    results = [loader.generator(path).generate(1, 1) for path in (first, other)]
    assert results == [{"a": 1}, {"a": 2}]


def test_loading_writes_no_bytecode_next_to_the_content(loader, tmp_path):
    path = write(tmp_path, "generator.py", "import json\n\ndef generate(rng, n):\n    return {}\n")
    loader.generator(path)
    assert not (path.parent / "__pycache__").exists()


def test_content_code_may_define_dataclasses(loader, tmp_path):
    text = (
        "from dataclasses import dataclass\n\n@dataclass\nclass Pair:\n    a: int\n\n"
        "def generate(rng, n):\n    return {'a': Pair(n).a}\n"
    )
    assert loader.generator(write(tmp_path, "generator.py", text)).generate(4, 1) == {"a": 4}


def test_syntax_errors_are_content_errors(loader, tmp_path):
    with pytest.raises(ContentError, match="SyntaxError"):
        loader.generator(write(tmp_path, "generator.py", "def generate(:\n"))
