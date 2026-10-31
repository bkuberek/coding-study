"""`cstudy ide` and the IDE step of `cstudy init`
(docs/specs/installation-and-workspaces.md#ide-files)."""

from collections.abc import Mapping

from coding_study.application.ide_files import IdeRequest, generate_ide_files, link_rust_projects
from coding_study.domain.ide import (
    NO_PROJECT_FOLDERS,
    Change,
    GeneratedFile,
    Ide,
    IdeWorkspace,
    content_digest,
)

TASKS = ".vscode/tasks.json"
MISC = ".idea/misc.xml"


class FakeRenderer:
    def __init__(self, *files: GeneratedFile) -> None:
        self._files = files
        self.workspaces: list[IdeWorkspace] = []

    def files(self, workspace: IdeWorkspace = NO_PROJECT_FOLDERS) -> tuple[GeneratedFile, ...]:
        self.workspaces.append(workspace)
        return self._files


class InMemoryFiles:
    def __init__(self) -> None:
        self.contents: dict[str, str] = {}
        self.recorded: dict[str, str] = {}
        self.manifest_saves = 0

    def digest(self, path: str) -> str | None:
        content = self.contents.get(path)
        return None if content is None else content_digest(content.encode())

    def write(self, path: str, content: str) -> None:
        self.contents[path] = content

    def remove(self, path: str) -> None:
        del self.contents[path]

    def manifest(self) -> dict[str, str]:
        return dict(self.recorded)

    def save_manifest(self, manifest: Mapping[str, str]) -> None:
        self.recorded = dict(manifest)
        self.manifest_saves += 1

    def rust_projects(self) -> tuple[str, ...]:
        return ("projects/bank-project-rust/Cargo.toml",)


RENDERERS = {
    Ide.VSCODE: FakeRenderer(GeneratedFile(TASKS, "tasks\n")),
    Ide.IDEA: FakeRenderer(GeneratedFile(MISC, "misc\n")),
}
BOTH = IdeRequest((Ide.VSCODE, Ide.IDEA))


def changes(report) -> dict[str, Change]:
    return {step.path: step.change for step in report.steps}


def test_a_new_workspace_gets_every_file():
    store = InMemoryFiles()
    generate_ide_files(RENDERERS, store, BOTH)
    assert store.contents == {TASKS: "tasks\n", MISC: "misc\n"}


def test_the_written_files_are_recorded():
    store = InMemoryFiles()
    generate_ide_files(RENDERERS, store, BOTH)
    assert set(store.recorded) == {TASKS, MISC}


def test_only_the_requested_ide_is_generated():
    store = InMemoryFiles()
    generate_ide_files(RENDERERS, store, IdeRequest((Ide.VSCODE,)))
    assert set(store.contents) == {TASKS}


def test_a_second_run_changes_nothing():
    store = InMemoryFiles()
    generate_ide_files(RENDERERS, store, BOTH)
    report = generate_ide_files(RENDERERS, store, BOTH)
    assert (report.changed, store.manifest_saves) == (False, 1)


def test_an_edited_file_is_kept():
    store = InMemoryFiles()
    generate_ide_files(RENDERERS, store, BOTH)
    store.contents[TASKS] = "mine\n"
    report = generate_ide_files(RENDERERS, store, BOTH)
    assert (changes(report)[TASKS], store.contents[TASKS]) == (Change.KEPT, "mine\n")


def test_the_report_lists_the_kept_files():
    store = InMemoryFiles()
    generate_ide_files(RENDERERS, store, BOTH)
    store.contents[TASKS] = "mine\n"
    assert generate_ide_files(RENDERERS, store, BOTH).paths(Change.KEPT) == (TASKS,)


def test_force_overwrites_an_edited_file():
    store = InMemoryFiles()
    generate_ide_files(RENDERERS, store, BOTH)
    store.contents[TASKS] = "mine\n"
    generate_ide_files(RENDERERS, store, IdeRequest((Ide.VSCODE,), force=True))
    assert store.contents[TASKS] == "tasks\n"


def test_a_file_no_longer_generated_is_removed():
    store = InMemoryFiles()
    old = {Ide.VSCODE: FakeRenderer(GeneratedFile(".vscode/old.json", "{}\n"))}
    generate_ide_files(old, store, IdeRequest((Ide.VSCODE,)))
    generate_ide_files(RENDERERS, store, IdeRequest((Ide.VSCODE,)))
    assert set(store.contents) == {TASKS}


def test_a_file_of_another_name_in_the_directory_is_never_touched():
    store = InMemoryFiles()
    store.contents[".idea/runConfigurations/Mine.xml"] = "<mine />\n"
    generate_ide_files(RENDERERS, store, IdeRequest((Ide.IDEA,), force=True))
    assert store.contents[".idea/runConfigurations/Mine.xml"] == "<mine />\n"


def test_the_renderers_see_the_workspaces_rust_projects():
    renderer = FakeRenderer(GeneratedFile(TASKS, "tasks\n"))
    generate_ide_files({Ide.VSCODE: renderer}, InMemoryFiles(), IdeRequest((Ide.VSCODE,)))
    assert renderer.workspaces == [IdeWorkspace(("projects/bank-project-rust/Cargo.toml",))]


# cstudy start of a Rust project links its folder (docs/specs/cli.md#cstudy-start)

SETTINGS = ".vscode/settings.json"
UNLINKED = '{"rust-analyzer.linkedProjects": ["rust/Cargo.toml"]}\n'
LINKED = GeneratedFile(SETTINGS, '{"rust-analyzer.linkedProjects": ["...", "projects/..."]}\n')
RUST_START = {Ide.VSCODE: FakeRenderer(LINKED), Ide.IDEA: FakeRenderer(GeneratedFile(MISC, "x\n"))}


def written_by_cstudy(store: InMemoryFiles, path: str, content: str) -> None:
    store.contents[path] = content
    store.recorded[path] = content_digest(content.encode())


def test_a_rust_start_refreshes_the_vscode_settings_cstudy_wrote():
    store = InMemoryFiles()
    written_by_cstudy(store, SETTINGS, UNLINKED)
    link_rust_projects(RUST_START, store)
    assert store.contents[SETTINGS] == LINKED.content


def test_a_rust_start_refreshes_vscode_files_only():
    store = InMemoryFiles()
    written_by_cstudy(store, SETTINGS, UNLINKED)
    report = link_rust_projects(RUST_START, store)
    assert report is not None
    assert (report.ides, changes(report)) == ((Ide.VSCODE,), {SETTINGS: Change.UPDATED})


def test_a_rust_start_keeps_vscode_settings_you_edited():
    store = InMemoryFiles()
    written_by_cstudy(store, SETTINGS, UNLINKED)
    store.contents[SETTINGS] = '{"editor.fontSize": 14}\n'
    report = link_rust_projects(RUST_START, store)
    assert report is not None
    assert changes(report) == {SETTINGS: Change.KEPT}


def test_a_rust_start_writes_no_ide_file_where_cstudy_never_wrote_vscode_settings():
    store = InMemoryFiles()
    written_by_cstudy(store, MISC, "x\n")
    assert (link_rust_projects(RUST_START, store), set(store.contents)) == (None, {MISC})
