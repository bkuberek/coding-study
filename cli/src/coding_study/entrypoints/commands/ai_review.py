"""`cstudy ai review` (docs/specs/cli.md#cstudy-ai-review): reviews a rubric problem's notes
against its rubric, and lists, shows and dismisses the stored reviews."""

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.environment_factory import load_environment
from coding_study.application.ai_ports import LanguageModels
from coding_study.application.ai_review import (
    Reviewed,
    ReviewView,
    dismiss_review,
    dry_run_review,
    list_reviews,
    prepare_review,
    run_review,
    show_review,
)
from coding_study.application.environment import Environment
from coding_study.domain.ai import AiTask, ApiKey, Provider
from coding_study.domain.ai_models import ModelReply, ModelRequest
from coding_study.domain.ai_routing import task_spec
from coding_study.domain.errors import UsageError
from coding_study.entrypoints.commands.ai_consent_prompt import TerminalAsker
from coding_study.entrypoints.commands.ai_review_report import (
    dry_run_text,
    list_document,
    list_lines,
    review_document,
    review_lines,
)
from coding_study.entrypoints.shared import command_environ, console


class _AnnouncingModels:
    """The models of the environment, saying what they are about to do just before a request
    leaves: after the consent question, and after every refusal."""

    def __init__(self, models: LanguageModels, announce: Callable[[], None]) -> None:
        self._models = models
        self._announce = announce

    def complete(self, request: ModelRequest, key: ApiKey) -> ModelReply:
        self._announce()
        return self._models.complete(request, key)

    def list_models(self, provider: Provider, key: ApiKey, deadline_s: float) -> tuple[str, ...]:
        return self._models.list_models(provider, key, deadline_s)


def review(
    context: typer.Context,
    slug: Annotated[
        str | None,
        typer.Argument(help="The rubric problem; default: the problem of the active attempt."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print what a review would send, and send nothing."),
    ] = False,
    list_it: Annotated[
        bool, typer.Option("--list", help="List the problem's reviews, newest first.")
    ] = False,
    show: Annotated[
        int | None, typer.Option("--show", metavar="ID", help="Show one stored review.")
    ] = None,
    dismiss: Annotated[
        int | None, typer.Option("--dismiss", metavar="ID", help="Dismiss a stored review.")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Machine-readable output.")] = False,
) -> None:
    """Review your notes on a rubric problem against its rubric; an AI review changes no grade."""
    forms = [
        name
        for name, chosen in (
            ("--dry-run", dry_run),
            ("--list", list_it),
            ("--show", show is not None),
            ("--dismiss", dismiss is not None),
        )
        if chosen
    ]
    _check_form(forms, slug, as_json)
    environment = load_environment(Path.cwd(), command_environ(context), Path.home())
    if dry_run:
        typer.echo(dry_run_text(dry_run_review(environment, slug)), nl=False)
    elif list_it:
        _list(context, environment, slug, as_json)
    elif show is not None:
        _show(context, show_review(environment, show), as_json)
    elif dismiss is not None:
        dismissal = dismiss_review(environment, dismiss)
        name = dismissal.review.slug
        console(context).print(
            Text(
                f"AI review {dismiss} is already dismissed"
                if dismissal.already_dismissed
                else f"dismissed AI review {dismiss} of {name}"
            )
        )
    else:
        _review(context, environment, slug, as_json)


def _check_form(forms: list[str], slug: str | None, as_json: bool) -> None:
    """Raises UsageError for flags that do not go together."""
    if len(forms) > 1:
        raise UsageError(f"{' and '.join(forms)} cannot be used together")
    form = forms[0] if forms else None
    if as_json and form in ("--dry-run", "--dismiss"):
        raise UsageError(f"--json does not apply to {form}")
    if slug is not None and form in ("--show", "--dismiss"):
        raise UsageError(f"{form} takes a review id, not a problem")


def _list(
    context: typer.Context, environment: Environment, slug: str | None, as_json: bool
) -> None:
    listing = list_reviews(environment, slug)
    if as_json:
        typer.echo(json.dumps(list_document(listing), indent=2))
        return
    output = console(context)
    for line in list_lines(listing, environment.clock.local_date):
        output.print(Text(line))


def _show(context: typer.Context, view: ReviewView, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(review_document(view), indent=2))
        return
    output = console(context)
    for line in review_lines(view):
        output.print(Text(line))


def _review(
    context: typer.Context, environment: Environment, slug: str | None, as_json: bool
) -> None:
    prepared = prepare_review(environment, slug)
    target = prepared.target

    def announce() -> None:
        seconds = task_spec(AiTask.REVIEW).deadline_s
        typer.echo(f"reviewing with {target.model}, up to {seconds:g} s", err=True)

    announcing = replace(environment, models=_AnnouncingModels(environment.models, announce))
    result = run_review(announcing, prepared, TerminalAsker(subject=prepared.plan.meta.slug))
    if not isinstance(result, Reviewed):
        typer.echo("not sent", err=as_json)
        return
    _show(context, result.review, as_json)
