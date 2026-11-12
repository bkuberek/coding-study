"""Undo and redo in a small text editor, with one stack of edits done and one of edits undone.

An edit is (position, removed, inserted): at `position`, the text `removed` becomes `inserted`.
Swapping `removed` and `inserted` gives the edit that takes it back, so undo applies the inverse.
"""

Edit = tuple[int, str, str]


def apply(text: str, edit: Edit) -> str:
    position, removed, inserted = edit
    assert text[position : position + len(removed)] == removed
    return text[:position] + inserted + text[position + len(removed) :]


def inverse(edit: Edit) -> Edit:
    position, removed, inserted = edit
    return position, inserted, removed


class Editor:
    def __init__(self) -> None:
        self.text = ""
        self.done: list[Edit] = []  # the most recent edit on top
        self.undone: list[Edit] = []  # the most recently undone edit on top

    def edit(self, position: int, removed: str, inserted: str) -> None:
        change = (position, removed, inserted)
        self.text = apply(self.text, change)
        self.done.append(change)
        self.undone.clear()  # a new edit starts a new future: what was undone cannot come back

    def undo(self) -> None:
        if self.done:
            change = self.done.pop()
            self.text = apply(self.text, inverse(change))
            self.undone.append(change)

    def redo(self) -> None:
        if self.undone:
            change = self.undone.pop()
            self.text = apply(self.text, change)
            self.done.append(change)


editor = Editor()
steps = [
    ("type 'hello'", lambda: editor.edit(0, "", "hello")),
    ("type ' world'", lambda: editor.edit(5, "", " world")),
    ("replace 'world' with 'there'", lambda: editor.edit(6, "world", "there")),
    ("undo", editor.undo),
    ("undo", editor.undo),
    ("redo", editor.redo),
    ("type '!'", lambda: editor.edit(11, "", "!")),
    ("redo", editor.redo),
]
for label, step in steps:
    step()
    print(f"{label:<29} {editor.text!r:<15} done {len(editor.done)}, undone {len(editor.undone)}")
