"""S14, S15, S19 and S22 as they stand for a service project."""

import pytest

from coding_study.domain.problem import (
    Approach,
    ApproachRole,
    ComparatorSpec,
    ComparatorType,
    ContentStatus,
    Difficulty,
    Language,
    Level,
    ProblemKind,
    ProblemMeta,
    Track,
)
from coding_study.domain.project import NO_ENTRY, Project, ProjectFile, ProjectTree
from coding_study.domain.service_checks import service_issues, service_settings_issues
from coding_study.domain.service_project import (
    ServiceApp,
    ServiceCommands,
    ServiceMock,
    ServiceProject,
    ServiceRequires,
    ServiceSizes,
    env_file_text,
)
from coding_study.domain.signature import NO_SIGNATURE

IMAGE = "node:24-slim@sha256:01d566e8d94d8c619591d78652babfccd3c6992a3dffa9ed5ab39e11cf6c70e9"
INSTALL = ("corepack", "pnpm", "install", "--frozen-lockfile", "--ignore-scripts")
SIZES = ServiceSizes(install_mb=40, images_mb={"app": 80, "forwarder": 41}, memory_mb=700)


def service(**changes) -> ServiceProject:
    fields = {
        "image": IMAGE,
        "commands": ServiceCommands(run=("node", "s.ts"), test=("node", "--test"), install=INSTALL),
        "app": ServiceApp("PORT", 8000, "/health"),
        "env": {"PORT": "8000"},
        "requires": ServiceRequires(lock="pnpm-lock.yaml", sizes=SIZES),
        **changes,
    }
    return ServiceProject(**fields)


def meta_of(project: ServiceProject, **changes) -> ProblemMeta:
    fields = {
        "id": "0001",
        "slug": "rooms-typescript",
        "title": "Rooms",
        "status": ContentStatus.DRAFT,
        "difficulty": Difficulty.MEDIUM,
        "track": Track.PRACTICAL,
        "kind": ProblemKind.PROJECT,
        "signature": NO_SIGNATURE,
        "comparator": ComparatorSpec(ComparatorType.EXACT),
        "approaches": (Approach("reference", "R", ApproachRole.OPTIMAL, "t", "s", None, None),),
        "languages": (Language.TYPESCRIPT,),
        "levels": (Level(1, "One"),),
        "project": Project(NO_ENTRY, service=project),
        **changes,
    }
    return ProblemMeta(**fields)


def tree(**texts: str) -> ProjectTree:
    return ProjectTree(
        tuple(
            ProjectFile(path.replace("__", "."), len(text.encode()), text)
            for path, text in texts.items()
        )
    )


PACKAGE = (
    '{"type": "module", "packageManager": "pnpm@10.0.0", '
    '"devDependencies": {"typescript": "^6.0.0"}}'
)


def starter(**changes: str) -> ProjectTree:
    files = {
        "README__md": "# Rooms",
        "package__json": PACKAGE,
        "pnpm-lock__yaml": "lockfileVersion: '9.0'\n",
        **changes,
    }
    return tree(**files)


def settings(project: ServiceProject, **changes) -> list[str]:
    issues = service_settings_issues(meta_of(project, **changes), project)
    return [f"{where}: {message}" for where, message in issues]


def tree_issues(project: ServiceProject, files: ProjectTree | None = None) -> list[str]:
    return [
        f"{path}: {message}"
        for path, message in service_issues(meta_of(project), project, files or starter())
    ]


def test_a_well_formed_service_project_has_no_issue():
    assert settings(service()) == []
    assert tree_issues(service()) == []


def test_a_track_other_than_practical_is_allowed():
    assert settings(service(), track=Track.DEBUGGING) == []


def test_a_service_project_lists_exactly_one_language():
    found = settings(service(), languages=(Language.TYPESCRIPT, Language.PYTHON))

    assert "languages: a project problem lists exactly one language" in found


def test_a_service_project_has_exactly_one_approach():
    approach = Approach("a", "A", ApproachRole.OPTIMAL, "t", "s", None, None)

    assert any(
        "exactly one approach" in text
        for text in settings(service(), approaches=(approach, approach))
    )


def test_the_image_is_pinned_by_digest():
    assert any("digest" in text for text in settings(service(image="node:24-slim")))


def test_install_is_required_with_a_lock():
    project = service(commands=ServiceCommands(run=("r",), test=("t",)))

    assert any("install" in text for text in settings(project))


def test_a_lock_is_required_with_install():
    project = service(requires=ServiceRequires(sizes=SIZES))

    assert any("needs requires.lock" in text for text in settings(project))


@pytest.mark.parametrize(
    "command",
    [
        ("pnpm", "install"),
        ("corepack", "pnpm", "install", "--ignore-scripts"),
        ("corepack", "pnpm", "install", "--frozen-lockfile"),
    ],
)
def test_pnpm_must_use_the_lock_exactly_and_run_no_install_script(command):
    project = service(commands=ServiceCommands(run=("r",), test=("t",), install=command))

    assert any("pnpm" in text and "--" in text for text in settings(project))


@pytest.mark.parametrize(
    "command", [("uv", "sync"), ("uv", "sync", "--frozen"), ("uv", "sync", "--no-build")]
)
def test_uv_must_use_the_lock_exactly_and_build_nothing(command):
    project = service(commands=ServiceCommands(run=("r",), test=("t",), install=command))

    assert any("uv" in text and "--" in text for text in settings(project))


def test_uv_with_both_flags_is_fine():
    command = ("uv", "sync", "--frozen", "--no-build")
    project = service(
        commands=ServiceCommands(run=("r",), test=("t",), install=command),
        requires=ServiceRequires(lock="uv.lock", sizes=SIZES),
    )

    assert settings(project) == []


def test_another_tools_install_is_judged_by_what_it_does():
    project = service(
        commands=ServiceCommands(run=("r",), test=("t",), install=("my-tool", "fetch"))
    )

    assert settings(project) == []


def test_bootstrap_is_required_with_services():
    project = service(
        services="services/compose.yaml",
        requires=ServiceRequires(lock="pnpm-lock.yaml", services=("postgres",), sizes=SIZES),
    )

    assert any("bootstrap" in text for text in settings(project))


def test_the_problem_placeholder_is_refused_outside_grade_setup():
    project = service(
        commands=ServiceCommands(run=("x", "{problem}/a"), test=("t",), install=INSTALL)
    )

    assert any("{problem}" in text for text in settings(project))


def test_grade_setup_must_point_outside_the_starter():
    command = ("node", "scripts/setup.ts")
    project = service(
        commands=ServiceCommands(run=("r",), test=("t",), install=INSTALL, grade_setup=command)
    )

    assert any("grade_setup" in text for text in settings(project))


def test_grade_setup_in_the_problems_files_is_fine():
    command = ("node", "{problem}/grading/setup.ts")
    project = service(
        commands=ServiceCommands(run=("r",), test=("t",), install=INSTALL, grade_setup=command)
    )

    assert settings(project) == []


def test_env_holds_the_port_variable_with_the_apps_port():
    assert any("PORT" in text for text in settings(service(env={"PORT": "9999"})))
    assert any("PORT" in text for text in settings(service(env={})))


def test_a_url_names_a_declared_mock_server_on_its_port():
    project = service(
        env={"PORT": "8000", "ROOM_URL": "http://room-vendor:8080"},
        mocks=(ServiceMock("room-vendor", "mocks/room-vendor.yaml"),),
        requires=ServiceRequires(
            lock="pnpm-lock.yaml",
            sizes=ServiceSizes(40, {"app": 80, "mocks": 41}, 700),
        ),
    )

    assert settings(project) == []


def test_a_url_to_nothing_declared_is_refused():
    project = service(env={"PORT": "8000", "ROOM_URL": "http://room-vendor:8080"})

    assert any("room-vendor" in text for text in settings(project))


def test_a_url_to_a_mock_server_on_another_port_is_refused():
    project = service(
        env={"PORT": "8000", "ROOM_URL": "http://room-vendor:9090"},
        mocks=(ServiceMock("room-vendor", "m.yaml"),),
    )

    assert any("8080" in text for text in settings(project))


def test_a_url_to_this_machine_is_refused():
    project = service(env={"PORT": "8000", "ROOM_URL": "http://localhost:3000"})

    assert any("localhost" in text for text in settings(project))


def test_a_url_with_declared_services_may_name_a_service():
    sizes = ServiceSizes(40, {"app": 80, "postgres": 160}, 700)
    project = service(
        env={"PORT": "8000", "DATABASE_URL": "postgres://app:app@db:5432/app"},
        services="services/compose.yaml",
        commands=ServiceCommands(run=("r",), test=("t",), install=INSTALL, bootstrap=("b",)),
        requires=ServiceRequires(lock="pnpm-lock.yaml", services=("postgres",), sizes=sizes),
    )

    assert settings(project) == []


def test_mock_names_are_unique():
    mock = ServiceMock("room-vendor", "m.yaml")

    assert any("unique" in text for text in settings(service(mocks=(mock, mock))))


@pytest.mark.parametrize("name", ["app", "cstudy-mocks", "cstudy-forward", "bootstrap"])
def test_a_mock_may_not_take_a_reserved_name(name):
    assert any(
        "reserved" in text for text in settings(service(mocks=(ServiceMock(name, "m.yaml"),)))
    )


def test_at_most_four_mock_servers():
    mocks = tuple(ServiceMock(f"m{index}", "m.yaml") for index in range(5))

    assert any("at most 4" in text for text in settings(service(mocks=mocks)))


def test_the_app_port_cannot_be_the_control_port_with_mock_servers():
    project = service(
        app=ServiceApp("PORT", 9000, "/health"),
        env={"PORT": "9000"},
        mocks=(ServiceMock("room-vendor", "m.yaml"),),
    )

    assert any("9000" in text for text in settings(project))


def test_services_and_requires_services_go_together():
    project = service(
        requires=ServiceRequires(lock="pnpm-lock.yaml", services=("postgres",), sizes=SIZES)
    )

    assert any("requires.services" in text for text in settings(project))


def test_every_image_has_a_size_row():
    project = service(
        requires=ServiceRequires(lock="pnpm-lock.yaml", sizes=ServiceSizes(40, {}, 700))
    )

    assert any("images_mb" in text and "app" in text for text in settings(project))


def test_mock_servers_need_a_size_row_for_the_mock_image():
    project = service(mocks=(ServiceMock("room-vendor", "m.yaml"),))

    assert any("images_mb" in text and "mocks" in text for text in settings(project))


def test_memory_and_install_sizes_are_declared():
    project = service(
        requires=ServiceRequires(lock="pnpm-lock.yaml", sizes=ServiceSizes(None, {"app": 80}, None))
    )

    found = settings(project)
    assert any("memory_mb" in text for text in found)
    assert any("install_mb" in text for text in found)


def test_a_starter_needs_a_readme():
    files = tree(__env="PORT=8000\n", package__json=PACKAGE, **{"pnpm-lock__yaml": "x"})

    assert any("README.md" in text for text in tree_issues(service(), files))


def test_a_starter_is_required():
    assert service_issues(meta_of(service()), service(), None)


def test_the_declared_lock_is_required_in_the_starter():
    files = tree(README__md="x", __env="PORT=8000\n", package__json=PACKAGE)

    assert any(
        "pnpm-lock.yaml" in text and "missing" in text for text in tree_issues(service(), files)
    )


def test_another_lock_file_is_refused():
    assert any("yarn.lock" in text for text in tree_issues(service(), starter(yarn__lock="x")))


def test_the_lock_is_outside_the_starters_size_limit():
    big = "x" * (300 * 1024)

    assert tree_issues(service(), starter(**{"pnpm-lock__yaml": big})) == []


def test_other_files_stay_inside_the_size_limit():
    big = "x" * (300 * 1024)

    assert any("KiB" in text for text in tree_issues(service(), starter(big__txt=big)))


def test_the_file_count_leaves_the_lock_out():
    many = {f"f{index}__txt": "x" for index in range(46)}

    assert tree_issues(service(), starter(**many)) == []


def test_too_many_files_are_refused():
    many = {f"f{index}__txt": "x" for index in range(60)}

    assert any("at most 50" in text for text in tree_issues(service(), starter(**many)))


def test_a_cache_in_the_starter_is_refused():
    files = ProjectTree((*starter().files, ProjectFile("node_modules/a.js", 1, "x")))

    assert any("node_modules" in text for text in tree_issues(service(), files))


def test_a_file_that_is_not_text_is_refused():
    files = ProjectTree((*starter().files, ProjectFile("logo.png", 1, None)))

    assert any("UTF-8" in text for text in tree_issues(service(), files))


def test_a_starter_holds_no_env_file():
    issues = tree_issues(service(), starter(__env="PORT=8000\n"))

    assert any(".env" in text and "project.env" in text for text in issues)


def test_the_env_file_keeps_the_manifests_order():
    assert env_file_text({"Z": "1", "A": "2"}) == "Z=1\nA=2\n"


def test_a_starter_without_an_env_file_is_complete():
    assert tree_issues(service(), starter()) == []


def test_there_is_no_env_local():
    assert any(
        ".env.local" in text for text in tree_issues(service(), starter(__env__local="X=1\n"))
    )


def test_a_node_project_pins_its_package_manager():
    files = starter(package__json='{"type": "module"}')

    assert any("packageManager" in text for text in tree_issues(service(), files))


def test_a_node_project_is_an_es_module_package():
    package = '{"packageManager": "pnpm@10.0.0"}'

    assert any(
        '"type": "module"' in text
        for text in tree_issues(service(), starter(package__json=package))
    )


def test_typescript_stays_below_7_in_a_starter():
    package = PACKAGE.replace("^6.0.0", "7.0.2")

    assert any(
        "typescript" in text for text in tree_issues(service(), starter(package__json=package))
    )


PYTHON_REQUIRES = ServiceRequires(lock="uv.lock", sizes=SIZES)
PYTHON_INSTALL = ("uv", "sync", "--frozen", "--no-build")
PYPROJECT = '[project]\nname = "x"\nversion = "0"\nrequires-python = ">=3.13"\n'


def python_service() -> ServiceProject:
    return service(
        commands=ServiceCommands(run=("r",), test=("t",), install=PYTHON_INSTALL),
        requires=PYTHON_REQUIRES,
    )


def python_starter(**changes: str) -> ProjectTree:
    files = {
        "README__md": "x",
        "pyproject__toml": PYPROJECT,
        "uv__lock": "version = 1\n",
        "__gitignore": ".venv/\n!uv.lock\n",
        **changes,
    }
    return tree(**files)


def test_a_python_starter_is_fine_with_a_project_table():
    assert tree_issues(python_service(), python_starter()) == []


def test_a_python_starter_declares_its_project_and_python():
    files = python_starter(pyproject__toml="[tool.ruff]\n")

    found = tree_issues(python_service(), files)
    assert any("[project]" in text for text in found)


def test_a_python_starter_keeps_its_lock_past_the_workspaces_gitignore():
    files = python_starter(__gitignore=".venv/\n")

    assert any("!uv.lock" in text for text in tree_issues(python_service(), files))


def test_a_python_module_may_not_hide_the_standard_library():
    files = python_starter(random__py="x = 1\n")
    meta = meta_of(python_service(), languages=(Language.PYTHON,))

    assert any("random" in message for _, message in service_issues(meta, python_service(), files))
