"""`cstudy ai` (docs/specs/cli.md#cstudy-ai): the AI preview. `key` keeps a provider's key in
`credentials.toml`; it needs no workspace and works with AI off."""

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.text import Text
from typer._click import Context as ClickContext
from typer.core import TyperCommand

from coding_study.adapters.locations import workspace_directory
from coding_study.adapters.toml_credentials import open_credentials
from coding_study.application.ai_keys import parse_provider, remove_key, save_key
from coding_study.domain.ai import Provider
from coding_study.entrypoints.shared import add_command, command_environ, console

NAME = "ai"
HOME = "~"
PROVIDER_HELP = "anthropic, google, openai or openrouter."
NO_KEY_ARGUMENT = "cstudy ai key takes the provider only: it asks for the key"


def register(app: typer.Typer) -> None:
    group = typer.Typer(help="Set up the AI preview (off by default).", no_args_is_help=True)
    add_command(group, key, "key", _KeyCommand)
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
    output.print(Text(f"{chosen} key saved in {_shown(location)}"))


def _asked_for(provider: Provider) -> str:
    """The key: a hidden prompt at a terminal, else one line of standard input."""
    if sys.stdin.isatty():
        return typer.prompt(f"{provider} key", hide_input=True, default="", show_default=False)
    return sys.stdin.readline().rstrip("\r\n")


def _shown(location: str) -> str:
    path = Path(location)
    home = Path.home()
    return f"{HOME}/{path.relative_to(home).as_posix()}" if path.is_relative_to(home) else location
