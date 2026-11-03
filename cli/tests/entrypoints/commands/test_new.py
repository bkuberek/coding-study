import pytest
from typer.testing import CliRunner

from coding_study.domain.scaffold import TemplateName
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import new, verify
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import make_environment

runner = CliRunner()


@pytest.fixture
def environment(content_root, monkeypatch):
    environment = make_environment(content_root)
    monkeypatch.setattr(new, "load_environment", lambda *_: environment)
    monkeypatch.setattr(verify, "load_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["new", *arguments])


def test_prints_the_new_directory(environment):
    assert invoke("max-gap").output.splitlines()[0] == (
        "created  problems/0003-max-gap  (array template, draft)"
    )


def test_prints_the_authoring_workflow_with_the_slug(environment):
    lines = invoke("max-gap").output.splitlines()
    assert lines[2:5] == [
        "next steps (docs/specs/authoring.md#workflow)",
        "  2. Write problem.md: statement, input, output, constraints, in original wording",
        "     cstudy verify max-gap --static",
    ]


def test_says_where_to_trim_the_languages(environment):
    assert invoke("max-gap").output.splitlines()[1] == (
        "languages  meta.yaml lists the languages to write references in; remove the ones you "
        "do not practice, and their reference files"
    )


def test_ends_with_the_ready_gate(environment):
    assert invoke("max-gap").output.splitlines()[-1] == (
        "     cstudy verify max-gap --oracle --ladder --require-ready"
    )


PROJECT_TEMPLATES = (
    "project-python",
    "project-typescript",
    "project-java",
    "project-kotlin",
    "project-go",
    "project-rust",
)


@pytest.mark.parametrize("template", PROJECT_TEMPLATES)
def test_a_project_template_prints_the_project_workflow(environment, template):
    lines = invoke(f"bank-{template}", "--from-template", template).output.splitlines()
    assert lines[1:4] == [
        "next steps (docs/specs/authoring.md#project-problems)",
        "  2. Write problem.md, with ## Project and one ## Level section per level, and "
        "tests.json, with at least 2 visible and 2 hidden cases per level",
        f"     cstudy verify bank-{template} --static",
    ]


@pytest.mark.parametrize("template", PROJECT_TEMPLATES)
def test_a_project_template_ends_with_the_ready_gate(environment, template):
    lines = invoke(f"bank-{template}", "--from-template", template).output.splitlines()
    assert lines[-2:] == [
        "  5. Write solutions/explanation.md with ### Design; set status: ready",
        f"     cstudy verify bank-{template} --require-ready",
    ]


def test_the_virtual_clock_flag_writes_a_go_project_on_the_virtual_clock(environment):
    result = invoke("waiter-project-go", "--from-template", "project-go", "--virtual-clock")
    meta = environment.problems.load("waiter-project-go").meta
    assert (result.exit_code, meta.project.clock) == (0, "virtual")  # type: ignore[union-attr]


def test_the_virtual_clock_flag_writes_a_python_project_on_the_virtual_clock(environment):
    result = invoke("waiter-project-python", "--from-template", "project-python", "--virtual-clock")
    meta = environment.problems.load("waiter-project-python").meta
    assert (result.exit_code, meta.project.clock) == (0, "virtual")  # type: ignore[union-attr]


def test_the_virtual_clock_flag_writes_a_typescript_project_on_the_virtual_clock(environment):
    result = invoke(
        "waiter-project-typescript", "--from-template", "project-typescript", "--virtual-clock"
    )
    meta = environment.problems.load("waiter-project-typescript").meta
    assert (result.exit_code, meta.project.clock) == (0, "virtual")  # type: ignore[union-attr]


def test_the_virtual_clock_flag_writes_a_kotlin_project_on_the_virtual_clock(environment):
    result = invoke("waiter-project-kotlin", "--from-template", "project-kotlin", "--virtual-clock")
    meta = environment.problems.load("waiter-project-kotlin").meta
    assert (result.exit_code, meta.project.clock) == (0, "virtual")  # type: ignore[union-attr]


def test_a_virtual_clock_project_says_so_in_its_first_line(environment):
    result = invoke("waiter-project-go", "--from-template", "project-go", "--virtual-clock")
    assert result.output.splitlines()[0] == (
        "created  problems/0003-waiter-project-go  "
        "(project-go template with the virtual clock, draft)"
    )


def test_a_virtual_clock_project_adds_the_determinism_step_to_the_workflow(environment):
    lines = invoke("waiter-project-go", "--from-template", "project-go", "--virtual-clock")
    steps = lines.output.splitlines()
    assert steps[6:10] == [
        "  4. Write the reference overlay in solutions/<approach>/, level by level",
        "     cstudy verify waiter-project-go",
        "  5. Check that every case gives the same outputs in every run, and fix the expected "
        "values that depend on a tie",
        "     cstudy verify waiter-project-go",
    ]


def test_a_virtual_clock_project_still_ends_with_the_ready_gate(environment):
    lines = invoke("waiter-project-go", "--from-template", "project-go", "--virtual-clock")
    assert lines.output.splitlines()[-2:] == [
        "  6. Write solutions/explanation.md with ### Design; set status: ready",
        "     cstudy verify waiter-project-go --require-ready",
    ]


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["--from-template", "array"], "--virtual-clock applies to the project-* templates"),
        (
            ["--from-template", "project-java"],
            "--virtual-clock is not available for project-java: Java has no virtual clock\n",
        ),
    ],
)
def test_the_virtual_clock_flag_exits_3_where_it_does_not_apply(environment, arguments, message):
    result = invoke("waiter", *arguments, "--virtual-clock")
    assert (result.exit_code, message in result.output) == (ExitCode.USAGE_ERROR, True)


def test_the_virtual_clock_flag_writes_nothing_where_it_does_not_apply(environment):
    invoke("waiter", "--from-template", "project-java", "--virtual-clock")
    assert not environment.workspace.exists("problems/0003-waiter")


STRESS_TEMPLATES = (
    "project-python",
    "project-java",
    "project-kotlin",
    "project-go",
    "project-rust",
)


@pytest.mark.parametrize("template", STRESS_TEMPLATES)
def test_the_stress_flag_writes_a_project_with_a_broken_overlay(environment, template):
    result = invoke(f"tally-{template}", "--from-template", template, "--stress")
    concurrency = environment.problems.load(f"tally-{template}").meta.concurrency
    broken = [reference.id for reference in concurrency.broken]  # type: ignore[union-attr]
    assert (result.exit_code, broken) == (0, ["lost-update"])


@pytest.mark.parametrize("template", ["project-python", "project-typescript", "project-kotlin"])
def test_the_stress_flag_combines_with_the_virtual_clock(environment, template):
    result = invoke(f"tally-{template}", "--from-template", template, "--virtual-clock", "--stress")
    meta = environment.problems.load(f"tally-{template}").meta
    broken = [reference.id for reference in meta.concurrency.broken]  # type: ignore[union-attr]
    assert (result.exit_code, meta.project.clock, broken) == (  # type: ignore[union-attr]
        0,
        "virtual",
        ["lost-update"],
    )


def test_a_stress_project_says_so_in_its_first_line(environment):
    result = invoke("tally-go", "--from-template", "project-go", "--stress")
    assert result.output.splitlines()[0] == (
        "created  problems/0003-tally-go  (project-go template with stress cases, draft)"
    )


def test_a_stress_project_on_the_virtual_clock_says_both_in_its_first_line(environment):
    result = invoke("tally-go", "--from-template", "project-go", "--virtual-clock", "--stress")
    assert result.output.splitlines()[0] == (
        "created  problems/0003-tally-go  "
        "(project-go template with the virtual clock and stress cases, draft)"
    )


def test_a_stress_project_adds_the_broken_overlay_step_to_the_workflow(environment):
    lines = invoke("tally-go", "--from-template", "project-go", "--stress").output.splitlines()
    assert lines[6:10] == [
        "  4. Write the reference overlay in solutions/<approach>/, level by level",
        "     cstudy verify tally-go",
        "  5. Write the broken overlays in solutions/broken/<id>/ and tune the stress cases until "
        "each overlay is caught",
        "     cstudy verify tally-go",
    ]


def test_a_stress_project_on_the_virtual_clock_checks_determinism_before_the_broken_overlays(
    environment,
):
    lines = invoke("tally-go", "--from-template", "project-go", "--virtual-clock", "--stress")
    steps = [line for line in lines.output.splitlines() if line[:3].strip().rstrip(".").isdigit()]
    assert [step[5:30] for step in steps] == [
        "Write problem.md, with ##",
        "Shape the starter: the en",
        "Write the reference overl",
        "Check that every case giv",
        "Write the broken overlays",
        "Write solutions/explanati",
    ]


@pytest.mark.parametrize("flags", [("--stress",), ("--virtual-clock", "--stress")])
def test_a_stress_project_still_ends_with_the_ready_gate(environment, flags):
    lines = invoke("tally-go", "--from-template", "project-go", *flags).output.splitlines()
    assert lines[-1] == "     cstudy verify tally-go --require-ready"


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["--from-template", "array"], "--stress applies to the project-* templates"),
        (["--from-template", "project-typescript"], "without --virtual-clock"),
        (
            ["--from-template", "project-java", "--virtual-clock"],
            "--virtual-clock is not available for project-java: Java has no virtual clock\n",
        ),
    ],
)
def test_the_stress_flag_exits_3_where_it_does_not_apply(environment, arguments, message):
    result = invoke("tally", *arguments, "--stress")
    assert (result.exit_code, message in result.output) == (ExitCode.USAGE_ERROR, True)


def test_the_stress_flag_writes_nothing_where_it_does_not_apply(environment):
    invoke("tally", "--from-template", "project-typescript", "--stress")
    assert not environment.workspace.exists("problems/0003-tally")


@pytest.mark.parametrize("flags", [("--stress",), ("--virtual-clock", "--stress")])
def test_cs_verify_static_passes_once_the_placeholders_are_replaced_in_a_stress_project(
    environment, flags
):
    invoke("scaffolded", "--from-template", "project-go", *flags)
    for path in (environment.root / "problems" / "0003-scaffolded").rglob("*"):
        if path.is_file():
            path.write_text(path.read_text().replace("TODO", "Written"))
    result = runner.invoke(cli.app, ["verify", "scaffolded", "--static"])
    assert (result.exit_code, "warning" in result.output) == (0, False)


def test_flags_reach_the_scaffold(environment):
    invoke("same-tree", "--from-template", "tree", "--title", "Same Tree?", "--difficulty", "easy")
    meta = environment.problems.load("same-tree").meta
    assert (meta.title, meta.difficulty, meta.patterns) == ("Same Tree?", "easy", ("trees",))


def test_an_existing_slug_exits_3(environment):
    assert invoke("two-sum").exit_code == ExitCode.USAGE_ERROR


def test_an_unknown_template_exits_3(environment):
    assert invoke("x", "--from-template", "graph").exit_code == ExitCode.USAGE_ERROR


@pytest.mark.parametrize("flags", [(), ("--virtual-clock",)])
def test_cs_verify_static_passes_once_the_placeholders_are_replaced_in_a_clock_project(
    environment, flags
):
    invoke("scaffolded", "--from-template", "project-go", *flags)
    for path in (environment.root / "problems" / "0003-scaffolded").rglob("*"):
        if path.is_file():
            path.write_text(path.read_text().replace("TODO", "Written"))
    result = runner.invoke(cli.app, ["verify", "scaffolded", "--static"])
    assert (result.exit_code, "warning" in result.output) == (0, False)


@pytest.mark.parametrize("template", list(TemplateName))
def test_cs_verify_static_passes_once_the_placeholders_are_replaced(environment, template):
    invoke("scaffolded", "--from-template", template)
    for path in (environment.root / "problems" / "0003-scaffolded").rglob("*"):
        if path.is_file():
            path.write_text(path.read_text().replace("TODO", "Written"))
    result = runner.invoke(cli.app, ["verify", "scaffolded", "--static"])
    assert (result.exit_code, "warning" in result.output) == (0, False)
