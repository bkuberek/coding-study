from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LanguageContext:
    """What every runner factory receives; new fields get defaults so factories keep working."""

    workspace: Path
    """The absolute workspace root: the practice projects and `.cs/` live under it."""
    runners: Path
    """The absolute runners directory the practice projects build against (`<name>/` each)."""
