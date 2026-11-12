GROUP_GAP_MS = 1000
ROOT = 0


class Step:
    """One recorded edit, kept as a command that can be applied and reverted: at `position`,
    `removed` was replaced by `inserted`. The step is also the history state it leads to."""

    def __init__(self, number: int, parent: "Step | None", position: int) -> None:
        self.number = number
        self.parent = parent
        self.position = position
        self.removed = ""
        self.inserted = ""
        self.children: list[Step] = []
        self.current_child: Step | None = None

    def apply(self, text: str) -> str:
        return text[: self.position] + self.inserted + text[self.position + len(self.removed) :]

    def revert(self, text: str) -> str:
        return text[: self.position] + self.removed + text[self.position + len(self.inserted) :]

    def ancestors(self) -> list["Step"]:
        """This step and every step above it, up to the root."""
        chain = []
        step: Step | None = self
        while step is not None:
            chain.append(step)
            step = step.parent
        return chain


class Editor:
    def __init__(self, initial: str) -> None:
        self._text = initial
        self._root = Step(ROOT, None, 0)
        self._steps = [self._root]
        self._current = self._root
        self._checkpoints: dict[str, str] = {}
        self._group_open = False
        self._last_typed_at = 0

    # Level 1
    def insert(self, position: int, text: str) -> None:
        self._group_open = False
        self._record(min(position, len(self._text)), "", text)

    def erase(self, position: int, count: int) -> None:
        self._group_open = False
        start = min(position, len(self._text))
        end = min(len(self._text), start + count)
        self._record(start, self._text[start:end], "")

    def undo(self) -> bool:
        self._group_open = False
        if self._current.parent is None:
            return False
        self._text = self._current.revert(self._text)
        self._current = self._current.parent
        return True

    def redo(self) -> bool:
        self._group_open = False
        child = self._current.current_child
        if child is None:
            return False
        self._text = child.apply(self._text)
        self._current = child
        return True

    def text(self) -> str:
        return self._text

    # Level 2
    def type_text(self, timestamp: int, position: int, text: str) -> None:
        position = min(position, len(self._text))
        if self._joins_group(timestamp, position):
            group = self._current
            self._text = self._text[:position] + text + self._text[position:]
            group.inserted += text
        else:
            self._record(position, "", text)
        self._group_open = True
        self._last_typed_at = timestamp

    def _joins_group(self, timestamp: int, position: int) -> bool:
        group = self._current
        return (
            self._group_open
            and position == group.position + len(group.inserted)
            and timestamp - self._last_typed_at <= GROUP_GAP_MS
            and not group.inserted.endswith(" ")
        )

    # Level 3
    def checkpoint(self, name: str) -> None:
        self._group_open = False
        self._checkpoints[name] = self._text

    def restore(self, name: str) -> bool:
        self._group_open = False
        if name not in self._checkpoints:
            return False
        self._record(0, self._text, self._checkpoints[name])
        return True

    # Level 4
    def state(self) -> int:
        return self._current.number

    def branches(self) -> list[int]:
        return [child.number for child in self._current.children]

    def jump(self, state: int) -> bool:
        self._group_open = False
        if not 0 <= state < len(self._steps):
            return False
        target = self._steps[state]
        path_down = target.ancestors()
        on_target_path = set(path_down)
        while self._current not in on_target_path:
            self._text = self._current.revert(self._text)
            self._current = self._current.parent  # type: ignore[assignment]
        common = self._current
        for step in reversed(path_down[: path_down.index(common)]):
            self._text = step.apply(self._text)
        for child, parent in zip(path_down, path_down[1:]):
            parent.current_child = child
        self._current = target
        return True

    def _record(self, position: int, removed: str, inserted: str) -> None:
        """Records one step, unless it would leave the text as it is."""
        if removed == inserted:
            return
        step = Step(len(self._steps), self._current, position)
        step.removed = removed
        step.inserted = inserted
        self._steps.append(step)
        self._current.children.append(step)
        self._current.current_child = step
        self._text = step.apply(self._text)
        self._current = step
