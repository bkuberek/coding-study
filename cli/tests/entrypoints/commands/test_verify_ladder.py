"""How `cstudy verify --ladder` reports the ladder check."""

from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import verify as verify_command
from coding_study.entrypoints.shared import ExitCode
from tests.application.test_verify_ladder import environment_with
from tests.bench_fakes import optimal_user, power_law, timed

runner = CliRunner()


def invoke(tmp_path, monkeypatch, benches=None):
    environment = environment_with(tmp_path, benches or optimal_user())
    monkeypatch.setattr(verify_command, "load_environment", lambda *_: environment)
    return runner.invoke(cli.app, ["verify", "two-sum", "--lang", "python", "--ladder"])


def test_a_consistent_ladder_is_ok(tmp_path, monkeypatch):
    result = invoke(tmp_path, monkeypatch)
    line = next(line for line in result.output.splitlines() if line.startswith("0001-two-sum"))
    assert "ladder ok" in line


def test_a_consistent_ladder_exits_0(tmp_path, monkeypatch):
    assert invoke(tmp_path, monkeypatch).exit_code == ExitCode.SUCCESS


def test_a_contradiction_fails_with_its_message(tmp_path, monkeypatch):
    result = invoke(tmp_path, monkeypatch, optimal_user(**{"hash-map": power_law(2.0)}))
    assert result.exit_code == ExitCode.FAILURES
    assert (
        "  ladder py: hash-map declares O(n) but measures ~n^2 (slope 2.00); "
        "time / n varies 160x, more than the 4x tolerance"
    ) in result.output


def test_a_tolerated_band_is_a_warning(tmp_path, monkeypatch):
    fixed_cost = timed(lambda size: 1000.0 + 10.0 * size, [1, 0])
    result = invoke(tmp_path, monkeypatch, optimal_user(**{"hash-map": fixed_cost}))
    assert "warning: ladder py: hash-map declares O(n) and measures ~1|log n|sqrt n" in (
        result.output
    )


def test_an_unclassified_reference_is_a_warning(tmp_path, monkeypatch):
    def too_slow_from_400(target, bench_input):
        measured = power_law(2.0)(target, bench_input)
        if bench_input.size < 400:
            return measured
        return type(measured)(bench_input.size, exceeded_ns=5 * 10**9)

    result = invoke(tmp_path, monkeypatch, optimal_user(**{"brute-force": too_slow_from_400}))
    assert "warning: ladder py: brute-force: 2 usable sizes (budget exceeded at n=4e2)" in (
        result.output
    )
