from coding_study.adapters.fs_calibration_cache import FsCalibrationCache, local_machine_id
from coding_study.domain.problem import Language
from coding_study.domain.time_limits import Calibration

CALIBRATION = Calibration("hash-map", {"ex1": 1200, "g1": 8_000_000})


def test_saved_calibration_loads_back(tmp_path):
    cache = FsCalibrationCache(tmp_path, "machine-a")
    cache.save(Language.KOTLIN, "two-sum", "key-1", CALIBRATION)
    assert cache.load(Language.KOTLIN, "two-sum", "key-1") == CALIBRATION


def test_calibration_lives_in_one_file_per_language_and_problem(tmp_path):
    FsCalibrationCache(tmp_path, "machine-a").save(Language.JAVA, "two-sum", "k", CALIBRATION)
    assert (tmp_path / ".cs" / "calibration" / "java" / "two-sum.json").is_file()


def test_another_key_is_a_miss(tmp_path):
    cache = FsCalibrationCache(tmp_path, "machine-a")
    cache.save(Language.PYTHON, "two-sum", "key-1", CALIBRATION)
    assert cache.load(Language.PYTHON, "two-sum", "key-2") is None


def test_another_machine_is_a_miss(tmp_path):
    FsCalibrationCache(tmp_path, "machine-a").save(Language.PYTHON, "two-sum", "k", CALIBRATION)
    assert FsCalibrationCache(tmp_path, "machine-b").load(Language.PYTHON, "two-sum", "k") is None


def test_missing_file_is_a_miss(tmp_path):
    assert FsCalibrationCache(tmp_path, "machine-a").load(Language.PYTHON, "two-sum", "k") is None


def test_unreadable_file_is_a_miss(tmp_path):
    entry = tmp_path / ".cs" / "calibration" / "python" / "two-sum.json"
    entry.parent.mkdir(parents=True)
    entry.write_text("{not json")
    assert FsCalibrationCache(tmp_path, "machine-a").load(Language.PYTHON, "two-sum", "k") is None


def test_saving_again_replaces_the_entry(tmp_path):
    cache = FsCalibrationCache(tmp_path, "machine-a")
    cache.save(Language.PYTHON, "two-sum", "old", CALIBRATION)
    cache.save(Language.PYTHON, "two-sum", "new", Calibration("sort", {"ex1": 5}))
    assert cache.load(Language.PYTHON, "two-sum", "new") == Calibration("sort", {"ex1": 5})


def test_machine_id_is_stable():
    assert local_machine_id() == local_machine_id()
