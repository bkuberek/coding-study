"""The program: reads the rendered config, serves, and ends at once on SIGTERM or SIGINT."""

import argparse
import json
import os
import signal
import sys
from collections.abc import Sequence
from pathlib import Path
from types import FrameType

from .config import ConfigError, load_stack_config
from .http_server import (
    DEFAULT_API_PORT,
    DEFAULT_BIND_ADDRESS,
    DEFAULT_CONTROL_PORT,
    ListenOn,
    start_servers,
)

EXIT_CLEAN = 0
EXIT_CANNOT_LISTEN = 1
EXIT_BAD_CONFIG = 2
ENDING_SIGNALS = (signal.SIGTERM, signal.SIGINT)


def main(arguments: Sequence[str]) -> int:
    config_path, listen = parse_options(arguments)
    for ending_signal in ENDING_SIGNALS:
        signal.signal(ending_signal, _exit_at_once)
    try:
        config = load_stack_config(config_path)
        servers = start_servers(config, listen)
    except ConfigError as error:
        print(f"mock server: {error}", file=sys.stderr)
        return EXIT_BAD_CONFIG
    except OSError as error:
        print(f"mock server: cannot listen: {error}", file=sys.stderr)
        return EXIT_CANNOT_LISTEN
    listening = {
        "api_port": servers.api_port,
        "control_port": servers.control_port,
        "mocks": [mock.name for mock in config.mocks],
    }
    print(json.dumps(listening), flush=True)
    while True:
        signal.pause()


def parse_options(arguments: Sequence[str]) -> tuple[Path, ListenOn]:
    parser = argparse.ArgumentParser(prog="mock_server", description=__doc__)
    parser.add_argument("config", type=Path, help="the rendered JSON config")
    parser.add_argument("--bind", default=DEFAULT_BIND_ADDRESS, help="the address to listen on")
    parser.add_argument(
        "--api-port", type=int, default=DEFAULT_API_PORT, help="where the mocked APIs answer"
    )
    parser.add_argument(
        "--control-port",
        type=int,
        default=DEFAULT_CONTROL_PORT,
        help="where the control interface and the health endpoint answer",
    )
    options = parser.parse_args(arguments)
    return options.config, ListenOn(options.bind, options.api_port, options.control_port)


def _exit_at_once(_signal_number: int, _frame: FrameType | None) -> None:
    """All state is in memory, so nothing is left to save. Finalizing the interpreter would wait on
    or race the daemon threads still sleeping through a delay."""
    os._exit(EXIT_CLEAN)
