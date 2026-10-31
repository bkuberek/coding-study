"""Static checks on project problems: S13's exception, S14 to S16, and the progressive checks
(S5, S6, S7, S10) as they apply to them."""

from dataclasses import replace

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.cases import Case, GeneratedInput, OperationSequence
from coding_study.domain.problem import (
    ComparatorSpec,
    ComparatorType,
    Language,
    ProblemKind,
    Track,
)
from coding_study.domain.project import Project, ProjectFile, ProjectFiles, ProjectTree
from coding_study.domain.ready_criteria import ready_problems
from coding_study.domain.signature import ClassSignature, Param
from coding_study.domain.static_checks import ProblemContent, static_checks
from coding_study.domain.stress import StressScenario
from coding_study.domain.type_dsl import parse_value_type
from tests.fakes import repository_root
from tests.helpers import BANK_PROJECT, PROJECT_PROBLEMS

FIXTURE = PROJECT_PROBLEMS / BANK_PROJECT
DIRECTORY = f"problems/{BANK_PROJECT}"
META = f"{DIRECTORY}/meta.yaml"
TESTS = f"{DIRECTORY}/tests.json"
PROBLEM = f"{DIRECTORY}/problem.md"
EXPLANATION = f"{DIRECTORY}/solutions/explanation.md"
STARTER = f"{DIRECTORY}/starter"
SOLUTIONS = f"{DIRECTORY}/solutions"
MAX_STARTER_BYTES = 256 * 1024


@pytest.fixture(scope="module")
def bank(tmp_path_factory):
    root = repository_root(tmp_path_factory.mktemp("repository"), PROJECT_PROBLEMS)
    return FsProblemRepository(root).load("bank-project-python")


def content(problem, **changes) -> ProblemContent:
    base = ProblemContent(
        directory=DIRECTORY,
        problem=problem,
        problem_markdown=(FIXTURE / "problem.md").read_text(),
        explanation=(FIXTURE / "solutions" / "explanation.md").read_text(),
        files=("meta.yaml", "problem.md", "tests.json"),
        solution_files=("explanation.md",),
    )
    return replace(base, **changes)


def errors(content_) -> list[str]:
    return [str(issue) for issue in static_checks(content_).errors]


def warnings(content_) -> list[str]:
    return [str(issue) for issue in static_checks(content_).warnings]


def with_meta(problem, **changes):
    return replace(problem, meta=replace(problem.meta, **changes))


def text_file(path: str, text: str = "") -> ProjectFile:
    return ProjectFile(path, len(text.encode()), text)


def project_files(problem) -> ProjectFiles:
    assert problem.project_files is not None
    return problem.project_files


def starter_files(problem) -> tuple[ProjectFile, ...]:
    starter = project_files(problem).starter
    assert starter is not None
    return starter.files


def with_starter(problem, *files: ProjectFile):
    """The starter with `files` added, or replacing the files at their paths."""
    paths = {file.path for file in files}
    kept = tuple(file for file in starter_files(problem) if file.path not in paths)
    starter = ProjectTree(tuple(sorted((*kept, *files), key=lambda file: file.path)))
    return replace(problem, project_files=replace(project_files(problem), starter=starter))


def without_starter_files(problem, *paths: str):
    kept = tuple(file for file in starter_files(problem) if file.path not in paths)
    starter = ProjectTree(kept)
    return replace(problem, project_files=replace(project_files(problem), starter=starter))


def with_overlays(problem, **overlays: ProjectTree):
    return replace(problem, project_files=replace(project_files(problem), overlays=overlays))


def edited_markdown(old: str, new: str) -> str:
    text = (FIXTURE / "problem.md").read_text()
    assert old in text
    return text.replace(old, new)


def edited_explanation(old: str, new: str) -> str:
    text = (FIXTURE / "solutions" / "explanation.md").read_text()
    assert old in text
    return text.replace(old, new)


def test_the_fixture_passes(bank):
    assert errors(content(bank)) == []


def test_the_fixture_has_no_warnings_without_language_notes(bank):
    assert warnings(content(bank)) == []


# S13


def test_a_project_problem_lists_one_language_and_no_more(bank):
    assert [issue for issue in errors(content(bank)) if "must list" in issue] == []


def test_a_project_problem_still_cannot_list_a_language_that_cannot_express_it(bank):
    head = Param("head", parse_value_type("ListNode"))
    signature = bank.meta.signature
    assert isinstance(signature, ClassSignature)
    signature = replace(signature, constructor_params=(head,))
    cyclic = OperationSequence(("Bank",), (({"values": [1], "cycle_at": 0},),))
    cases = (*bank.cases, replace(bank.cases[0], id="c1", input=cyclic))
    problem = with_meta(bank, signature=signature, languages=(Language.RUST,))
    problem = replace(problem, cases=cases)
    assert any("cannot list rust" in issue for issue in errors(content(problem)))


# S5


def test_project_examples_go_in_level_sections(bank):
    markdown = edited_markdown("## Constraints", "## Examples\n\nNone.\n\n## Constraints")
    assert (
        f'{PROBLEM}: project problems put examples in "## Level" sections, not in "## Examples"'
    ) in errors(content(bank, problem_markdown=markdown))


def test_every_level_of_a_project_needs_its_section(bank):
    text = (FIXTURE / "problem.md").read_text()
    markdown = text[: text.index("## Level 2")] + text[text.index("## Constraints") :]
    assert f'{PROBLEM}: missing "## Level 2: Transfers"' in errors(
        content(bank, problem_markdown=markdown)
    )


# S7


def test_a_project_reference_is_not_a_file_per_language(bank):
    found = errors(content(bank, solution_files=("explanation.md", "reference.py")))
    assert found == [
        f"{SOLUTIONS}/reference.py: a project reference is a directory, solutions/<approach>/"
    ]


def test_every_directory_in_solutions_is_the_declared_approach(bank):
    overlays = {**project_files(bank).overlays, "draft": ProjectTree((text_file("a.py"),))}
    assert errors(content(with_overlays(bank, **overlays))) == [
        f"{SOLUTIONS}/draft: maps to no declared approach"
    ]


@pytest.mark.parametrize("overlay", [None, ProjectTree(())], ids=["missing", "empty"])
def test_the_approach_has_files_in_its_directory(bank, overlay):
    overlays = {} if overlay is None else {"reference": overlay}
    assert errors(content(with_overlays(bank, **overlays))) == [
        f"{META}: approaches: reference has no files in solutions/reference/"
    ]


# S10


def test_a_project_case_uses_only_methods_of_its_level(bank):
    first = bank.cases[0]
    assert isinstance(first.input, OperationSequence)
    ops = OperationSequence(("Bank", "transfer"), ((), (1, "ivy", "leo", 5)))
    problem = replace(bank, cases=(replace(first, input=ops), *bank.cases[1:]))
    assert f"{TESTS}: cases[0] ex1: transfer is introduced at level 2" in errors(content(problem))


# S14


def test_a_project_problem_has_a_project_block(bank):
    assert errors(content(with_meta(bank, project=None))) == [
        f"{META}: project: missing (kind: project)"
    ]


def test_only_a_project_problem_has_a_project_block(bank):
    problem = with_meta(bank, kind=ProblemKind.PROGRESSIVE)
    assert f"{META}: project: only project problems have one" in errors(content(problem))


def test_a_project_problem_is_on_the_practical_track(bank):
    problem = with_meta(bank, track=Track.LLD)
    assert f"{META}: track: project problems are on the practical track" in errors(content(problem))


def test_a_project_problem_lists_exactly_one_language(bank):
    problem = with_meta(bank, languages=(Language.PYTHON, Language.TYPESCRIPT))
    assert errors(content(problem)) == [
        f"{META}: languages: a project problem lists exactly one language"
    ]


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN, Language.GO, Language.RUST])
def test_other_languages_have_no_project_problems_yet(bank, language):
    problem = with_meta(bank, languages=(language,))
    assert errors(content(problem)) == [
        f"{META}: languages: project problems are not yet supported in {language}"
    ]


def test_the_entry_is_well_formed_for_the_language(bank):
    problem = with_meta(bank, project=Project("bank/bank.py"))
    assert errors(content(problem)) == [
        f'{META}: project.entry: "bank/bank.py" is not a dotted module name such as bank.bank'
    ]


def test_the_tests_directory_stays_inside_the_project(bank):
    problem = with_meta(bank, project=Project("bank.bank", "../tests"))
    assert errors(content(problem)) == [
        f'{META}: project.tests: "../tests" leaves its folder through ".."'
    ]


def test_a_project_problem_uses_the_ops_comparator(bank):
    problem = with_meta(bank, comparator=ComparatorSpec(ComparatorType.EXACT))
    assert f"{META}: comparator.type: project problems use the ops comparator" in errors(
        content(problem)
    )


@pytest.mark.parametrize(
    "compared", [ComparatorType.EXACT, ComparatorType.UNORDERED, ComparatorType.FLOAT]
)
def test_a_method_compares_as_a_generated_test_can(bank, compared):
    comparator = ComparatorSpec(ComparatorType.OPS, per_method={"deposit": compared})
    assert errors(content(with_meta(bank, comparator=comparator))) == []


def test_a_method_cannot_compare_unordered_nested(bank):
    nested = ComparatorType.UNORDERED_NESTED
    comparator = ComparatorSpec(ComparatorType.OPS, per_method={"deposit": nested})
    assert errors(content(with_meta(bank, comparator=comparator))) == [
        f"{META}: comparator.per_method.deposit: generated tests compare with exact, unordered "
        "or float, not unordered-nested"
    ]


def with_constructor_param(problem, type_text: str):
    signature = problem.meta.signature
    assert isinstance(signature, ClassSignature)
    params = (Param("seed", parse_value_type(type_text)),)
    return with_meta(problem, signature=replace(signature, constructor_params=params))


def signature_errors(problem) -> list[str]:
    return [issue for issue in errors(content(problem)) if issue.startswith(f"{META}: signature")]


@pytest.mark.parametrize("type_text", ["TreeNode", "list<ListNode>", "GraphNode[]"])
def test_a_project_signature_has_no_node_types(bank, type_text):
    assert signature_errors(with_constructor_param(bank, type_text)) == [
        f"{META}: signature: {type_text}: project problems take scalars, arrays and lists, "
        "not node types"
    ]


@pytest.mark.parametrize("type_text", ["long", "string[]", "list<list<int>>", "decimal", "date"])
def test_a_python_project_signature_takes_scalars_arrays_and_lists(bank, type_text):
    assert signature_errors(with_constructor_param(bank, type_text)) == []


def typescript(problem):
    """The fixture as a TypeScript project, with a valid TypeScript starter and reference."""
    starter = ProjectTree(
        (
            text_file("README.md", "Run node --test.\n"),
            text_file("package.json", '{"type": "module"}\n'),
            text_file("src/bank.ts", "export class Bank {}\n"),
            text_file("tsconfig.json", "{}\n"),
        )
    )
    files = ProjectFiles(starter, {"reference": ProjectTree((text_file("src/bank.ts"),))})
    meta = replace(problem.meta, languages=(Language.TYPESCRIPT,), project=Project("src/bank.ts"))
    return replace(problem, meta=meta, project_files=files)


def test_the_typescript_fixture_passes(bank):
    assert errors(content(typescript(bank))) == []


@pytest.mark.parametrize("type_text", ["decimal", "list<decimal>"])
def test_a_typescript_project_signature_has_no_decimal(bank, type_text):
    assert signature_errors(with_constructor_param(typescript(bank), type_text)) == [
        f"{META}: signature: {type_text}: a TypeScript project cannot reach the Decimal class "
        "of the runner's support module"
    ]


def test_a_project_problem_has_exactly_one_approach(bank):
    approaches = (bank.meta.approaches[0], replace(bank.meta.approaches[0], id="ledger"))
    problem = with_meta(bank, approaches=approaches)
    assert f"{META}: approaches: a project problem has exactly one approach (has 2)" in errors(
        content(problem)
    )


def test_a_project_problem_has_no_oracle(bank):
    problem = with_meta(bank, approaches=(replace(bank.meta.approaches[0], oracle=True),))
    assert f"{META}: approaches[0]: a project problem has no oracle" in errors(content(problem))


@pytest.mark.parametrize("name", ["generator.py", "checker.py", "stress_checker.py"])
def test_a_project_problem_has_no_generator_or_checker(bank, name):
    found = errors(content(bank, files=("meta.yaml", "problem.md", "tests.json", name)))
    assert f"{DIRECTORY}/{name}: a project problem has none" in found


def test_a_project_problem_has_no_buggy_stub(bank):
    found = errors(content(bank, buggy_files=("solution.py",)))
    assert f"{DIRECTORY}/buggy: a project problem has none" in found


def test_a_project_problem_has_no_generate_cases(bank):
    problem = replace(bank, cases=(*bank.cases, Case("g1", GeneratedInput(10, 1), level=2)))
    assert f"{TESTS}: cases[6] g1: a project problem has no generate cases" in errors(
        content(problem)
    )


def test_a_project_problem_has_no_stress_cases(bank):
    stress = StressScenario(OperationSequence(("Bank",), ((),)), ())
    problem = replace(bank, cases=(*bank.cases, Case("s1", stress, level=2)))
    assert f"{TESTS}: cases[6] s1: a project problem has no stress cases" in errors(
        content(problem)
    )


# S15


def starter_errors(problem) -> list[str]:
    return [issue for issue in errors(content(problem)) if issue.startswith(STARTER)]


def test_a_project_problem_has_a_starter(bank):
    problem = replace(bank, project_files=ProjectFiles(None, project_files(bank).overlays))
    assert errors(content(problem)) == [f"{STARTER}: missing (kind: project)"]


def test_the_starter_has_a_readme(bank):
    assert errors(content(without_starter_files(bank, "README.md"))) == [
        f"{STARTER}/README.md: missing"
    ]


def test_the_starter_holds_the_entry_file(bank):
    assert errors(content(without_starter_files(bank, "bank/bank.py"))) == [
        f"{STARTER}: has no bank/bank.py or bank/bank/__init__.py for the entry bank.bank"
    ]


def test_a_python_entry_may_be_a_package(bank):
    package = text_file("bank/bank/__init__.py")
    problem = with_starter(without_starter_files(bank, "bank/bank.py"), package)
    assert errors(content(problem)) == []


def numbered_files(count: int) -> tuple[ProjectFile, ...]:
    return tuple(text_file(f"notes/{number:02}.md") for number in range(count))


def test_the_starter_may_hold_50_files(bank):
    problem = with_starter(bank, *numbered_files(50 - len(starter_files(bank))))
    assert starter_errors(problem) == []


def test_the_starter_holds_at_most_50_files(bank):
    problem = with_starter(bank, *numbered_files(51 - len(starter_files(bank))))
    assert starter_errors(problem) == [f"{STARTER}: holds 51 files; at most 50 are allowed"]


def padding(total: int, problem) -> ProjectFile:
    """A file that brings the starter's size to `total` bytes."""
    used = sum(file.size for file in starter_files(problem))
    return text_file("notes.md", "x" * (total - used))


def test_the_starter_may_hold_256_kib(bank):
    assert starter_errors(with_starter(bank, padding(MAX_STARTER_BYTES, bank))) == []


def test_the_starter_holds_at_most_256_kib(bank):
    problem = with_starter(bank, padding(MAX_STARTER_BYTES + 1, bank))
    assert starter_errors(problem) == [
        f"{STARTER}: holds {MAX_STARTER_BYTES + 1} bytes; at most 256 KiB are allowed"
    ]


def test_the_starter_holds_text_only(bank):
    problem = with_starter(bank, ProjectFile("logo.png", 70, None))
    assert errors(content(problem)) == [f"{STARTER}/logo.png: is not UTF-8 text"]


def test_a_cache_directory_is_reported_once(bank):
    problem = with_starter(
        bank,
        ProjectFile("bank/__pycache__/bank.cpython-313.pyc", 10, None),
        ProjectFile("bank/__pycache__/models.cpython-313.pyc", 10, None),
    )
    assert errors(content(problem)) == [f"{STARTER}/bank/__pycache__: is build output or a cache"]


@pytest.mark.parametrize(
    "path",
    [".venv/bin/python", "node_modules/x/index.js", ".pytest_cache/README.md", ".ruff_cache/a"],
)
def test_the_starter_holds_no_caches(bank, path):
    cache = path.partition("/")[0]
    problem = with_starter(bank, text_file(path))
    assert errors(content(problem)) == [f"{STARTER}/{cache}: is build output or a cache"]


@pytest.mark.parametrize("path", ["bank.pyc", "tsconfig.tsbuildinfo"])
def test_the_starter_holds_no_build_output(bank, path):
    problem = with_starter(bank, text_file(path))
    assert errors(content(problem)) == [f"{STARTER}/{path}: is build output or a cache"]


@pytest.mark.parametrize("name", ["uv.lock", "package-lock.json", "pnpm-lock.yaml"])
def test_the_starter_holds_no_lock_files(bank, name):
    problem = with_starter(bank, text_file(name))
    assert errors(content(problem)) == [f"{STARTER}/{name}: is a lock file"]


def test_a_python_starter_has_a_pyproject(bank):
    assert errors(content(without_starter_files(bank, "pyproject.toml"))) == [
        f"{STARTER}/pyproject.toml: missing"
    ]


@pytest.mark.parametrize(
    ("toml", "issue"),
    [
        ('[project]\nname = "bank"\n', "has a [project] table"),
        ("[tool.uv]\npackage = false\n", "has a [tool.uv] table"),
        ('[tool.other]\nrequires-python = ">=3.14"\n', "sets requires-python"),
    ],
    ids=["project", "tool.uv", "requires-python"],
)
def test_a_python_starter_pyproject_holds_tool_settings_only(bank, toml, issue):
    problem = with_starter(bank, text_file("pyproject.toml", toml))
    assert errors(content(problem)) == [f"{STARTER}/pyproject.toml: {issue}"]


def test_a_python_starter_pyproject_is_valid_toml(bank):
    problem = with_starter(bank, text_file("pyproject.toml", "[tool.pytest\n"))
    [issue] = errors(content(problem))
    assert issue.startswith(f"{STARTER}/pyproject.toml: is not valid TOML: ")


@pytest.mark.parametrize(
    ("path", "module", "where"),
    [
        ("random.py", "random", "random.py"),
        ("typing.py", "typing", "typing.py"),
        ("json/encoder.py", "json", "json"),
        ("email/parser/headers.py", "email", "email"),
    ],
)
def test_a_python_starter_does_not_shadow_the_standard_library(bank, path, module, where):
    problem = with_starter(bank, text_file(path))
    assert errors(content(problem)) == [
        f'{STARTER}/{where}: is named after the standard-library module "{module}"'
    ]


def test_a_python_starter_does_not_shadow_pytest(bank):
    problem = with_starter(bank, text_file("pytest.py"))
    assert errors(content(problem)) == [f'{STARTER}/pytest.py: is named after the module "pytest"']


def test_a_directory_without_python_files_is_no_module(bank):
    assert errors(content(with_starter(bank, text_file("string/notes.md")))) == []


def test_a_typescript_starter_has_its_build_files(bank):
    problem = without_starter_files(typescript(bank), "package.json", "tsconfig.json")
    assert errors(content(problem)) == [
        f"{STARTER}/package.json: missing",
        f"{STARTER}/tsconfig.json: missing",
    ]


@pytest.mark.parametrize(
    ("package", "issue"),
    [
        ("{}", 'needs "type": "module"'),
        ('{"type": "commonjs"}', 'needs "type": "module"'),
        ('{"type": "module", "dependencies": {"left-pad": "1.0.0"}}', "declares dependencies"),
        ('{"type": "module", "devDependencies": {"vitest": "2"}}', "declares devDependencies"),
        ("[]", "is not a JSON object"),
    ],
    ids=["no type", "commonjs", "dependencies", "devDependencies", "array"],
)
def test_a_typescript_package_is_a_module_without_dependencies(bank, package, issue):
    problem = with_starter(typescript(bank), text_file("package.json", package))
    assert errors(content(problem)) == [f"{STARTER}/package.json: {issue}"]


def test_a_typescript_package_may_list_no_dependencies(bank):
    package = '{"type": "module", "dependencies": {}}'
    assert errors(content(with_starter(typescript(bank), text_file("package.json", package)))) == []


def test_a_typescript_package_is_valid_json(bank):
    problem = with_starter(typescript(bank), text_file("package.json", "{"))
    [issue] = errors(content(problem))
    assert issue.startswith(f"{STARTER}/package.json: is not valid JSON: ")


def test_an_overlay_holds_text_only(bank):
    overlay = ProjectTree((text_file("bank/bank.py"), ProjectFile("bank/data.bin", 4, None)))
    assert errors(content(with_overlays(bank, reference=overlay))) == [
        f"{SOLUTIONS}/reference/bank/data.bin: is not UTF-8 text"
    ]


# S16


@pytest.mark.parametrize("path", ["tests/test_level_1.py", "tests/unit/test_level_12.py"])
def test_no_starter_file_under_tests_has_a_generated_test_name(bank, path):
    assert errors(content(with_starter(bank, text_file(path)))) == [
        f"{STARTER}/{path}: has the name of a generated test file"
    ]


@pytest.mark.parametrize(
    "path", ["tests/test_bank.py", "tests/test_level_x.py", "other/test_level_1.py"]
)
def test_other_test_files_are_the_authors_to_ship(bank, path):
    assert errors(content(with_starter(bank, text_file(path)))) == []


def test_generated_test_names_follow_the_tests_directory(bank):
    problem = with_meta(bank, project=Project("bank.bank", "checks"))
    problem = with_starter(problem, text_file("checks/test_level_2.py"))
    assert errors(content(problem)) == [
        f"{STARTER}/checks/test_level_2.py: has the name of a generated test file"
    ]


def test_a_typescript_starter_holds_no_generated_test_name(bank):
    problem = with_starter(typescript(bank), text_file("tests/level-2.test.ts"))
    assert errors(content(problem)) == [
        f"{STARTER}/tests/level-2.test.ts: has the name of a generated test file"
    ]


def test_problem_md_has_a_project_section(bank):
    text = (FIXTURE / "problem.md").read_text()
    markdown = text[: text.index("## Project")] + text[text.index("## Level 1") :]
    assert errors(content(bank, problem_markdown=markdown)) == [f'{PROBLEM}: missing "## Project"']


def test_the_project_section_is_not_empty(bank):
    text = (FIXTURE / "problem.md").read_text()
    markdown = (
        text[: text.index("## Project")] + "## Project\n\n" + text[text.index("## Level 1") :]
    )
    assert errors(content(bank, problem_markdown=markdown)) == [f'{PROBLEM}: "## Project" is empty']


def test_the_project_section_comes_after_the_output(bank):
    text = (FIXTURE / "problem.md").read_text()
    output, project = text.index("## Output"), text.index("## Project")
    level = text.index("## Level 1")
    markdown = text[:output] + text[project:level] + text[output:project] + text[level:]
    assert errors(content(bank, problem_markdown=markdown)) == [
        f'{PROBLEM}: "## Project" must come after "## Output"'
    ]


def test_the_explanation_has_a_design(bank):
    explanation = edited_explanation(
        "### Design\n\n- `bank/bank.py`: the `Bank` class and the balances it keeps.\n\n", ""
    )
    assert errors(content(bank, explanation=explanation)) == [
        f'{EXPLANATION}: missing "### Design" in approach reference'
    ]


def test_the_design_is_not_empty(bank):
    explanation = edited_explanation(
        "- `bank/bank.py`: the `Bank` class and the balances it keeps.\n", ""
    )
    assert errors(content(bank, explanation=explanation)) == [
        f'{EXPLANATION}: "### Design" is empty in approach reference'
    ]


def test_the_design_comes_after_the_algorithm(bank):
    text = (FIXTURE / "solutions" / "explanation.md").read_text()
    intuition, design = text.index("### Intuition"), text.index("### Design")
    correctness = text.index("### Correctness")
    explanation = (
        text[:intuition] + text[design:correctness] + text[intuition:design] + text[correctness:]
    )
    assert errors(content(bank, explanation=explanation)) == [
        f'{EXPLANATION}: "### Design" must come after "### Algorithm" in approach reference'
    ]


# ready criteria


def test_a_project_problem_meets_the_level_ready_criteria(bank):
    cases = tuple(replace(case, visible=False) if case.id == "ex2" else case for case in bank.cases)
    problem = replace(bank, cases=cases)
    assert "level 2 needs at least 1 visible case (has 0)" in ready_problems(content(problem))
