"""The environment a process starts with when `cstudy` runs user code, or a tool on it
(docs/specs/runners.md#process-environment).

Every adapter that starts such a process begins from `inherited_environment` and adds its own
variables; none passes `os.environ` on. What is let through is decided in
`coding_study.domain.process_environment`.
"""

import os

from coding_study.domain.process_environment import allowed_environment


def inherited_environment() -> dict[str, str]:
    """The environment of this process, reduced to what user code and the tooling on it may
    inherit."""
    return allowed_environment(os.environ)
