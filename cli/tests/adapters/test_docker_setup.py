"""Where you stand with the docker group, from the group database and this process's groups."""

import grp

from coding_study.adapters.docker_setup import docker_group_of_this_process, docker_group_standing
from coding_study.domain.docker_engine import DockerGroup

DOCKER_GID = 986
USER = "ada"
USER_GID = 1000


def docker_group(*members: str) -> grp.struct_group:
    return grp.struct_group(("docker", "x", DOCKER_GID, list(members)))


def test_a_member_of_the_database_whose_session_lacks_the_group_is_not_yet_in_it():
    standing = docker_group_standing(docker_group(USER), USER, USER_GID, [USER_GID, 27])

    assert standing is DockerGroup.NOT_YET_IN_SESSION


def test_the_primary_group_of_the_database_counts_as_membership():
    standing = docker_group_standing(docker_group(), USER, DOCKER_GID, [USER_GID])

    assert standing is DockerGroup.NOT_YET_IN_SESSION


def test_a_session_that_has_the_group_is_in_it():
    standing = docker_group_standing(docker_group(USER), USER, USER_GID, [USER_GID, DOCKER_GID])

    assert standing is DockerGroup.IN_SESSION


def test_someone_the_database_does_not_list_is_not_a_member():
    standing = docker_group_standing(docker_group("grace"), USER, USER_GID, [USER_GID])

    assert standing is DockerGroup.NOT_A_MEMBER


def test_a_machine_without_a_docker_group_has_no_member():
    assert docker_group_standing(None, USER, USER_GID, [USER_GID]) is DockerGroup.NOT_A_MEMBER


def test_this_process_has_a_standing():
    assert docker_group_of_this_process() in set(DockerGroup)
