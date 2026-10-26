"""When cstudy may rewrite a generated IDE file
(docs/specs/installation-and-workspaces.md#ide-files)."""

import pytest

from coding_study.domain.ide import (
    Change,
    GeneratedFile,
    Ide,
    Regeneration,
    content_digest,
    plan_regeneration,
)

TASKS = ".vscode/tasks.json"
MISC = ".idea/misc.xml"
NEW = GeneratedFile(TASKS, "new\n")
OLD_DIGEST = content_digest(b"old\n")
EDITED_DIGEST = content_digest(b"edited\n")
BOTH = (Ide.VSCODE, Ide.IDEA)


def plan(
    current: dict[str, str | None],
    recorded: dict[str, str] | None = None,
    generated: tuple[GeneratedFile, ...] = (NEW,),
    ides: tuple[Ide, ...] = BOTH,
    force: bool = False,
):
    regeneration = Regeneration(generated, recorded or {}, ides, force=force)
    return plan_regeneration(regeneration, current)


def change_of(result, path: str = TASKS) -> Change:
    return {step.path: step.change for step in result.steps}[path]


def test_a_missing_file_is_created():
    assert change_of(plan({TASKS: None})) is Change.CREATED


def test_a_missing_file_is_created_even_when_recorded():
    assert change_of(plan({TASKS: None}, {TASKS: OLD_DIGEST})) is Change.CREATED


def test_a_file_as_cstudy_wrote_it_is_updated():
    assert change_of(plan({TASKS: OLD_DIGEST}, {TASKS: OLD_DIGEST})) is Change.UPDATED


def test_a_file_already_equal_to_the_new_content_is_unchanged():
    assert change_of(plan({TASKS: NEW.digest}, {TASKS: NEW.digest})) is Change.UNCHANGED


def test_an_unrecorded_file_equal_to_the_new_content_is_unchanged():
    assert change_of(plan({TASKS: NEW.digest})) is Change.UNCHANGED


def test_an_edited_file_is_kept():
    assert change_of(plan({TASKS: EDITED_DIGEST}, {TASKS: OLD_DIGEST})) is Change.KEPT


def test_a_file_cstudy_never_wrote_is_kept():
    assert change_of(plan({TASKS: EDITED_DIGEST})) is Change.KEPT


@pytest.mark.parametrize("recorded", [{TASKS: OLD_DIGEST}, {}])
def test_force_overwrites_a_kept_file(recorded):
    assert change_of(plan({TASKS: EDITED_DIGEST}, recorded, force=True)) is Change.UPDATED


def test_written_content_is_the_new_content():
    step = plan({TASKS: None}).steps[0]
    assert step.content == NEW.content


def test_the_manifest_records_what_was_written():
    assert plan({TASKS: None}).manifest == {TASKS: NEW.digest}


def test_the_manifest_keeps_the_record_of_an_edited_file():
    result = plan({TASKS: EDITED_DIGEST}, {TASKS: OLD_DIGEST})
    assert result.manifest == {TASKS: OLD_DIGEST}


def test_the_manifest_never_records_a_file_cstudy_never_wrote():
    assert plan({TASKS: EDITED_DIGEST}).manifest == {}


def test_a_file_no_longer_generated_is_removed_when_unchanged():
    result = plan({TASKS: None, MISC: OLD_DIGEST}, {MISC: OLD_DIGEST})
    assert change_of(result, MISC) is Change.REMOVED


def test_a_removed_file_leaves_the_manifest():
    result = plan({TASKS: None, MISC: OLD_DIGEST}, {MISC: OLD_DIGEST})
    assert MISC not in result.manifest


def test_a_file_no_longer_generated_is_kept_when_edited():
    result = plan({TASKS: None, MISC: EDITED_DIGEST}, {MISC: OLD_DIGEST})
    assert change_of(result, MISC) is Change.KEPT


def test_a_kept_file_no_longer_generated_leaves_the_manifest():
    result = plan({TASKS: None, MISC: EDITED_DIGEST}, {MISC: OLD_DIGEST})
    assert MISC not in result.manifest


def test_a_deleted_file_no_longer_generated_leaves_the_manifest_silently():
    result = plan({TASKS: None, MISC: None}, {MISC: OLD_DIGEST})
    assert ([step.path for step in result.steps], MISC in result.manifest) == ([TASKS], False)


def test_files_of_an_ide_not_regenerated_are_left_alone():
    result = plan({TASKS: None, MISC: OLD_DIGEST}, {MISC: OLD_DIGEST}, ides=(Ide.VSCODE,))
    assert ([step.path for step in result.steps], result.manifest[MISC]) == ([TASKS], OLD_DIGEST)


def test_the_paths_to_inspect_are_the_generated_and_the_recorded_ones():
    regeneration = Regeneration((NEW,), {MISC: OLD_DIGEST, "elsewhere/x": OLD_DIGEST}, BOTH)
    assert regeneration.paths() == {TASKS, MISC}
