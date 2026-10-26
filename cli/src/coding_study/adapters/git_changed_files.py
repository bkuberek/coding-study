"""`ChangedFiles` from git, run in the repository root.

`git diff <merge-base>` compares the working tree (committed, staged and unstaged changes) with
the point where the branch left `base`, and `git ls-files --others` adds untracked files.
Both list paths relative to the root and only below it, NUL-separated (`-z`).
"""

import subprocess
from pathlib import Path

from coding_study.domain.errors import VersionControlError

GIT = "git"


class GitChangedFiles:
    def __init__(self, root: Path, executable: str = GIT) -> None:
        self._root = root
        self._executable = executable

    def changed_since(self, base: str) -> tuple[str, ...]:
        merge_base = self._git("merge-base", base, "HEAD").strip()
        changed = self._git("diff", "--name-only", "--no-renames", "--relative", "-z", merge_base)
        untracked = self._git("ls-files", "--others", "--exclude-standard", "-z")
        paths = {path for path in (*changed.split("\0"), *untracked.split("\0")) if path}
        return tuple(sorted(paths))

    def _git(self, *arguments: str) -> str:
        try:
            completed = subprocess.run(
                [self._executable, *arguments],
                cwd=self._root,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            raise VersionControlError(f"{self._executable} not found on PATH") from None
        if completed.returncode != 0:
            reason = completed.stderr.strip().splitlines()[-1:] or ["no output"]
            command = " ".join((GIT, *arguments))
            raise VersionControlError(f"{command} failed in {self._root}: {reason[0]}")
        return completed.stdout
