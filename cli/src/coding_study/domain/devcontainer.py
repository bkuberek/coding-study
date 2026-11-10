"""The `devcontainer.json` that `cstudy dev` writes in a service project's `.devcontainer/`
(docs/specs/service-projects.md#your-own-ide).

VS Code and IntelliJ start your IDE's container from it: the dev stack's image, the project folder
at its same path, and the dev stack's `sandbox` network, so its mock servers and backing services
answer by their names there as they do to your app, and nothing beyond the stack does. The network
is there only while `cstudy dev` runs. The container runs as you, as the stack does, so what you
write there is yours on your machine too.

Both IDEs read the file as JSON with comments. Its first line says `cstudy` wrote it, and `cstudy`
writes it again while that line is there: delete the line, and your edits stay.
"""

import json

from coding_study.domain.sandbox import (
    DEVCONTAINER_DIRECTORY,
    HOME_DIRECTORY,
    NO_NEW_PRIVILEGES,
    SANDBOX_NETWORK,
    StackPlan,
)

DEVCONTAINER_FILE = f"{DEVCONTAINER_DIRECTORY}/devcontainer.json"
"""Relative to the project folder."""
GENERATED_LINE = "// Written by cstudy dev, which writes it again while this line is here."
INDENT = 2


def devcontainer_text(plan: StackPlan) -> str:
    """The file for the dev stack of `plan`, its first line `GENERATED_LINE`."""
    project = plan.paths.project
    document = {
        "name": f"{plan.identity.slug} (cstudy dev)",
        "image": plan.app.image,
        "workspaceMount": f"source={project},target={project},type=bind",
        "workspaceFolder": project,
        "runArgs": [
            f"--network={_compose_network(plan, SANDBOX_NETWORK)}",
            f"--user={plan.user.spec}",
            "--cap-drop=ALL",
            f"--security-opt={NO_NEW_PRIVILEGES}",
        ],
        "containerEnv": {**plan.app.environment, "HOME": HOME_DIRECTORY},
    }
    return f"{GENERATED_LINE}\n{json.dumps(document, indent=INDENT)}\n"


def is_generated(text: str) -> bool:
    """Whether `cstudy` may write the file again: its first line is still `GENERATED_LINE`."""
    return text.split("\n", 1)[0] == GENERATED_LINE


def _compose_network(plan: StackPlan, network: str) -> str:
    """Compose names a network it creates `<project>_<network>`."""
    return f"{plan.identity.name}_{network}"
