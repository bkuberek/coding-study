ARROW_DOWN = "ArrowDown"
ARROW_UP = "ArrowUp"
ENTER = "Enter"
NOTHING = -1


class SearchBox:
    """The list is empty exactly when nothing is highlighted: `_show` keeps the two in step."""

    def __init__(self, names: list[str]) -> None:
        self._names = names
        self._lowered_names = [name.lower() for name in names]
        self._shown: list[str] = []
        self._highlight = NOTHING
        self._text = ""
        self._requests_sent = 0
        self._awaited_request: int | None = None
        self._selected: list[str] = []

    # Level 1
    def keydown(self, timestamp: int, key: str) -> None:
        if key == ARROW_DOWN:
            self._move(1)
        elif key == ARROW_UP:
            self._move(-1)
        elif key == ENTER:
            self._select_highlighted()

    def keyup(self, timestamp: int, key: str) -> None:
        """Releasing a key changes nothing: every action happens when the key goes down."""

    def results_arrived(self, timestamp: int, items: list[str]) -> None:
        self._show(items)

    def results(self, timestamp: int) -> list[str]:
        return list(self._shown)

    def highlighted(self, timestamp: int) -> int:
        return self._highlight

    def highlighted_text(self, timestamp: int) -> str:
        return "" if self._highlight == NOTHING else self._shown[self._highlight]

    # Level 2
    def search(self, timestamp: int, query: str) -> None:
        needle = query.strip().lower()
        if not needle:
            self._show([])
            return
        matches = zip(self._names, self._lowered_names, strict=True)
        self._show([name for name, lowered in matches if needle in lowered])

    # Level 3
    def input_changed(self, timestamp: int, text: str) -> int:
        self._text = text
        if not text.strip():
            self._stop_awaiting()
            return NOTHING
        self._requests_sent += 1
        self._awaited_request = self._requests_sent
        return self._requests_sent

    def response_arrived(self, timestamp: int, request_id: int, items: list[str]) -> None:
        if request_id == self._awaited_request:
            self._show(items)

    def input_text(self, timestamp: int) -> str:
        return self._text

    # Level 4
    def selections(self, timestamp: int) -> list[str]:
        return list(self._selected)

    def _move(self, step: int) -> None:
        count = len(self._shown)
        if count:
            self._highlight = (self._highlight + step) % count

    def _select_highlighted(self) -> None:
        if self._highlight == NOTHING:
            return
        choice = self._shown[self._highlight]
        self._selected.append(choice)
        self._text = choice
        self._stop_awaiting()

    def _stop_awaiting(self) -> None:
        """The input changed without a request: no response sent so far may be shown, and the
        list closes."""
        self._awaited_request = None
        self._show([])

    def _show(self, items: list[str]) -> None:
        self._shown = list(items)
        self._highlight = 0 if items else NOTHING
