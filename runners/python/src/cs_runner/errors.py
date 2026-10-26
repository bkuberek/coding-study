"""Why a request, a case input or a return value cannot be used."""


class BadRequestError(Exception):
    """The request file cannot be run at all (exit code 2)."""


class CaseInputError(Exception):
    """A case input that does not fit its declared type; reported as a case error."""


class InvalidOutputError(Exception):
    """A return value that cannot be serialized as its declared type (`invalid_output`)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
