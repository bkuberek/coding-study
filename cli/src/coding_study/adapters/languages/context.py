from dataclasses import dataclass, field
from pathlib import Path

from coding_study.adapters.jdk_locator import JdkHome, shell_jdk


@dataclass(frozen=True, slots=True)
class LanguageContext:
    """What every runner factory receives; new fields get defaults so factories keep working."""

    workspace: Path
    """The absolute workspace root: the practice projects and `.cs/` live under it."""
    runners: Path
    """The absolute runners directory the practice projects build against (`<name>/` each)."""
    jdk: JdkHome = field(default_factory=shell_jdk)
    """The JDK Java and Kotlin build and run with: the one the shell selects."""
