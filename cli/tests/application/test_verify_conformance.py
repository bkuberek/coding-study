import json
import shutil
from pathlib import Path

import pytest

from coding_study.adapters.conformance_fixtures import load_conformance_suite
from coding_study.adapters.environment_factory import conformance_environment
from coding_study.application.verify_conformance import (
    ConformanceRequest,
    FixtureVerification,
    verify_conformance,
)
from coding_study.domain.problem import Language
from tests.e2e import e2e_environment
from tests.helpers import REPOSITORY_ROOT, SCHEMAS_DIRECTORY

pytestmark = pytest.mark.slow

CONFORMANCE = REPOSITORY_ROOT / "runners" / "conformance"
SOLUTIONS = {
    "9002-conformance-function": {
        "identity.py": (
            "def echo_http_codes(first_value, second_value, third_flag):\n    return first_value\n"
        )
    },
    "9003-conformance-exception": {
        "raises.py": "def fail_with(message):\n    raise RuntimeError(message)\n"
    },
    "9004-conformance-op-error": {
        "counts.py": (
            "class Counter:\n"
            "    def __init__(self):\n        self.count = 0\n\n"
            "    def increment(self):\n        self.count += 1\n        return self.count\n\n"
            "    def fail(self):\n        raise RuntimeError('counter failure')\n"
        )
    },
    "9007-conformance-missing-symbol": {
        "misnamed.py": "def echo_number_typo(value):\n    return value\n"
    },
    "9008-conformance-hang": {
        "spins.py": "def wait_for(value):\n    while value < 0:\n        pass\n    return value\n"
    },
    "9009-conformance-stdout": {
        "prints.py": "def shout(text):\n    print(text)\n    return text\n"
    },
}


@pytest.fixture
def root(tmp_path: Path) -> Path:
    shutil.copytree(SCHEMAS_DIRECTORY, tmp_path / "schemas")
    (tmp_path / "problems").mkdir()
    fixtures = tmp_path / "runners" / "conformance"
    slugs = set()
    for directory, solutions in SOLUTIONS.items():
        target = fixtures / directory
        shutil.copytree(CONFORMANCE / directory, target)
        (target / "solutions").mkdir(exist_ok=True)
        for name, source in solutions.items():
            (target / "solutions" / name).write_text(source)
        slugs.add(directory.partition("-")[2])
    expectations = json.loads((CONFORMANCE / "expectations.json").read_text())
    expectations["expectations"] = [
        entry for entry in expectations["expectations"] if entry["problem"] in slugs
    ]
    (fixtures / "expectations.json").write_text(json.dumps(expectations))
    return tmp_path


def conformance(root: Path, **fields):
    environment = conformance_environment(e2e_environment(root))
    request = ConformanceRequest(**{"language": Language.PYTHON, **fields})
    return verify_conformance(environment, load_conformance_suite(root), request, lambda _: None)


def by_directory(results) -> dict[str, FixtureVerification]:
    return {result.directory.rpartition("/")[2]: result for result in results}


def test_correct_runner_passes_every_fixture(root):
    assert [result.passed for result in conformance(root)] == [True] * len(SOLUTIONS)


def test_fixtures_are_reported_in_directory_order(root):
    assert list(by_directory(conformance(root))) == list(SOLUTIONS)


def test_wrong_error_message_is_a_failure(root):
    solution = root / "runners/conformance/9003-conformance-exception/solutions/raises.py"
    solution.write_text("def fail_with(message):\n    raise RuntimeError('other')\n")
    result = by_directory(conformance(root, slugs=("conformance-exception",)))[
        "9003-conformance-exception"
    ]
    assert result.languages[0].approaches[0].failures == (
        'ascii: expected message "conformance failure", got "other"',
        'unicode: expected message "üñí failure", got "other"',
    )


def test_expected_load_error_that_loads_is_a_failure(root):
    solution = root / "runners/conformance/9007-conformance-missing-symbol/solutions/misnamed.py"
    solution.write_text("def echo_number(value):\n    return value\n")
    result = by_directory(conformance(root, slugs=("conformance-missing-symbol",)))[
        "9007-conformance-missing-symbol"
    ]
    assert result.languages[0].approaches[0].failures == (
        "expected load_error, but the target loaded",
    )


def test_missing_reference_file(root):
    (root / "runners/conformance/9009-conformance-stdout/solutions/prints.py").unlink()
    result = by_directory(conformance(root, slugs=("conformance-stdout",)))[
        "9009-conformance-stdout"
    ]
    assert result.languages[0].problems == ("no python reference for prints",)


def test_selected_fixtures_only(root):
    results = conformance(root, slugs=("conformance-hang",))
    assert [result.directory for result in results] == ["runners/conformance/9008-conformance-hang"]


def test_expectations_without_a_fixture_are_errors(root):
    shutil.rmtree(root / "runners/conformance/9009-conformance-stdout")
    errors = [error for result in conformance(root) for error in result.errors]
    assert errors == ['expectations.json names "conformance-stdout", which has no fixture']
