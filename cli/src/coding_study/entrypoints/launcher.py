"""The `cstudy` console script.

Importing the CLI (Typer, Rich, jsonschema) takes a noticeable moment; Ctrl-C during it would
end the process by signal. Importing it here, inside the handler, makes that exit 130 like a
Ctrl-C at any later point (docs/specs/cli.md#exit-codes). This module imports nothing heavy.
"""

import sys
from importlib import import_module

CLI_MODULE = "coding_study.entrypoints.cli"
INTERRUPTED_EXIT_CODE = 130
"""`ExitCode.INTERRUPTED`, without importing `entrypoints.shared` and its libraries."""


def main() -> None:
    try:
        import_module(CLI_MODULE).main()
    except KeyboardInterrupt:
        sys.exit(INTERRUPTED_EXIT_CODE)
