"""Asking `cstudy` for a fresh runner process (docs/specs/runners.md#exit-codes-hang-guard-and-
restarts-additions)."""


class RestartRequestError(Exception):
    """A stress run, or a case on the virtual clock, left threads alive; the runner writes
    `restart_requested` and exits with code 3."""
