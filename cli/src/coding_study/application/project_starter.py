"""A project problem's starter as a project folder receives it
(docs/specs/service-projects.md#env).

No starter holds a `.env`, which S15 refuses. A service project's is written from `project.env`, so
the manifest is its only source, and in the folder it is a file like any other: tracked, hashed
and archived.
"""

from coding_study.domain.problem import Problem
from coding_study.domain.project import ProjectFile, ProjectTree
from coding_study.domain.service_project import ENV_FILE, env_file_text, service_of


def provided_starter(problem: Problem) -> ProjectTree | None:
    """What `cstudy` copies into a folder or a build; None for a problem without a starter."""
    files = problem.project_files
    starter = files.starter if files else None
    service = service_of(problem.meta)
    if starter is None or service is None:
        return starter
    text = env_file_text(service.env)
    env = ProjectFile(ENV_FILE, len(text.encode()), text)
    others = (file for file in starter.files if file.path != ENV_FILE)
    return ProjectTree(tuple(sorted((*others, env), key=lambda file: file.path)))
