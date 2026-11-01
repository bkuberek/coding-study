"""A workspace where another program deletes a file while a change of it is under way: after the
change checked the file's content, before it moves or deletes the file."""

from coding_study.adapters.workspace_fs import WorkspaceFs


class OutsideDeletion(WorkspaceFs):
    """`WorkspaceFs`, but every `move_within` and `delete_within` finds its file deleted just
    before it acts, as when an editor or the terminal deletes it at that moment."""

    def move_within(self, folder: str, path: str, target: str) -> None:
        self.absolute(f"{folder}/{path}").unlink()
        super().move_within(folder, path, target)

    def delete_within(self, folder: str, path: str) -> None:
        self.absolute(f"{folder}/{path}").unlink()
        super().delete_within(folder, path)
