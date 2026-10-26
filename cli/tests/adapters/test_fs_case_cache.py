from pathlib import Path

from coding_study.adapters.fs_case_cache import FsGeneratedCaseCache
from coding_study.domain.cases import Expected, FunctionInput, OperationSequence
from coding_study.domain.generated_cases import GeneratedCase

CASES = {
    "g1": GeneratedCase(FunctionInput({"nums": [1, 2], "target": 3}), Expected([0, 1])),
    "g2": GeneratedCase(OperationSequence(("LRUCache", "get"), ((2,), (1,))), Expected([None, -1])),
    "g3": GeneratedCase(FunctionInput({}), Expected(None)),
}


def test_missing_entry(tmp_path):
    assert FsGeneratedCaseCache(tmp_path).load("two-sum", "abc") is None


def test_saved_cases_round_trip(tmp_path):
    cache = FsGeneratedCaseCache(tmp_path)
    cache.save("two-sum", "abc", CASES)
    assert cache.load("two-sum", "abc") == CASES


def test_entries_live_under_the_cases_cache(tmp_path):
    FsGeneratedCaseCache(tmp_path).save("two-sum", "abc", CASES)
    assert (tmp_path / ".cs/cases/two-sum/abc.json").is_file()


def test_other_keys_are_misses(tmp_path):
    cache = FsGeneratedCaseCache(tmp_path)
    cache.save("two-sum", "abc", CASES)
    assert cache.load("two-sum", "def") is None


def test_unreadable_entry_is_a_miss(tmp_path: Path):
    entry = tmp_path / ".cs/cases/two-sum/abc.json"
    entry.parent.mkdir(parents=True)
    entry.write_text("{not json")
    assert FsGeneratedCaseCache(tmp_path).load("two-sum", "abc") is None
