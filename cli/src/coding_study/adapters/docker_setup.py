"""Where you stand with the docker group, found without `sudo` and without changing anything
(docs/specs/service-projects.md#the-docker-group): from the group database and this process's own
groups.
"""

import grp
import os
import pwd
from collections.abc import Collection

from coding_study.domain.docker_engine import DockerGroup

DOCKER_GROUP = "docker"


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
