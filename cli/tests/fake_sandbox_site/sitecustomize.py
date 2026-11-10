"""Loaded by every Python process with this folder on `PYTHONPATH`: a browser test's `cstudy serve`
and the `cstudy` children it starts. When the environment names a script folder, the fake Docker
of `tests/scripted_sandbox.py` takes the place of `DockerSandbox`, before anything imports it."""

import os

if os.environ.get("CSTUDY_TEST_SANDBOX"):
    from coding_study.adapters import docker_sandbox
    from tests.scripted_sandbox import ScriptedSandbox

    docker_sandbox.DockerSandbox = ScriptedSandbox  # type: ignore[misc]
