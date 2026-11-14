TOKEN_CHARS = frozenset("!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
DECIMAL_DIGITS = frozenset("0123456789")
CRLF = "\r\n"
END_OF_HEAD = "\r\n\r\n"


class Failure(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class NeedMore(Exception):
    pass


def is_token(text: str) -> bool:
    return text != "" and all(char in TOKEN_CHARS for char in text)


def is_field_value(text: str) -> bool:
    return all(char == "\t" or " " <= char <= "~" for char in text)


def skip_empty_lines(data: str, pos: int) -> int:
    while data.startswith(CRLF, pos):
        pos += 2
    return pos


def check_line_endings(text: str) -> None:
    rest = text.replace(CRLF, "")
    if "\r" in rest or "\n" in rest:
        raise Failure("bad-line-ending")


def parse_request_line(line: str) -> list[str]:
    parts = line.split(" ")
    if len(parts) != 3:
        raise Failure("bad-request-line")
    method, target, version = parts
    valid_target = target != "" and all("!" <= char <= "~" for char in target)
    valid_version = (
        len(version) == 8
        and version.startswith("HTTP/")
        and version[5].isdigit()
        and version[6] == "."
        and version[7].isdigit()
    )
    if not (is_token(method) and valid_target and valid_version):
        raise Failure("bad-request-line")
    return ["request", method, target, version]


def parse_field_line(line: str) -> tuple[str, str]:
    if line[:1] in (" ", "\t"):
        raise Failure("obs-fold")
    colon = line.find(":")
    if colon == -1 or not is_token(line[:colon]):
        raise Failure("bad-field")
    value = line[colon + 1 :].strip(" \t")
    if not is_field_value(value):
        raise Failure("bad-field")
    return line[:colon].lower(), value


def list_elements(values: list[str]) -> list[str]:
    """A comma-separated list over every field line, with empty elements dropped."""
    elements = (element.strip(" \t") for element in ",".join(values).split(","))
    return [element for element in elements if element != ""]


class HttpParser:
    """A request is read in three stages: skip empty lines, find the end of the head
    (the first CRLF CRLF), then read the body that the framing fields announce. Each stage
    either finishes, needs more bytes, or fails, and the same code serves the one-shot
    methods and the connection: `feed` keeps the unread bytes and runs the stages again
    each time more arrive, so a message is reported by the call that completes it.
    """

    def __init__(self) -> None:
        self._head_limit: int | None = None
        self._body_limit: int | None = None
        self._buffer = ""
        self._closed = False

    # Level 1
    def parse_head(self, data: str) -> list[list[str]]:
        try:
            start = skip_empty_lines(data, 0)
            end = self._end_of_head(data, start)
            return self._head_rows(data[start : end - 4])
        except NeedMore:
            return [["error", "incomplete"]]
        except Failure as failure:
            return [["error", failure.code]]

    # Level 2
    def parse_message(self, data: str) -> list[list[str]]:
        try:
            rows, _ = self._message(data, skip_empty_lines(data, 0))
            return rows
        except NeedMore:
            return [["error", "incomplete"]]
        except Failure as failure:
            return [["error", failure.code]]

    # Level 3
    def feed(self, data: str) -> list[list[str]]:
        if self._closed:
            return []
        self._buffer += data
        rows: list[list[str]] = []
        while True:
            start = skip_empty_lines(self._buffer, 0)
            self._buffer = self._buffer[start:]
            try:
                message, end = self._message(self._buffer, 0)
            except NeedMore:
                return rows
            except Failure as failure:
                self._closed = True
                self._buffer = ""
                return [*rows, ["error", failure.code]]
            rows.extend(message)
            self._buffer = self._buffer[end:]

    def close(self) -> list[list[str]]:
        if self._closed:
            return []
        self._closed = True
        return [["error", "incomplete"]] if self._buffer else []

    # Level 4
    def set_limits(self, max_head_bytes: int, max_body_bytes: int) -> None:
        self._head_limit = max_head_bytes
        self._body_limit = max_body_bytes

    # The stages
    def _end_of_head(self, data: str, start: int) -> int:
        """The index just after the head's empty line. With a limit, only the first
        `limit` bytes are searched, so a head that cannot fit fails without waiting."""
        if self._head_limit is None:
            found = data.find(END_OF_HEAD, start)
        else:
            found = data.find(END_OF_HEAD, start, start + self._head_limit)
            if found == -1 and len(data) - start >= self._head_limit:
                raise Failure("head-too-large")
        if found == -1:
            raise NeedMore
        return found + 4

    def _head_rows(self, text: str) -> list[list[str]]:
        check_line_endings(text)
        lines = text.split(CRLF)
        rows = [parse_request_line(lines[0])]
        rows.extend(["field", *parse_field_line(line)] for line in lines[1:])
        hosts = sum(1 for row in rows[1:] if row[1] == "host")
        if hosts > 1 or (hosts == 0 and rows[0][3] == "HTTP/1.1"):
            raise Failure("bad-host")
        return rows

    def _message(self, data: str, start: int) -> tuple[list[list[str]], int]:
        head_end = self._end_of_head(data, start)
        rows = self._head_rows(data[start : head_end - 4])
        fields = rows[1:]
        codings = [row[2] for row in fields if row[1] == "transfer-encoding"]
        lengths = [row[2] for row in fields if row[1] == "content-length"]
        if codings and lengths:
            raise Failure("ambiguous-length")
        if codings:
            if [coding.lower() for coding in list_elements(codings)] != ["chunked"]:
                raise Failure("unsupported-transfer-coding")
            return self._chunked(data, head_end, rows)
        length = self._content_length(lengths) if lengths else 0
        if len(data) - head_end < length:
            raise NeedMore
        rows.append(["body", data[head_end : head_end + length]])
        return rows, head_end + length

    def _content_length(self, lines: list[str]) -> int:
        elements = list_elements(lines)
        if not elements or not all(set(element) <= DECIMAL_DIGITS for element in elements):
            raise Failure("bad-content-length")
        if len({int(element) for element in elements}) > 1:
            raise Failure("conflicting-content-length")
        length = int(elements[0])
        if self._too_large(length, 0):
            raise Failure("body-too-large")
        return length

    def _too_large(self, size: int, used: int) -> bool:
        # Python integers never overflow; in a fixed-width language, compare the digits
        # before converting, or a size such as 10000000000000000 (hex) wraps to 0.
        return self._body_limit is not None and used + size > self._body_limit

    def _chunked(
        self, data: str, pos: int, rows: list[list[str]]
    ) -> tuple[list[list[str]], int]:
        content: list[str] = []
        total = 0
        while True:
            line_end = data.find(CRLF, pos)
            if line_end == -1:
                raise NeedMore
            size = self._chunk_size(data[pos:line_end])
            if self._too_large(size, total):
                raise Failure("body-too-large")
            pos = line_end + 2
            if size == 0:
                break
            if len(data) - pos < size + 2:
                raise NeedMore
            if data[pos + size : pos + size + 2] != CRLF:
                raise Failure("bad-chunk")
            content.append(data[pos : pos + size])
            total += size
            pos += size + 2
        rows.append(["body", "".join(content)])
        if data.startswith(CRLF, pos):
            return rows, pos + 2
        found = data.find(END_OF_HEAD, pos)
        if found == -1:
            raise NeedMore
        text = data[pos:found]
        check_line_endings(text)
        rows.extend(["trailer", *parse_field_line(line)] for line in text.split(CRLF))
        return rows, found + 4

    def _chunk_size(self, line: str) -> int:
        if "\r" in line or "\n" in line:
            raise Failure("bad-chunk-size")
        semicolon = line.find(";")
        digits = line if semicolon == -1 else line[:semicolon].rstrip(" \t")
        if digits == "" or not all(char in HEX_DIGITS for char in digits):
            raise Failure("bad-chunk-size")
        return int(digits, 16)
