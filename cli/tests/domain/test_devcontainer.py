"""The `devcontainer.json` that `cstudy dev` writes for your own IDE."""

import json
from typing import Any

from coding_study.domain.devcontainer import (
    DEVCONTAINER_FILE,
    GENERATED_LINE,
    devcontainer_text,
    is_generated,
)
from coding_study.domain.sandbox import (
    AppContainer,
    SandboxPaths,
    SandboxUser,
    StackIdentity,
    StackKind,
    StackPlan,
)

PROJECT = "/work/projects/rooms"
IMAGE = "node:24-slim@sha256:0123"
PLAN = StackPlan(
    identity=StackIdentity("cstudy-d-rooms-d1g3st", StackKind.DEV, "d1g3st", "rooms", 41),
    user=SandboxUser(501, 20),
    paths=SandboxPaths(project=PROJECT, run="/work/.cs/runs/cstudy-d-rooms-d1g3st"),
    app=AppContainer(IMAGE, ("node", "src/server.ts"), 8000, {"PORT": "8000"}),
)


def document() -> dict[str, Any]:
    return json.loads(devcontainer_text(PLAN).split("\n", 1)[1])


def test_it_lives_in_the_projects_devcontainer_folder():
    assert DEVCONTAINER_FILE == ".devcontainer/devcontainer.json"


def test_its_first_line_says_cstudy_wrote_it():
    assert devcontainer_text(PLAN).split("\n", 1)[0] == GENERATED_LINE


def test_it_names_the_dev_stacks_image():
    assert document()["image"] == IMAGE


def test_it_mounts_the_project_folder_at_its_same_path():
    found = document()

    assert found["workspaceMount"] == f"source={PROJECT},target={PROJECT},type=bind"
    assert found["workspaceFolder"] == PROJECT


def test_it_joins_the_dev_stacks_sandbox_network():
    assert "--network=cstudy-d-rooms-d1g3st_sandbox" in document()["runArgs"]


def test_it_runs_as_you_as_the_stack_does():
    assert "--user=501:20" in document()["runArgs"]


def test_it_holds_no_capability_and_gains_no_privilege():
    run_arguments = document()["runArgs"]

    assert "--cap-drop=ALL" in run_arguments
    assert "--security-opt=no-new-privileges:true" in run_arguments


def test_it_sets_the_projects_variables_and_a_writable_home():
    assert document()["containerEnv"] == {"PORT": "8000", "HOME": "/tmp/home"}


def test_a_file_that_starts_with_cstudys_line_is_cstudys():
    assert is_generated(devcontainer_text(PLAN))


def test_a_file_without_cstudys_first_line_is_yours():
    assert not is_generated(f'{{"image": "mine"}}\n{GENERATED_LINE}\n')
