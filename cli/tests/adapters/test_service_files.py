"""A service project's mock configs and compose file, read with the problem through the real
loader."""

import pytest
import yaml

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.errors import ContentError
from tests.service_problems import (
    CONFIG,
    SLUG,
    VENDOR_CONFIG,
    make_content,
    meta_document,
    write_mock,
    write_problem,
)


@pytest.fixture
def root(tmp_path):
    found = make_content(tmp_path)
    write_problem(found, meta_document(mocks=[{"name": "room-vendor", "config": CONFIG}]))
    return found


def problem_directory(root):
    return root / "problems" / f"0901-{SLUG}"


def loaded(root):
    return FsProblemRepository(root).load(SLUG).project_files


def test_a_mock_config_comes_with_the_problem(root):
    write_mock(root)

    assert loaded(root).mocks["room-vendor"].document == VENDOR_CONFIG


def test_a_config_that_breaks_its_schema_is_a_content_error_naming_the_file(root):
    write_mock(root, {"routes": []})

    with pytest.raises(ContentError, match="room-vendor"):
        loaded(root)


def test_a_config_that_is_missing_is_a_content_error_naming_the_file(root):
    with pytest.raises(ContentError, match="room-vendor"):
        loaded(root)


def test_a_config_that_leaves_the_problem_is_a_content_error(tmp_path):
    root = make_content(tmp_path)
    document = meta_document(mocks=[{"name": "room-vendor", "config": "../elsewhere.yaml"}])
    write_problem(root, document)

    with pytest.raises(ContentError, match="leaves its folder"):
        FsProblemRepository(root).load(SLUG)


def with_body(root, body: bytes | None):
    config = {
        "routes": [
            {
                "id": "rooms",
                "method": "GET",
                "path": "/r",
                "response": {"status": 200, "body_file": "bodies/rooms.json"},
            }
        ]
    }
    write_mock(root, config)
    if body is not None:
        path = problem_directory(root) / "mocks" / "bodies" / "rooms.json"
        path.parent.mkdir()
        path.write_bytes(body)
    return loaded(root).mocks["room-vendor"]


def test_a_body_file_is_read_beside_its_config(root):
    assert with_body(root, b"[]\n").bodies == {"bodies/rooms.json": "[]\n"}


def test_a_body_that_is_not_text_is_held_as_none(root):
    assert with_body(root, b"\xff\xfe").bodies == {"bodies/rooms.json": None}


def test_a_body_that_is_not_there_is_not_held(root):
    assert with_body(root, None).bodies == {}


def test_a_body_behind_a_link_is_not_followed(root, tmp_path):
    write_mock(root, {"routes": VENDOR_CONFIG["routes"]})
    secret = tmp_path / "secret.json"
    secret.write_text("secret")
    (problem_directory(root) / "mocks" / "bodies").mkdir()
    (problem_directory(root) / "mocks" / "bodies" / "rooms.json").symlink_to(secret)
    config = yaml.safe_load((problem_directory(root) / CONFIG).read_text())
    config["routes"][0]["response"] = {"status": 200, "body_file": "bodies/rooms.json"}
    (problem_directory(root) / CONFIG).write_text(yaml.safe_dump(config))

    assert loaded(root).mocks["room-vendor"].bodies == {}


def test_the_vendor_documentation_is_read_next_to_the_config(root):
    write_mock(root)
    (problem_directory(root) / "mocks" / "room-vendor.API.md").write_text("# The vendor\n")

    assert loaded(root).mocks["room-vendor"].api == "# The vendor\n"


def test_no_vendor_documentation_is_none(root):
    write_mock(root)

    assert loaded(root).mocks["room-vendor"].api is None


def test_a_compose_file_comes_with_the_problem(tmp_path):
    root = make_content(tmp_path)
    write_problem(root, meta_document(services="services/compose.yaml"))
    compose = problem_directory(root) / "services" / "compose.yaml"
    compose.parent.mkdir()
    compose.write_text("services: {db: {image: postgres}}\n")

    assert loaded(root).backing_services == {"services": {"db": {"image": "postgres"}}}


def test_a_compose_file_that_is_missing_is_a_content_error(tmp_path):
    root = make_content(tmp_path)
    write_problem(root, meta_document(services="services/compose.yaml"))

    with pytest.raises(ContentError, match=r"compose\.yaml"):
        loaded(root)


def test_another_kind_of_project_reads_none_of_this(tmp_path):
    root = make_content(tmp_path)

    assert FsProblemRepository(root).load("two-sum").project_files is None
