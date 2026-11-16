"""`cstudy ai` (docs/specs/cli.md#cstudy-ai): the AI preview. `key` keeps a provider's key in
`credentials.toml`; it needs no workspace. `status`, `usage` and `consent` read and write the
workspace's records. Each works with AI off."""

import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text
from typer._click import Context as ClickContext
from typer.core import TyperCommand

from coding_study.adapters.environment_factory import load_environment
from coding_study.adapters.locations import workspace_directory
from coding_study.adapters.toml_credentials import open_credentials
from coding_study.application.ai_consent import grant, parse_model, parse_purpose, revoke
from coding_study.application.ai_keys import parse_provider, remove_key, save_key
from coding_study.application.ai_status import ai_status
from coding_study.application.ai_usage import DEFAULT_DAYS, MAX_DAYS, MIN_DAYS, usage_report
from coding_study.application.environment import Environment
from coding_study.domain.ai import Provider
from coding_study.domain.ai_routing import task_spec
from coding_study.entrypoints.commands.ai_check import check, models
from coding_study.entrypoints.commands.ai_report import (
    shown_path,
    status_document,
    status_lines,
    usage_document,
    usage_lines,
)
from coding_study.entrypoints.commands.ai_review import review
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "ai"
PROVIDER_HELP = "anthropic, google, openai or openrouter."
NO_KEY_ARGUMENT = "cstudy ai key takes the provider only: it asks for the key"


def register(app: typer.Typer) -> None:
    group = typer.Typer(help="Set up the AI preview (off by default).", no_args_is_help=True)
    add_command(group, status, "status")
    add_command(group, usage, "usage")
    add_command(group, key, "key", _KeyCommand)
    add_command(group, consent, "consent")
    add_command(group, models, "models")
    add_command(group, check, "check")
    add_command(group, review, "review")
    app.add_typer(group, name=NAME)


class _KeyCommand(TyperCommand):
    """Refuses a second argument without echoing it: it may be a key."""

    def parse_args(self, ctx: ClickContext, args: list[str]) -> list[str]:
        if sum(not argument.startswith("-") for argument in args) > 1:
            raise typer.BadParameter(NO_KEY_ARGUMENT)
        return super().parse_args(ctx, args)


def key(
    context: typer.Context,
    provider: Annotated[str, typer.Argument(help=PROVIDER_HELP)],
    remove: Annotated[
        bool, typer.Option("--remove", help="Delete the provider's key instead of setting it.")
    ] = False,
) -> None:
    """Keep a provider's key in credentials.toml, asked for with a hidden prompt."""
    chosen = parse_provider(provider)
    environ = command_environ(context)
    credentials = open_credentials(environ, Path.home(), workspace_directory(Path.cwd(), environ))
    output = console(context)
    if remove:
        removed = remove_key(credentials, chosen)
        output.print(Text(f"{chosen} key removed" if removed else f"{chosen} has no key"))
        return
    location = save_key(credentials, chosen, _asked_for(chosen))
    output.print(Text(f"{chosen} key saved in {shown_path(location, Path.home())}"))


def _asked_for(provider: Provider) -> str:
    """The key: a hidden prompt at a terminal, else one line of standard input."""
    if sys.stdin.isatty():
        return typer.prompt(f"{provider} key", hide_input=True, default="", show_default=False)
    return sys.stdin.readline().rstrip("\r\n")


def status(
    context: typer.Context,
    as_json: Annotated[bool, typer.Option("--json", help="Machine-readable output.")] = False,
) -> None:
    """Show the AI settings, what each task would use, the keys, the consents and today's usage."""
    environment = _environment(context)
    report = ai_status(environment)
    if as_json:
        typer.echo(json.dumps(status_document(report), indent=2))
        return
    output = console(context)
    for line in status_lines(report, environment.clock.local_date, Path.home()):
        output.print(Text(line))


def usage(
    context: typer.Context,
    days: Annotated[
        int,
        typer.Option("--days", help=f"Days to cover, today included ({MIN_DAYS} to {MAX_DAYS})."),
    ] = DEFAULT_DAYS,
    as_json: Annotated[bool, typer.Option("--json", help="Machine-readable output.")] = False,
) -> None:
    """Show the AI requests of the last days, by day, provider, model and purpose."""
    report = usage_report(_environment(context), days)
    if as_json:
        typer.echo(json.dumps(usage_document(report), indent=2))
        return
    output = console(context)
    for line in usage_lines(report):
        output.print(Text(line))


def consent(
    context: typer.Context,
    model: Annotated[str, typer.Argument(help="<provider>:<model id>, such as anthropic:<id>.")],
    purpose: Annotated[str, typer.Option("--purpose", help="review or check.")],
    revoke_it: Annotated[
        bool, typer.Option("--revoke", help="Remove the consent instead of recording it.")
    ] = False,
) -> None:
    """Record, or with --revoke remove, your consent to send to a model for a purpose."""
    chosen = parse_model(model)
    task = parse_purpose(purpose)
    environment = _environment(context)
    name = task_spec(task).name
    output = console(context)
    if revoke_it:
        removed = revoke(environment, chosen, task)
        output.print(
            Text(
                f"consent revoked: {chosen} for {name}"
                if removed
                else f"no consent to revoke for {chosen} and {name}"
            )
        )
        return
    grant(environment, chosen, task)
    output.print(Text(f"consent recorded: {chosen} for {name}"))


def _environment(context: typer.Context) -> Environment:
    return load_environment(Path.cwd(), command_environ(context), Path.home())
