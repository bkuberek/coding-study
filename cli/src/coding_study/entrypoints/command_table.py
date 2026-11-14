"""`cstudy`'s command line as the user docs' D6 check reads it (docs/specs/user-docs.md#accuracy):
every command, subcommand and flag, from the Click command tree Typer builds."""

from typer._click import Command
from typer.core import TyperGroup, TyperOption

from coding_study.domain.doc_checks import CommandSpec

HELP = "--help"
"""Every command takes it; Click adds it outside the command's parameters."""


def command_spec(command: Command) -> CommandSpec:
    """`command`, `cstudy`'s group or one of its commands, with its flags and subcommands."""
    options = {
        name: not (parameter.is_flag or parameter.count)
        for parameter in command.params
        if isinstance(parameter, TyperOption)
        for name in (*parameter.opts, *parameter.secondary_opts)
    }
    subcommands = (
        {name: command_spec(sub) for name, sub in command.commands.items()}
        if isinstance(command, TyperGroup)
        else {}
    )
    return CommandSpec(options={**options, HELP: False}, subcommands=subcommands)
