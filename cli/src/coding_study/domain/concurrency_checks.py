"""`cstudy verify --static` checks S11 and S12 on concurrent problems
(docs/specs/authoring.md#static).

S11 covers the problem: kind and track, models per language, files a concurrent problem may not
have, and the `## Concurrency` section. S12 covers the stress cases (steps, templates, harness
ops, selectors, limits) and the broken references with their explanation sections.
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from coding_study.domain.cases import Case, JsonValue, OperationSequence
from coding_study.domain.concurrency import BROKEN_PREFIX, Concurrency, model_problems
from coding_study.domain.errors import ContentIssue
from coding_study.domain.explanation import Explanation
from coding_study.domain.layout import SOURCE_EXTENSIONS, language_of_extension
from coding_study.domain.markdown import MarkdownDocument
from coding_study.domain.problem import ProblemKind, ProblemMeta, Track
from coding_study.domain.problem_files import (
    EXPLANATION_FILE,
    GENERATOR_FILE,
    META_FILE,
    PROBLEM_FILE,
    STRESS_CHECKER_FILE,
    TESTS_FILE,
    broken_file,
)
from coding_study.domain.signature import ClassSignature, Method
from coding_study.domain.stress import (
    HARNESS_ARITY,
    MAX_PAUSE,
    SECTION_MODES,
    ArithmeticSequence,
    CheckerInvariant,
    HarnessOp,
    Literal,
    Pick,
    RandomInteger,
    Selector,
    Step,
    StressScenario,
    Template,
    WorkerGroup,
    invariant_selectors,
    is_harness_op,
)
from coding_study.domain.type_dsl import Scalar, ScalarType, ValueType, VoidType
from coding_study.domain.value_checks import input_value_issues, output_value_issues
from coding_study.domain.value_text import value_text

CONCURRENCY_SECTION = "Concurrency"
CONSTRAINTS_SECTION = "Constraints"
BROKEN_SUBSECTIONS = ("Bug", "Failing interleaving", "Fix")
MIN_WORKERS = 2
MAX_WORKERS = 64
MAX_OPS_PER_RUN = 20_000
_INTEGER_SCALARS = (Scalar.INT, Scalar.LONG)


@dataclass(frozen=True, slots=True)
class ConcurrencyContent:
    """What S11 and S12 read from one problem directory."""

    directory: str
    meta: ProblemMeta
    cases: tuple[Case, ...]
    problem_markdown: str | None
    explanation: str | None
    files: tuple[str, ...]
    """File names directly in the problem directory."""
    broken_files: tuple[str, ...]
    """File names in solutions/broken/."""


def concurrency_issues(content: ConcurrencyContent) -> tuple[ContentIssue, ...]:
    """S11 and S12; nothing for problems that are neither concurrent nor in that track."""
    meta = content.meta
    is_concurrent = meta.kind is ProblemKind.CONCURRENT
    if not is_concurrent and meta.track is not Track.CONCURRENCY:
        return ()
    issues = _Issues(content.directory)
    if is_concurrent != (meta.track is Track.CONCURRENCY):
        issues.error(META_FILE, "kind concurrent goes with track concurrency, and only with it")
    concurrency = meta.concurrency
    if concurrency is None or not isinstance(meta.signature, ClassSignature):
        return tuple(issues.errors)
    _Problem(issues, content, concurrency).check()
    stress = _Stress(issues, meta, meta.signature)
    for index, case in enumerate(content.cases):
        if isinstance(case.input, StressScenario):
            stress.check(f"cases[{index}] {case.id}", case.input)
    stress.check_checker_file(content)
    return tuple(issues.errors)


class _Issues:
    def __init__(self, directory: str) -> None:
        self._directory = directory
        self.errors: list[ContentIssue] = []

    def error(self, name: str, message: str, location: str = "") -> None:
        self.errors.append(ContentIssue(f"{self._directory}/{name}", location, message))


class _Problem:
    """S11 and the broken-reference part of S12."""

    def __init__(self, issues: _Issues, content: ConcurrencyContent, concurrency: Concurrency):
        self._issues = issues
        self._content = content
        self._concurrency = concurrency

    def check(self) -> None:
        meta = self._content.meta
        for problem in model_problems(self._concurrency, meta.languages):
            self._issues.error(META_FILE, problem, "concurrency.model")
        if GENERATOR_FILE in self._content.files:
            self._issues.error(GENERATOR_FILE, "concurrent problems have no generator")
        self._concurrency_section()
        self._broken_ids()
        self._broken_files()
        self._broken_sections()

    def _concurrency_section(self) -> None:
        markdown = self._content.problem_markdown
        if markdown is None:
            return
        document = MarkdownDocument(markdown)
        titles = [section.title for section in document.sections(2)]
        section = document.section(CONCURRENCY_SECTION)
        if section is None:
            self._issues.error(PROBLEM_FILE, f'missing "## {CONCURRENCY_SECTION}"')
        elif not section.text:
            self._issues.error(PROBLEM_FILE, f'"## {CONCURRENCY_SECTION}" is empty')
        elif CONSTRAINTS_SECTION in titles and titles.index(CONCURRENCY_SECTION) < titles.index(
            CONSTRAINTS_SECTION
        ):
            message = f'"## {CONCURRENCY_SECTION}" must come after "## {CONSTRAINTS_SECTION}"'
            self._issues.error(PROBLEM_FILE, message)

    def _broken_ids(self) -> None:
        approaches = {approach.id for approach in self._content.meta.approaches}
        seen: set[str] = set()
        for index, broken in enumerate(self._concurrency.broken):
            location = f"concurrency.broken[{index}]"
            if broken.id in approaches or broken.id in seen:
                self._issues.error(META_FILE, f'duplicate id "{broken.id}"', location)
            seen.add(broken.id)
            stress_ids = {
                case.id for case in self._content.cases if isinstance(case.input, StressScenario)
            }
            for case_id in broken.caught_by:
                if case_id not in stress_ids:
                    message = f'caught_by "{case_id}" is not a stress case'
                    self._issues.error(META_FILE, message, location)
            outside = [
                language
                for language in broken.languages or ()
                if language not in self._content.meta.languages
            ]
            if outside:
                listed = ", ".join(outside)
                self._issues.error(META_FILE, f"languages not in languages: {listed}", location)
        for approach in sorted(approaches):
            if approach.startswith(BROKEN_PREFIX):
                message = f'approach "{approach}" may not start with "{BROKEN_PREFIX}"'
                self._issues.error(META_FILE, message, "approaches")

    def _broken_files(self) -> None:
        meta = self._content.meta
        expected = {
            f"{broken.id}.{SOURCE_EXTENSIONS[language]}"
            for broken in self._concurrency.broken
            for language in meta.languages
            if broken.covers(language, meta.languages)
        }
        present = set(self._content.broken_files)
        for name in sorted(present - expected):
            stem, _, extension = name.rpartition(".")
            known = self._concurrency.broken_reference(stem) is not None
            if known and language_of_extension(extension) is not None:
                message = "its language is not in the broken reference's languages"
            else:
                message = "maps to no broken reference in concurrency.broken"
            self._issues.error(broken_file(name), message)
        for name in sorted(expected - present):
            self._issues.error(broken_file(name), "missing (declared in concurrency.broken)")

    def _broken_sections(self) -> None:
        text = self._content.explanation
        if text is None:
            return
        explanation = Explanation(text)
        found = {section.broken_id: section for section in explanation.broken()}
        for broken_id in found.keys() - {broken.id for broken in self._concurrency.broken}:
            self._error(f'"## Broken: {broken_id}" names no broken reference in meta.yaml')
        declared = [broken.id for broken in self._concurrency.broken]
        in_file = [section.broken_id for section in explanation.broken()]
        if [item for item in in_file if item in declared] != [
            item for item in declared if item in found
        ]:
            self._error(
                f"broken sections must follow concurrency.broken order: {', '.join(declared)}"
            )
        for broken in self._concurrency.broken:
            section = found.get(broken.id)
            if section is None:
                self._error(f'missing "## Broken: {broken.id} ({broken.name})"')
                continue
            if section.name != broken.name:
                self._error(
                    f'broken {broken.id} is named "{broken.name}" in meta.yaml, '
                    f'not "{section.name}"'
                )
            subsections = {
                sub.title: sub for sub in explanation.document.sections(3, section.section)
            }
            for title in BROKEN_SUBSECTIONS:
                sub = subsections.get(title)
                if sub is None or not sub.text:
                    state = "missing" if sub is None else "empty"
                    self._error(f'"### {title}" is {state} in broken {broken.id}')

    def _error(self, message: str) -> None:
        self._issues.error(EXPLANATION_FILE, message)


class _Stress:
    """S12 for one stress case at a time."""

    def __init__(self, issues: _Issues, meta: ProblemMeta, signature: ClassSignature) -> None:
        self._issues = issues
        self._meta = meta
        self._signature = signature
        self._methods = {method.name: method for method in signature.methods}
        self._uses_checker = False

    def check(self, location: str, scenario: StressScenario) -> None:
        errors = [
            *self._setup(scenario.setup),
            *self._final(scenario),
            *self._limits(scenario),
            *(problem for group in scenario.workers for problem in self._group(group)),
            *self._selectors(scenario),
        ]
        groups = [group.group for group in scenario.workers]
        errors += [f'duplicate group "{name}"' for name in _duplicates(groups)]
        for message in errors:
            self._issues.error(TESTS_FILE, message, location)
        if any(isinstance(item, CheckerInvariant) for item in scenario.invariants):
            self._uses_checker = True

    def check_checker_file(self, content: ConcurrencyContent) -> None:
        present = STRESS_CHECKER_FILE in content.files
        if self._uses_checker and not present:
            self._issues.error(
                STRESS_CHECKER_FILE, "missing (a stress case has a checker invariant)"
            )
        if present and not self._uses_checker:
            self._issues.error(
                STRESS_CHECKER_FILE, "present but no stress case has a checker invariant"
            )

    def _setup(self, setup: OperationSequence) -> Iterator[str]:
        if setup.ops[0] != self._signature.name:
            yield f'setup.ops[0]: expected the class name "{self._signature.name}"'
        else:
            params = self._signature.constructor_params
            yield from _argument_problems(
                tuple(param.type for param in params), setup.args[0], "setup.args[0]"
            )
        yield from self._calls(setup.ops[1:], setup.args[1:], "setup", first=1)

    def _final(self, scenario: StressScenario) -> Iterator[str]:
        final = scenario.final
        if final is None:
            return
        yield from self._calls(final.ops, final.args, "final", first=0)
        if final.expected is None:
            return
        if len(final.expected) != len(final.ops):
            yield f"final.expected: {len(final.expected)} values for {len(final.ops)} operations"
            return
        for index, (op, value) in enumerate(zip(final.ops, final.expected, strict=True)):
            method = self._methods.get(op)
            if method is not None:
                yield from _return_problems(method, value, f"final.expected[{index}]")

    def _calls(
        self,
        ops: Sequence[str],
        args: Sequence[tuple[JsonValue, ...]],
        label: str,
        first: int,
    ) -> Iterator[str]:
        if len(ops) != len(args):
            yield f"{label}: {len(args)} argument arrays for {len(ops)} operations"
            return
        for offset, (op, arguments) in enumerate(zip(ops, args, strict=True)):
            index = first + offset
            method = self._methods.get(op)
            if method is None:
                yield f'{label}.ops[{index}]: no method "{op}"'
                continue
            types = tuple(param.type for param in method.params)
            yield from _argument_problems(types, arguments, f"{label}.args[{index}]")

    def _limits(self, scenario: StressScenario) -> Iterator[str]:
        workers = scenario.worker_count
        if not MIN_WORKERS <= workers <= MAX_WORKERS:
            yield f"{workers} workers; a stress case runs {MIN_WORKERS} to {MAX_WORKERS}"
        for language in self._meta.languages:
            ops = scenario.ops_per_run(language)
            if ops > MAX_OPS_PER_RUN:
                yield f"{ops} ops per run in {language}; at most {MAX_OPS_PER_RUN}"

    def _group(self, group: WorkerGroup) -> Iterator[str]:
        label = f"workers[{group.group}]"
        for position, step in enumerate(group.steps):
            yield from self._step(step, group, f"{label}.steps[{position}]")
        iterations = [[step] for step in group.steps] if group.is_mix else [list(group.steps)]
        for steps in iterations:
            problem = _section_nesting(steps)
            if problem is not None:
                yield f"{label}: {problem}"
                break

    def _step(self, step: Step, group: WorkerGroup, label: str) -> Iterator[str]:
        if is_harness_op(step.op):
            yield from _harness_problems(step, label)
            return
        if step.op == self._signature.name:
            yield f'{label}: the constructor "{step.op}" is not allowed in steps'
            return
        method = self._methods.get(step.op)
        if method is None:
            yield f'{label}: no method "{step.op}"'
            return
        if len(step.args) != len(method.params):
            noun = "argument" if len(method.params) == 1 else "arguments"
            yield f"{label}: {step.op} takes {len(method.params)} {noun}, got {len(step.args)}"
            return
        repeat = group.repeat.largest
        for position, (param, template) in enumerate(zip(method.params, step.args, strict=True)):
            yield from _template_problems(
                template, param.type, _Span(group.count, repeat), f"{label}.args[{position}]"
            )

    def _selectors(self, scenario: StressScenario) -> Iterator[str]:
        groups = {group.group for group in scenario.workers}
        for index, invariant in enumerate(scenario.invariants):
            for selector in invariant_selectors(invariant):
                yield from self._selector(selector, groups, f"invariants[{index}]")

    def _selector(self, selector: Selector, groups: set[str], label: str) -> Iterator[str]:
        method = self._methods.get(selector.op)
        if method is None:
            yield f'{label}: no method "{selector.op}"'
            return
        argument = selector.argument_index
        if argument is not None and argument >= len(method.params):
            yield f"{label}: {selector.op} has no argument {argument}"
        if argument is None and isinstance(method.returns.type, VoidType):
            yield f"{label}: {selector.op} returns nothing; select an argument instead"
        if selector.group is not None and selector.group not in groups:
            yield f'{label}: no worker group "{selector.group}"'


@dataclass(frozen=True, slots=True)
class _Span:
    workers: int
    iterations: int


def _template_problems(
    template: Template, value_type: ValueType, span: _Span, label: str
) -> Iterator[str]:
    match template:
        case Literal(value=value):
            yield from (f"{label}: {issue}" for issue in input_value_issues(value, value_type))
        case ArithmeticSequence(start=start, worker_stride=stride, step=step):
            extremes = {
                start + worker * stride + iteration * step
                for worker in (0, span.workers - 1)
                for iteration in (0, span.iterations - 1)
            }
            yield from _integer_template_problems(sorted(extremes), value_type, label)
        case RandomInteger(low=low, high=high):
            if low > high:
                yield f"{label}: $rand needs low <= high, got [{low}, {high}]"
            yield from _integer_template_problems([low, high], value_type, label)
        case Pick(values=values):
            for value in values:
                for issue in input_value_issues(value, value_type):
                    yield f"{label}: $pick value {value_text(value)}: {issue}"


def _integer_template_problems(
    values: list[int], value_type: ValueType, label: str
) -> Iterator[str]:
    if not (isinstance(value_type, ScalarType) and value_type.scalar in _INTEGER_SCALARS):
        yield f"{label}: integer templates need an int or long parameter, not {value_type}"
        return
    for value in (values[0], values[-1]):
        yield from (f"{label}: {issue}" for issue in input_value_issues(value, value_type))


def _harness_problems(step: Step, label: str) -> Iterator[str]:
    if step.op not in HarnessOp:
        yield f'{label}: unknown harness op "{step.op}"'
        return
    harness = HarnessOp(step.op)
    arity = HARNESS_ARITY[harness]
    if len(step.args) != arity:
        yield f"{label}: {step.op} takes {arity} arguments, got {len(step.args)}"
        return
    values = [template.value if isinstance(template, Literal) else None for template in step.args]
    if any(not isinstance(template, Literal) for template in step.args):
        yield f"{label}: harness ops take literal arguments"
        return
    match harness:
        case HarnessOp.ENTER:
            if not isinstance(values[0], str) or values[1] not in SECTION_MODES:
                yield f'{label}: @enter takes a section name and "exclusive" or "shared"'
        case HarnessOp.EXIT:
            if not isinstance(values[0], str):
                yield f"{label}: @exit takes a section name"
        case HarnessOp.PAUSE:
            count = values[0]
            if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= MAX_PAUSE:
                yield f"{label}: @pause takes a count from 1 to {MAX_PAUSE}"


def _section_nesting(steps: Sequence[Step]) -> str | None:
    """Why `@enter`/`@exit` are not balanced and properly nested within one iteration."""
    open_sections: list[str] = []
    for step in steps:
        name = step.args[0].value if step.args and isinstance(step.args[0], Literal) else None
        if step.op == HarnessOp.ENTER:
            open_sections.append(str(name))
        elif step.op == HarnessOp.EXIT:
            if not open_sections or open_sections[-1] != str(name):
                return f'@exit "{name}" does not close the section entered last'
            open_sections.pop()
    if open_sections:
        return f'@enter "{open_sections[-1]}" has no @exit in the same iteration'
    return None


def _argument_problems(
    types: tuple[ValueType, ...], arguments: tuple[JsonValue, ...], label: str
) -> Iterator[str]:
    if len(arguments) != len(types):
        yield f"{label}: {len(types)} arguments expected, got {len(arguments)}"
        return
    for position, (value_type, value) in enumerate(zip(types, arguments, strict=True)):
        for issue in input_value_issues(value, value_type):
            yield f"{label}[{position}]: {issue}"


def _return_problems(method: Method, value: JsonValue, label: str) -> Iterator[str]:
    returns = method.returns.type
    if isinstance(returns, VoidType):
        if value is not None:
            yield f"{label}: void returns expect null"
        return
    yield from (f"{label}: {issue}" for issue in output_value_issues(value, returns))


def _duplicates(names: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    repeated: list[str] = []
    for name in names:
        if name in seen and name not in repeated:
            repeated.append(name)
        seen.add(name)
    return repeated
