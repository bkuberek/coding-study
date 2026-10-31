"""`cstudy new`: scaffold a draft problem from a template (docs/specs/cli.md#cstudy-new).

Writes the template files with their placeholders filled in and the files the track needs (an
`lld` rubric), then one empty reference file per declared approach and language, read back from
the new meta.yaml, and for concurrent problems one empty broken reference file per broken id and
language; a project template holds its starter and its reference overlay instead. Slugs are
unique across problems/ and tracks/. The problem goes to the environment's destination: an
editable content checkout, or the workspace's own problems/ numbered from 5001.
"""

from dataclasses import dataclass

from coding_study.application.environment import Environment
from coding_study.application.ports import ProblemTemplates
from coding_study.domain.errors import UsageError
from coding_study.domain.layout import reference_file_name
from coding_study.domain.problem import ProblemKind, ProblemMeta
from coding_study.domain.problem_files import broken_file, solution_file
from coding_study.domain.scaffold import (
    ScaffoldRequest,
    TemplateName,
    next_problem_id,
    plan_scaffold,
    render_template,
)


@dataclass(frozen=True, slots=True)
class CreatedProblem:
    slug: str
    directory: str
    """Relative to the destination root, e.g. `problems/0004-max-gap`."""
    template: TemplateName
    files: tuple[str, ...]
    """Relative to `directory`, in the order written."""


def create_problem(
    environment: Environment, templates: ProblemTemplates, request: ScaffoldRequest
) -> CreatedProblem:
    """Raises UsageError when a problem or item has the slug, or the request is invalid."""
    _require_new_slug(environment, request.slug)
    destination = environment.new_problems
    problems = destination.files
    problem_id = next_problem_id(problems.directory_names(), destination.first_id)
    scaffold = plan_scaffold(request, problem_id)
    directory = f"{problems.directory}/{scaffold.directory_name}"
    placeholders = scaffold.placeholders()
    written: list[str] = []
    for template_path, text in sorted(templates.files(request.template).items()):
        name = render_template(template_path, placeholders)
        destination.writer.write_text(f"{directory}/{name}", render_template(text, placeholders))
        written.append(name)
    for name, text in scaffold.track_files().items():
        destination.writer.write_text(f"{directory}/{name}", text)
        written.append(name)
    meta = environment.problems.load(scaffold.slug).meta
    for name in _empty_references(meta):
        destination.writer.write_text(f"{directory}/{name}", "")
        written.append(name)
    return CreatedProblem(scaffold.slug, directory, request.template, tuple(written))


def _empty_references(meta: ProblemMeta) -> list[str]:
    """One file per approach and language, and per broken reference of a concurrent problem;
    none for a project problem, whose template holds its reference's overlay."""
    if meta.kind is ProblemKind.PROJECT:
        return []
    names = [
        solution_file(reference_file_name(approach.id, language))
        for approach in meta.approaches
        for language in meta.languages
    ]
    if meta.concurrency is not None:
        names += [
            broken_file(reference_file_name(broken.id, language))
            for broken in meta.concurrency.broken
            for language in meta.languages
            if broken.covers(language, meta.languages)
        ]
    return names


def _require_new_slug(environment: Environment, slug: str) -> None:
    problems = environment.files
    existing = dict(zip(problems.slugs(), problems.directory_names(), strict=True))
    if slug in existing:
        raise UsageError(f"{slug} already exists: {problems.directory}/{existing[slug]}")
    if slug in environment.items.slugs():
        raise UsageError(f"{slug} already exists: {environment.items.item_directory(slug)}")
