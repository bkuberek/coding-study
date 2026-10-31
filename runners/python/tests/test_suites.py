"""Suite jobs: a project's own tests, run by pytest inside the runner
(docs/specs/runners.md#suite-job)."""

import pytest

from cs_runner.program import BAD_REQUEST_EXIT_CODE
from tests.project_harness import conformance_project, run_project, suite_job, write_project
from tests.runner_harness import Event, RunnerRun, run_jobs

PYPROJECT = """
    [tool.pytest.ini_options]
    testpaths = ["tests"]
    pythonpath = ["."]
    addopts = "--import-mode=importlib -p no:cacheprovider"
"""
STATUSES = {
    "pyproject.toml": PYPROJECT,
    "calc/calc.py": """
        def double(value):
            return 2 * value
    """,
    "tests/test_calc.py": """
        import pytest

        from calc.calc import double


        def test_passes():
            assert double(2) == 4


        def test_fails():
            assert double(2) == 5


        def test_raises():
            {}["missing"]


        def test_prints():
            print("hello from a test")


        @pytest.mark.skip(reason="not today")
        def test_skipped():
            pass


        @pytest.fixture
        def broken():
            raise RuntimeError("fixture failure")


        def test_setup_fails(broken):
            pass


        def test_calls_fail():
            pytest.fail("explicit failure")


        @pytest.mark.xfail(reason="known bug")
        def test_expected_to_fail():
            assert double(2) == 5
    """,
    "tests/test_other.py": """
        from calc.calc import double


        def test_double():
            assert double(3) == 6


        def test_double_zero():
            assert double(0) == 0
    """,
}
CALC = "tests/test_calc.py"
OTHER = "tests/test_other.py"


def results(run: RunnerRun) -> dict[str, Event]:
    return {result["case_id"]: result for result in run.named("case_result")}


def statuses(run: RunnerRun) -> dict[str, str]:
    return {case_id: str(result["status"]) for case_id, result in results(run).items()}


@pytest.fixture(scope="module")
def statuses_project(tmp_path_factory):
    return write_project(tmp_path_factory.mktemp("statuses") / "project", STATUSES)


@pytest.fixture(scope="module")
def full_run(statuses_project):
    return run_project(statuses_project, suite_job(statuses_project))


def test_a_suite_reports_every_test_in_order_inside_its_job(full_run):
    names = [(event["event"], event.get("case_id")) for event in full_run.events[1:3]]
    assert names == [("job_start", None), ("case_start", f"{CALC}::test_passes")]


def test_a_suite_ends_its_job_and_says_bye(full_run):
    assert [event["event"] for event in full_run.events[-2:]] == ["job_end", "bye"]


def test_each_test_reports_its_status_under_its_node_id(full_run):
    assert statuses(full_run) == {
        f"{CALC}::test_passes": "ok",
        f"{CALC}::test_fails": "failed",
        f"{CALC}::test_raises": "error",
        f"{CALC}::test_prints": "ok",
        f"{CALC}::test_skipped": "skipped",
        f"{CALC}::test_setup_fails": "error",
        f"{CALC}::test_calls_fail": "failed",
        f"{CALC}::test_expected_to_fail": "skipped",
        f"{OTHER}::test_double": "ok",
        f"{OTHER}::test_double_zero": "ok",
    }


def test_a_failed_assertion_carries_pytests_detail(full_run):
    failed = results(full_run)[f"{CALC}::test_fails"]
    assert failed["message"] == "assert 4 == 5\n +  where 4 = double(2)"


def test_pytest_fail_is_a_failure_with_its_message(full_run):
    assert results(full_run)[f"{CALC}::test_calls_fail"]["message"] == "explicit failure"


def test_another_exception_is_an_error_traced_in_the_project(full_run):
    assert results(full_run)[f"{CALC}::test_raises"]["error"] == {
        "type": "KeyError",
        "message": "'missing'",
        "trace": f"{CALC}:16 in test_raises",
    }


def test_a_failing_fixture_is_an_error(full_run):
    error = results(full_run)[f"{CALC}::test_setup_fails"]["error"]
    assert (error["type"], error["message"]) == ("RuntimeError", "fixture failure")


def test_a_skipped_test_carries_its_reason(full_run):
    assert results(full_run)[f"{CALC}::test_skipped"]["message"] == "not today"


def test_an_expected_failure_is_skipped_with_its_reason(full_run):
    assert results(full_run)[f"{CALC}::test_expected_to_fail"]["message"] == "xfail: known bug"


def test_output_is_captured_per_test(full_run):
    printed = {case_id: result.get("stdout") for case_id, result in results(full_run).items()}
    assert {case_id: text for case_id, text in printed.items() if text} == {
        f"{CALC}::test_prints": "hello from a test\n"
    }


def test_every_result_carries_a_duration(full_run):
    assert all(result["duration_ns"] >= 0 for result in results(full_run).values())


def test_select_runs_tests_by_id_or_by_their_last_part(statuses_project):
    job = suite_job(statuses_project, select=[f"{CALC}::test_passes", "test_double"])
    run = run_project(statuses_project, job)
    assert list(statuses(run)) == [f"{CALC}::test_passes", f"{OTHER}::test_double"]


def test_skip_leaves_out_exactly_the_named_tests(statuses_project):
    skipped = [f"{CALC}::{name}" for name in ("test_passes", "test_fails", "test_raises")]
    run = run_project(statuses_project, suite_job(statuses_project, skip=[*skipped, OTHER]))
    assert f"{OTHER}::test_double" in statuses(run)
    assert not set(skipped) & set(statuses(run))


def test_exclude_leaves_out_whole_files(statuses_project):
    run = run_project(statuses_project, suite_job(statuses_project, exclude=[CALC]))
    assert list(statuses(run)) == [f"{OTHER}::test_double", f"{OTHER}::test_double_zero"]


def test_a_suite_without_tests_reports_none(tmp_path):
    root = write_project(tmp_path / "project", {"pyproject.toml": PYPROJECT, "tests/x.py": ""})
    run = run_project(root, suite_job(root))
    assert [event["event"] for event in run.events] == ["hello", "job_start", "job_end", "bye"]


@pytest.fixture
def broken_import(tmp_path):
    files = {"pyproject.toml": PYPROJECT, "tests/test_broken.py": "import missing_library\n"}
    calc = {path: STATUSES[path] for path in ("calc/calc.py", OTHER)}
    return write_project(tmp_path / "project", files | calc)


def test_a_test_file_that_does_not_import_is_one_error_named_after_the_file(broken_import):
    error = results(run_project(broken_import, suite_job(broken_import)))["tests/test_broken.py"]
    assert error["error"] == {
        "type": "ModuleNotFoundError",
        "message": "No module named 'missing_library'",
        "trace": "tests/test_broken.py:1 in <module>",
    }


def test_the_other_files_still_run_after_a_collection_error(broken_import):
    run = run_project(broken_import, suite_job(broken_import))
    assert f"{OTHER}::test_double" in statuses(run)


def test_a_collection_error_reported_before_a_restart_is_not_repeated(broken_import):
    run = run_project(broken_import, suite_job(broken_import, skip=["tests/test_broken.py"]))
    assert "tests/test_broken.py" not in statuses(run)


def test_unusable_pytest_options_are_a_load_error(tmp_path):
    pyproject = '[tool.pytest.ini_options]\naddopts = "--no-such-option"\n'
    root = write_project(tmp_path / "project", {"pyproject.toml": pyproject})
    (load_error,) = run_project(root, suite_job(root)).named("load_error")
    assert load_error["error"]["type"] == "UsageError"


def test_a_project_file_named_like_pytest_does_not_replace_it(tmp_path):
    files = {
        "pyproject.toml": PYPROJECT,
        "pytest.py": "raise ImportError('shadowed')\n",
        "tests/test_imports.py": """
            import pytest


            def test_uses_pytest():
                assert pytest.approx(1) == 1
        """,
    }
    root = write_project(tmp_path / "project", files)
    assert set(statuses(run_project(root, suite_job(root))).values()) == {"ok"}


def test_project_modules_in_a_suite_compile_from_source_on_every_run(tmp_path):
    files = {
        "pyproject.toml": PYPROJECT,
        "calc/limit.py": "LIMIT = 100\n",
        "tests/test_limit.py": """
            from calc.limit import LIMIT


            def test_limit():
                assert LIMIT == 200
        """,
    }
    root = write_project(tmp_path / "project", files)
    run_project(root, suite_job(root))
    (root / "calc" / "limit.py").write_text("LIMIT = 200\n", encoding="utf-8")
    assert set(statuses(run_project(root, suite_job(root))).values()) == {"ok"}


def test_another_framework_is_a_bad_request(tmp_path):
    run = run_jobs(tmp_path, suite_job(tmp_path, framework="node-test"))
    assert run.exit_code == BAD_REQUEST_EXIT_CODE


@pytest.fixture(scope="module")
def conformance_suite(tmp_path_factory):
    root = tmp_path_factory.mktemp("suite") / "project"
    return conformance_project("conformance-suite-pytest", "reference", root)


STATUS_TESTS = "tests/test_statuses.py"
HANGS = f"{STATUS_TESTS}::test_hangs"
ENDS = f"{STATUS_TESTS}::test_ends_the_process"


@pytest.fixture(scope="module")
def run_until_the_process_ends(conformance_suite):
    """The CLI's hang guard killed the runner at the hanging test; this is the restart."""
    return run_project(conformance_suite, suite_job(conformance_suite, skip=[HANGS]))


def test_a_test_that_ends_the_process_leaves_its_case_open(run_until_the_process_ends):
    run = run_until_the_process_ends
    assert (run.exit_code, run.events[-1]) == (
        3,
        {
            "event": "case_start",
            "job_id": "project/suite",
            "case_id": ENDS,
        },
    )


def test_the_conformance_suite_reports_the_tests_before_the_exit(run_until_the_process_ends):
    assert statuses(run_until_the_process_ends) == {
        f"{STATUS_TESTS}::test_passes": "ok",
        f"{STATUS_TESTS}::test_fails_an_assertion": "failed",
    }


def test_the_restart_after_the_exit_runs_the_remaining_tests(conformance_suite):
    reported = [f"{STATUS_TESTS}::test_passes", HANGS, f"{STATUS_TESTS}::test_fails_an_assertion"]
    run = run_project(conformance_suite, suite_job(conformance_suite, skip=[*reported, ENDS]))
    assert statuses(run) == {
        f"{STATUS_TESTS}::test_raises": "error",
        f"{STATUS_TESTS}::test_prints": "ok",
    }
