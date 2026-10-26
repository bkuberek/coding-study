import sys

from coding_study.adapters.subprocess_tool_probe import (
    TIMED_OUT_EXIT_CODE,
    SubprocessCommandRunner,
    SubprocessToolProbe,
)
from coding_study.application.ports import ProbeResult


def python_command(code: str) -> tuple[str, ...]:
    return (sys.executable, "-I", "-c", code)


def test_returns_exit_code_and_output():
    result = SubprocessToolProbe().run(python_command("print('v1.2.3')"))
    assert result == ProbeResult(0, "v1.2.3\n")


def test_output_includes_standard_error_after_standard_output():
    code = "import sys; print('out'); print('err', file=sys.stderr)"
    assert SubprocessToolProbe().run(python_command(code)) == ProbeResult(0, "out\nerr\n")


def test_reports_non_zero_exit_code():
    result = SubprocessToolProbe().run(python_command("raise SystemExit(3)"))
    assert result == ProbeResult(3, "")


def test_missing_executable_returns_none():
    assert SubprocessToolProbe().run(("cs-test-no-such-tool", "--version")) is None


def test_hanging_command_times_out():
    probe = SubprocessToolProbe(timeout_seconds=0.05)
    result = probe.run(python_command("import time; time.sleep(5)"))
    assert result == ProbeResult(TIMED_OUT_EXIT_CODE, "timed out after 0.05s")


def test_setup_command_runs_in_the_given_directory(tmp_path):
    result = SubprocessCommandRunner().run(
        python_command("import os; print(os.getcwd())"), tmp_path
    )
    assert result == ProbeResult(0, f"{tmp_path.resolve()}\n")


def test_setup_command_with_a_missing_executable_returns_none(tmp_path):
    assert SubprocessCommandRunner().run(("cs-test-no-such-tool", "install"), tmp_path) is None
