"""What migrating progress.db did, and the line that says it
(docs/specs/compatibility.md#migrations)."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProgressMigration:
    found: int
    """The schema the database was at."""
    latest: int
    """The schema it is at now."""
    backup: str | None
    """The copy made first, relative to the workspace; None for a database that was new."""

    @property
    def notice(self) -> str:
        if self.backup is None:
            return f"progress.db: migrated from schema {self.found} to {self.latest}"
        return (
            f"progress.db: backed up to {self.backup}; "
            f"migrated from schema {self.found} to {self.latest}"
        )
