"""`cstudy verify --static` on a service project: S14, S15, S19 and S22
(docs/specs/service-projects.md#static).

The rules on `meta.yaml` come back as a location and a message, and those on the starter as a path
and a message. S20, the mock configs, is P5's; S21, the compose file, is P10's; S23, the HTTP cases,
is P6's: nothing here reads those files.
"""

import json
import posixpath
import re
import sys
import tomllib
from collections.abc import Iterator
from typing import cast

from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.project import PATH_SEPARATOR, ProjectFile, ProjectTree
from coding_study.domain.sandbox import CONTROL_PORT, MOCK_PORT, RESERVED_SERVICES
from coding_study.domain.service_project import (
    ENV_FILE,
    FROZEN_INSTALL_FLAGS,
    GRADLE_LOCK,
    PROBLEM_PLACEHOLDER,
    ServiceCommands,
    ServiceProject,
)
from coding_study.domain.starter_files import LOCK_FILES, cache_path

MAX_MOCK_SERVERS = 4
MAX_STARTER_FILES = 50
MAX_STARTER_KIB = 256
MAX_STARTER_BYTES = MAX_STARTER_KIB * 1024
README_FILE = "README.md"
ENV_LOCAL_FILE = ".env.local"
PACKAGE_FILE = "package.json"
PNPM_LOCK = "pnpm-lock.yaml"
UV_LOCK = "uv.lock"
PYPROJECT_FILE = "pyproject.toml"
GITIGNORE_FILE = ".gitignore"
APP_IMAGE_ROW = "app"
MOCK_IMAGE_ROW = "mocks"
TYPESCRIPT_BELOW = 7
"""The broker needs `tsserver.js`, which a 7 may lack: unchecked, so held back."""
_DIGEST = re.compile(r"[^@\s]+@sha256:[0-9a-f]+")
_URL = re.compile(r"^[a-z][a-z0-9+.-]*://(?:[^@/]*@)?(?P<host>[^:/]+)(?::(?P<port>\d+))?")
THIS_MACHINE = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal"})
"""Hosts that name your machine, which the sandbox cannot reach."""
_VERSION_NUMBER = re.compile(r"\d+")
_PYTHON_SUFFIX = ".py"
INSTALL_COMMAND = "install"
GRADLE = "gradle"
GRADLE_OFFLINE = "--offline"
GRADLE_LOCK_OVERRIDES = frozenset(
    {
        *("--write-verification-metadata", "-M", "--dependency-verification", "-F"),
        *("--write-locks", "--update-locks"),
    }
)
"""What would make an install write its lock, or check less than it says."""
GRADLE_SETTINGS_FILES = ("settings.gradle.kts", "settings.gradle")
GRADLE_WRAPPER_SCRIPT = "gradlew"
GRADLE_WRAPPER_DIRECTORY = "gradle/wrapper/"
GRADLE_PROPERTIES_FILE = "gradle.properties"
GRADLE_DAEMON = "org.gradle.daemon"
_PROPERTY = re.compile(r"(?P<name>[^=:\s]+)\s*[=:\s]\s*(?P<value>.*)")
_PROPERTY_COMMENTS = ("#", "!")

type _Found = Iterator[tuple[str, str]]


def service_settings_issues(
    meta: ProblemMeta, service: ServiceProject
) -> tuple[tuple[str, str], ...]:
    """S14 and S19 on `meta.yaml`, then S22: each as the field and what is wrong with it."""
    return (
        *_settings(meta),
        *_image(service),
        *_commands(service),
        *_environment(service),
        *_mocks(service),
        *_requires(service),
    )


def service_issues(
    meta: ProblemMeta, service: ServiceProject, starter: ProjectTree | None
) -> tuple[tuple[str, str], ...]:
    """S15 and S19 on the starter: each as the path and what is wrong with it."""
    if starter is None:
        return (("", "missing (kind: project)"),)
    return tuple(_starter(meta, service, starter))


def _settings(meta: ProblemMeta) -> _Found:
    if len(meta.languages) != 1:
        yield "languages", "a project problem lists exactly one language"
    if len(meta.approaches) != 1:
        yield (
            "approaches",
            f"a project problem has exactly one approach (has {len(meta.approaches)})",
        )
    for index, approach in enumerate(meta.approaches):
        if approach.oracle:
            yield f"approaches[{index}]", "a project problem has no oracle"


def _image(service: ServiceProject) -> _Found:
    if not _DIGEST.fullmatch(service.image):
        yield "project.image", f'"{service.image}" is not pinned by digest'


def _commands(service: ServiceProject) -> _Found:
    commands, requires = service.commands, service.requires
    if requires.lock is not None and commands.install is None:
        yield "project.commands.install", "required: requires.lock names a lock file to install"
    if commands.install is not None:
        if requires.lock is None:
            yield "project.requires.lock", "an install needs requires.lock: a frozen lock file"
        yield from _frozen(commands.install)
    if service.services is not None and commands.bootstrap is None:
        yield "project.commands.bootstrap", "required: project.services needs its data brought up"
    if service.app.install_cache and commands.install is None:
        yield "project.app.install_cache", "needs commands.install, which fills the cache"
    yield from _placeholders(commands)
    yield from _gradle_commands(commands)


def _frozen(install: tuple[str, ...]) -> _Found:
    for manager, flags in FROZEN_INSTALL_FLAGS.items():
        if manager in install:
            for flag in flags:
                if flag not in install:
                    yield "project.commands.install", f"{manager} needs {flag}"


def _gradle_commands(commands: ServiceCommands) -> _Found:
    """Gradle reaches the network in `install` alone, and there it downloads what the lock lists
    and nothing else; every other command runs it offline, from the install cache."""
    for name, command in commands.declared().items():
        if posixpath.basename(command[0]) != GRADLE:
            continue
        where = f"project.commands.{name}"
        if name != INSTALL_COMMAND:
            if GRADLE_OFFLINE not in command:
                yield where, f"gradle needs {GRADLE_OFFLINE}: only install has the network"
            continue
        if GRADLE_OFFLINE in command:
            yield where, f"gradle downloads at install: no {GRADLE_OFFLINE}"
        for word in command:
            if word.partition("=")[0] in GRADLE_LOCK_OVERRIDES:
                yield where, f"gradle installs from the lock exactly: no {word}"


def _placeholders(commands: ServiceCommands) -> _Found:
    for name, command in commands.declared().items():
        if name != "grade_setup" and any(PROBLEM_PLACEHOLDER in word for word in command):
            yield f"project.commands.{name}", f"{PROBLEM_PLACEHOLDER} belongs in grade_setup only"
    setup = commands.grade_setup
    if setup is not None and not any(PROBLEM_PLACEHOLDER in word for word in setup):
        yield (
            "project.commands.grade_setup",
            f"must point into the problem's own files, through {PROBLEM_PLACEHOLDER}: "
            "you can edit a script in the starter",
        )


def _environment(service: ServiceProject) -> _Found:
    app = service.app
    if service.env.get(app.port_env) != str(app.port):
        yield "project.env", f"needs {app.port_env}={app.port}, the app's port"
    mocks = {mock.name for mock in service.mocks}
    for name, value in service.env.items():
        yield from _url(name, value, mocks, service.services is not None)


def url_host(value: str) -> str | None:
    """The host a URL in `project.env` names; None for a value that is no URL."""
    found = _URL.match(value)
    return found["host"] if found is not None else None


def _url(name: str, value: str, mocks: set[str], has_services: bool) -> _Found:
    found = _URL.match(value)
    if found is None:
        return
    host, port = found["host"], found["port"]
    where = f"project.env.{name}"
    if host in THIS_MACHINE:
        yield where, f"{host} is not reachable from the sandbox, which has no way out"
    elif host in mocks:
        if port != str(MOCK_PORT):
            yield where, f"the mock server {host} answers on port {MOCK_PORT}"
    elif not has_services:
        yield where, f"{host} is neither a declared mock server nor a declared service"


def _mocks(service: ServiceProject) -> _Found:
    names = [mock.name for mock in service.mocks]
    if len(names) > MAX_MOCK_SERVERS:
        yield "project.mocks", f"at most {MAX_MOCK_SERVERS} mock servers"
    if len(set(names)) != len(names):
        yield "project.mocks", "each mock server has a unique name"
    for name in names:
        if name in RESERVED_SERVICES:
            yield "project.mocks", f'"{name}" is a reserved name'
    if names and service.app.port == CONTROL_PORT:
        yield "project.app.port", f"{CONTROL_PORT} is the mock control port in this stack"


def _requires(service: ServiceProject) -> _Found:
    requires = service.requires
    sizes = requires.sizes
    if bool(requires.services) != (service.services is not None):
        yield "project.requires.services", "names the services of project.services, and only then"
    rows = [APP_IMAGE_ROW, *([MOCK_IMAGE_ROW] if service.mocks else []), *requires.services]
    for row in rows:
        if row not in sizes.images_mb:
            yield "project.requires.sizes.images_mb", f"needs a row for {row}"
    if sizes.memory_mb is None:
        yield "project.requires.sizes.memory_mb", "required: it is shown before any download"
    if requires.lock is not None and sizes.install_mb is None:
        yield (
            "project.requires.sizes.install_mb",
            "required with a lock: it is shown before install",
        )


def _starter(meta: ProblemMeta, service: ServiceProject, starter: ProjectTree) -> _Found:
    lock = service.requires.lock
    if README_FILE not in starter.paths:
        yield README_FILE, "missing"
    if lock is not None and lock not in starter.paths:
        yield lock, "missing: requires.lock names it"
    if lock is not None and PATH_SEPARATOR in lock and lock != GRADLE_LOCK:
        yield lock, f"a lock file lies at the starter's root, or is Gradle's {GRADLE_LOCK}"
    yield from _limits(starter, lock)
    yield from _contents(starter, lock)
    yield from _env_files(starter)
    if lock == PNPM_LOCK:
        yield from _node_package(starter)
    if lock == UV_LOCK:
        yield from _python_project(starter)
    if lock == GRADLE_LOCK:
        yield from _gradle_project(starter)
    if Language.PYTHON in meta.languages:
        yield from _shadowed_modules(starter)


def _limits(starter: ProjectTree, lock: str | None) -> _Found:
    """A lock file may not fit the limits of a starter, so it stands outside them."""
    counted = [file for file in starter.files if file.path != lock]
    if len(counted) > MAX_STARTER_FILES:
        yield "", f"holds {len(counted)} files; at most {MAX_STARTER_FILES} are allowed"
    size = sum(file.size for file in counted)
    if size > MAX_STARTER_BYTES:
        yield "", f"holds {size} bytes; at most {MAX_STARTER_KIB} KiB are allowed"


def _contents(starter: ProjectTree, lock: str | None) -> _Found:
    caches = dict.fromkeys(cache_path(file.path) for file in starter.files)
    for cache in caches:
        if cache is not None:
            yield cache, "is build output or a cache"
    for file in starter.files:
        if cache_path(file.path) is not None:
            continue
        name = file.path.rpartition(PATH_SEPARATOR)[2]
        if name in LOCK_FILES and file.path != lock:
            yield file.path, "is a lock file that requires.lock does not name"
        if file.text is None:
            yield file.path, "is not UTF-8 text"


def _env_files(starter: ProjectTree) -> _Found:
    if ENV_FILE in starter.paths:
        yield ENV_FILE, "a starter holds no .env: cstudy writes it from project.env"
    if ENV_LOCAL_FILE in starter.paths:
        yield ENV_LOCAL_FILE, "there is no .env.local: with fixed values, you edit .env itself"


def _node_package(starter: ProjectTree) -> _Found:
    file = starter.file(PACKAGE_FILE)
    if file is None:
        yield PACKAGE_FILE, "missing"
        return
    package = _json_object(file)
    if package is None:
        yield PACKAGE_FILE, "is not a JSON object"
        return
    if package.get("type") != "module":
        yield PACKAGE_FILE, 'needs "type": "module"'
    manager = package.get("packageManager")
    if not isinstance(manager, str) or not manager.startswith("pnpm@"):
        yield PACKAGE_FILE, 'needs "packageManager": "pnpm@<version>", which corepack holds to'
    yield from _typescript_version(package)


def _json_object(file: ProjectFile) -> dict[str, object] | None:
    try:
        document: object = json.loads(file.text or "")
    except json.JSONDecodeError:
        return None
    return cast(dict[str, object], document) if isinstance(document, dict) else None


def _typescript_version(package: dict[str, object]) -> _Found:
    for field in ("dependencies", "devDependencies"):
        declared = package.get(field)
        version = (
            cast(dict[str, object], declared).get("typescript")
            if isinstance(declared, dict)
            else None
        )
        if isinstance(version, str):
            major = _VERSION_NUMBER.search(version)
            if major is not None and int(major[0]) >= TYPESCRIPT_BELOW:
                yield PACKAGE_FILE, f"typescript stays below {TYPESCRIPT_BELOW} until it is checked"


def _python_project(starter: ProjectTree) -> _Found:
    file = starter.file(PYPROJECT_FILE)
    if file is None:
        yield PYPROJECT_FILE, "missing"
        return
    try:
        document = tomllib.loads(file.text or "")
    except tomllib.TOMLDecodeError as error:
        yield PYPROJECT_FILE, f"is not valid TOML: {error}"
        return
    table = document.get("project")
    if not isinstance(table, dict) or "requires-python" not in table:
        yield PYPROJECT_FILE, "needs a [project] table with requires-python"
    ignore = starter.file(GITIGNORE_FILE)
    if ignore is None or f"!{UV_LOCK}" not in (ignore.text or "").splitlines():
        yield GITIGNORE_FILE, f"needs !{UV_LOCK}, which the workspace's .gitignore ignores"


def _gradle_project(starter: ProjectTree) -> _Found:
    """The image's Gradle builds the folder, offline, and leaves no daemon behind in the app's
    container: each command is a container of its own, and the app runs once the build ends."""
    if not any(name in starter.paths for name in GRADLE_SETTINGS_FILES):
        yield GRADLE_SETTINGS_FILES[0], "missing: without it Gradle looks for one above this folder"
    for path in sorted(starter.paths):
        if path == GRADLE_WRAPPER_SCRIPT or path.startswith(GRADLE_WRAPPER_DIRECTORY):
            yield path, "the image holds Gradle, and a wrapper would download another"
    properties = starter.file(GRADLE_PROPERTIES_FILE)
    if properties is None or _property(properties, GRADLE_DAEMON) != "false":
        yield (
            GRADLE_PROPERTIES_FILE,
            f"needs {GRADLE_DAEMON}=false: a daemon would outlive the build in the app's container",
        )


def _property(file: ProjectFile, name: str) -> str | None:
    """`name`'s value in a `.properties` file, in the forms Gradle reads: `name=value`,
    `name: value` or `name value`."""
    for line in (file.text or "").splitlines():
        entry = line.strip()
        if not entry or entry.startswith(_PROPERTY_COMMENTS):
            continue
        found = _PROPERTY.fullmatch(entry)
        if found is not None and found["name"] == name:
            return found["value"].strip()
    return None


def _shadowed_modules(starter: ProjectTree) -> _Found:
    for path in sorted(starter.paths):
        if path.endswith(_PYTHON_SUFFIX):
            top = path.partition(PATH_SEPARATOR)[0].removesuffix(_PYTHON_SUFFIX)
            if top in sys.stdlib_module_names:
                yield path, f'is named after the standard-library module "{top}"'
