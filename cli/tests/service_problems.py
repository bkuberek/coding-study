"""A small service project problem on disk, for tests that go through the real loader."""

import json
from pathlib import Path
from typing import cast

import yaml

from tests.fakes import repository_root
from tests.helpers import FIXTURE_PROBLEMS

SLUG = "rooms-typescript"
IMAGE = "node:24-slim@sha256:01d566e8d94d8c619591d78652babfccd3c6992a3dffa9ed5ab39e11cf6c70e9"
LOCK = "pnpm-lock.yaml"
FOLDER = f"projects/{SLUG}"
INSTALL = ["corepack", "pnpm", "install", "--frozen-lockfile", "--ignore-scripts"]
CONFIG = "mocks/room-vendor.yaml"
VENDOR_CONFIG: dict[str, object] = {
    "routes": [
        {
            "id": "rooms",
            "method": "GET",
            "path": "/rooms",
            "response": {"status": 200, "body": {"rooms": []}},
        }
    ],
    "scenarios": {
        "outage": {"visible": True, "status": 503},
        "rate_limited": {"status": 429, "headers": {"Retry-After": "1"}},
    },
}


def make_content(tmp_path: Path) -> Path:
    return repository_root(tmp_path, FIXTURE_PROBLEMS)


def meta_document(**project: object) -> dict[str, object]:
    return {
        "id": "0901",
        "slug": SLUG,
        "title": "Rooms",
        "status": "draft",
        "difficulty": "medium",
        "track": "practical",
        "kind": "project",
        "languages": ["typescript"],
        "levels": [{"level": 1, "title": "One"}],
        "comparator": {"type": "exact"},
        "approaches": [
            {"id": "reference", "name": "R", "role": "optimal", "time": "t", "space": "s"}
        ],
        "project": {
            "grading": "http",
            "image": IMAGE,
            "commands": {
                "install": INSTALL,
                "bootstrap": ["node", "scripts/migrate.ts"],
                "run": ["node", "src/server.ts"],
                "test": ["node", "--test"],
                "reset": ["node", "scripts/reset.ts"],
            },
            "app": {"port_env": "PORT", "port": 8000, "health": "/health", "ready_timeout_s": 45},
            "env": {"PORT": "8000"},
            "install_env": {"COREPACK_HOME": "/cache/corepack"},
            "requires": {
                "lock": LOCK,
                "sizes": {"install_mb": 40, "images_mb": {"app": 77}, "memory_mb": 300},
            },
            **project,
        },
    }


GRADLE_IMAGE = (
    "gradle:9.8.2-jdk25-alpine"
    "@sha256:20d4d9547874206648a7a72991bf3af6d8bc1c8bffc7f32051f682b21f86d027"
)


def java_meta_document() -> dict[str, object]:
    """A Java service project as P12's template writes one: Gradle in the image, its user home in
    the install cache."""
    return {
        **meta_document(
            image=GRADLE_IMAGE,
            app={
                "port_env": "PORT",
                "port": 8000,
                "health": "/health",
                "ready_timeout_s": 120,
                "install_cache": True,
            },
            env={"PORT": "8000", "GRADLE_USER_HOME": "/cache/gradle"},
            install_env={"GRADLE_USER_HOME": "/cache/gradle"},
        ),
        "languages": ["java"],
    }


GO_IMAGE = "golang:1.27.3@sha256:e519d3b0a5b285e5aa53ab9eef02bc6bbb9cb04608389b743a136a9ce75f0d1e"
GO_ENV = {
    "PORT": "8000",
    "GOPROXY": "off",
    "GOFLAGS": "-mod=readonly",
    "GOMODCACHE": "/cache/go/mod",
    "GOCACHE": "/cache/go/build",
    "GOTMPDIR": "/cache",
    "GOWORK": "off",
    "CGO_ENABLED": "0",
}
GO_INSTALL_ENV = {
    "GOMODCACHE": "/cache/go/mod",
    "GOCACHE": "/cache/go/build",
    "GOFLAGS": "-mod=readonly",
    "GOWORK": "off",
}


def go_meta_document() -> dict[str, object]:
    """A Go service project as P13's template writes one: its modules in the install cache."""
    return {
        **meta_document(
            image=GO_IMAGE,
            commands={
                "install": ["go", "mod", "download"],
                "run": ["sh", "scripts/run.sh"],
                "test": ["go", "test", "-count=1", "./..."],
            },
            app={
                "port_env": "PORT",
                "port": 8000,
                "health": "/health",
                "ready_timeout_s": 180,
                "install_cache": True,
            },
            env=GO_ENV,
            install_env=GO_INSTALL_ENV,
        ),
        "languages": ["go"],
    }


def write_go_problem(root: Path) -> None:
    """`go_meta_document`'s problem, whose starter holds its lock, `go.sum`."""
    document = go_meta_document()
    project = cast(dict[str, object], document["project"])
    project["requires"] = {
        "lock": "go.sum",
        "sizes": {"install_mb": 120, "images_mb": {"app": 316}, "memory_mb": 450},
    }
    write_problem(root, document)
    (root / "problems" / f"0901-{SLUG}" / "starter" / "go.sum").write_text("")


def write_mock(root: Path, config: dict[str, object] | None = None) -> None:
    """The mock server `meta_document(mocks=[{"name": "room-vendor", "config": CONFIG}])` names."""
    path = root / "problems" / f"0901-{SLUG}" / CONFIG
    path.parent.mkdir()
    path.write_text(yaml.safe_dump(config or VENDOR_CONFIG))


def write_cases(root: Path, cases: list[dict[str, object]]) -> None:
    (root / "problems" / f"0901-{SLUG}" / "tests.json").write_text(
        json.dumps({"version": 1, "cases": cases})
    )


def write_problem(root: Path, document: dict[str, object] | None = None) -> None:
    directory = root / "problems" / f"0901-{SLUG}"
    (directory / "starter" / "src").mkdir(parents=True)
    (directory / "solutions" / "reference" / "src").mkdir(parents=True)
    (directory / "meta.yaml").write_text(yaml.safe_dump(document or meta_document()))
    (directory / "tests.json").write_text('{"version": 1, "cases": []}')
    (directory / "problem.md").write_text(
        "# Rooms\n\n## Statement\n\nS\n\n## Input\n\nI\n\n## Output\n\nO\n\n## Project\n\nP\n\n"
        "## Level 1: One\n\nL\n\n## Level 2: Two\n\nL\n"
    )
    (directory / "solutions" / "explanation.md").write_text("# Rooms: Explanation\n")
    (directory / "solutions" / "reference" / "src" / "server.ts").write_text("// reference\n")
    starter = directory / "starter"
    (starter / "README.md").write_text("# Rooms\n")
    (starter / "package.json").write_text('{"type": "module", "packageManager": "pnpm@10.0.0"}\n')
    (starter / LOCK).write_text("lockfileVersion: '9.0'\n")
    (starter / "src" / "server.ts").write_text("// server\n")
