"""What kind of Docker this is, found without `sudo` and without changing anything
(docs/specs/service-projects.md#docker-states).

The group comes from the group database and this process's own groups. The setup comes from the
address the Docker client talks to, which `DOCKER_HOST` or the current context sets, and, for the
system engine's address, from whether systemd's `docker.socket` is listening.
"""

import grp
import os
import pwd
from collections.abc import Collection, Sequence
from typing import Protocol

from coding_study.application.ports import ProbeResult
from coding_study.domain.docker_engine import DockerGroup, EngineSetup

DOCKER_GROUP = "docker"
SETUP_QUERY_S = 10.0
CONTEXT_ENDPOINT = ("docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}")
SOCKET_LISTENING = ("systemctl", "is-active", "docker.socket")
SYSTEM_ENDPOINTS = frozenset(("unix:///var/run/docker.sock", "unix:///run/docker.sock"))
_ACTIVE = "active"
_ROOTLESS_SOCKET = "docker.sock"


class SetupRunner(Protocol):
    def run(self, command: Sequence[str], timeout_s: float | None = None) -> ProbeResult | None:
        """None when the executable is missing."""
        ...


def docker_group_standing(
    group: grp.struct_group | None, user: str, primary_gid: int, session_gids: Collection[int]
) -> DockerGroup:
    """`primary_gid` is the database's, and `session_gids` are this process's groups."""
    if group is None:
        return DockerGroup.NOT_A_MEMBER
    if group.gr_gid in session_gids:
        return DockerGroup.IN_SESSION
    if user in group.gr_mem or primary_gid == group.gr_gid:
        return DockerGroup.NOT_YET_IN_SESSION
    return DockerGroup.NOT_A_MEMBER


def docker_group_of_this_process() -> DockerGroup:
    account = pwd.getpwuid(os.getuid())
    try:
        group = grp.getgrnam(DOCKER_GROUP)
    except KeyError:
        group = None
    session = {*os.getgroups(), os.getegid()}
    return docker_group_standing(group, account.pw_name, account.pw_gid, session)


def engine_setup(runner: SetupRunner, uid: int, runtime_directory: str | None) -> EngineSetup:
    """Asks the client's address and systemd's state; starts nothing."""
    endpoint = _endpoint(runner)
    if endpoint in _rootless_endpoints(uid, runtime_directory):
        return EngineSetup.ROOTLESS
    if endpoint not in SYSTEM_ENDPOINTS:
        return EngineSetup.OTHER
    listening = runner.run(SOCKET_LISTENING, SETUP_QUERY_S)
    if listening is not None and listening.exit_code == 0 and listening.output.strip() == _ACTIVE:
        return EngineSetup.SOCKET_ACTIVATED
    return EngineSetup.SYSTEM


def _endpoint(runner: SetupRunner) -> str | None:
    found = runner.run(CONTEXT_ENDPOINT, SETUP_QUERY_S)
    if found is None or found.exit_code != 0:
        return None
    return found.output.strip()


def _rootless_endpoints(uid: int, runtime_directory: str | None) -> set[str]:
    directories = {f"/run/user/{uid}"}
    if runtime_directory:
        directories.add(runtime_directory.rstrip("/"))
    return {f"unix://{directory}/{_ROOTLESS_SOCKET}" for directory in directories}
