"""http-message-parser promises that its hidden cases catch the classic mistakes of reading
HTTP/1.1 requests: case and whitespace rules of fields, lenient request lines and line endings,
folded lines accepted, the Host rule, bodies framed the wrong way or not at all, chunk sizes read
as decimal or with their extensions, trailers merged into the header, connections that report
too few messages or keep going after an error, and the framing ambiguities and size limits that
request smuggling and memory exhaustion rely on. These tests replay every case against a model
of the parser written from the statement, which must give every expected output, and against
that model with one mistake planted at a time, which some hidden case must fail.

The model's connection is deliberately not a buffer: on every call it parses everything received
so far from the start and reports what has become complete since the last call, so it shares no
incremental bookkeeping with the reference solutions."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0356-http-message-parser"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

TOKEN = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")
TARGET = re.compile(r"[!-~]+")
VERSION = re.compile(r"HTTP/[0-9]\.[0-9]")
VALUE = re.compile(r"[\t -~]*")
DIGITS = re.compile(r"[0-9]+")
SIZE_LINE = re.compile(r"([0-9A-Fa-f]+)(?:[ \t]*;[^\r\n]*)?")
LIST_SEPARATOR = re.compile(r"[ \t]*,[ \t]*")
END = "\r\n\r\n"

Rows = list[list[str]]


class IncompleteError(Exception):
    pass


class BadRequestError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class Model:
    """The parser as the statement words it. Each mistake below overrides one method."""

    def __init__(self) -> None:
        self.max_head: int | None = None
        self.max_body: int | None = None
        self.stream = ""
        self.reported = 0
        self.closed = False

    # --- level 1
    def skip_blank(self, data: str, pos: int) -> int:
        while data[pos : pos + 2] == "\r\n":
            pos += 2
        return pos

    def head_end(self, data: str, pos: int) -> int:
        found = data.find(END, pos)
        if self.max_head is not None:
            if found != -1 and found + 4 - pos > self.max_head:
                raise BadRequestError("head-too-large")
            if found == -1 and len(data) - pos >= self.max_head:
                raise BadRequestError("head-too-large")
        if found == -1:
            raise IncompleteError
        return found + 4

    def check_endings(self, text: str) -> None:
        if re.search(r"\r(?!\n)|(?<!\r)\n", text):
            raise BadRequestError("bad-line-ending")

    def lines(self, text: str) -> list[str]:
        return text.split("\r\n")

    def request_parts(self, line: str) -> list[str]:
        return line.split(" ")

    def version_ok(self, version: str) -> bool:
        return VERSION.fullmatch(version) is not None

    def request(self, line: str) -> list[str]:
        parts = self.request_parts(line)
        if (
            len(parts) != 3
            or not TOKEN.fullmatch(parts[0])
            or not TARGET.fullmatch(parts[1])
            or not self.version_ok(parts[2])
        ):
            raise BadRequestError("bad-request-line")
        return ["request", *parts]

    def folded(self, line: str) -> bool:
        return line[:1] in (" ", "\t")

    def split_field(self, line: str) -> tuple[str, str]:
        name, colon, value = line.partition(":")
        if not colon or not TOKEN.fullmatch(name):
            raise BadRequestError("bad-field")
        return name, value

    def trim(self, value: str) -> str:
        return value.strip(" \t")

    def name_of(self, name: str) -> str:
        return name.lower()

    def field(self, line: str) -> tuple[str, str]:
        if self.folded(line):
            raise BadRequestError("obs-fold")
        name, raw = self.split_field(line)
        value = self.trim(raw)
        if not VALUE.fullmatch(value):
            raise BadRequestError("bad-field")
        return self.name_of(name), value

    def fields(self, lines: list[str]) -> list[tuple[str, str]]:
        return [self.field(line) for line in lines]

    def host_ok(self, version: str, hosts: int) -> bool:
        return hosts <= 1 and (hosts == 1 or version != "HTTP/1.1")

    def head_rows(self, text: str) -> Rows:
        self.check_endings(text)
        first, *rest = self.lines(text)
        rows = [self.request(first)] + [["field", n, v] for n, v in self.fields(rest)]
        if not self.host_ok(rows[0][3], sum(row[1] == "host" for row in rows[1:])):
            raise BadRequestError("bad-host")
        return rows

    def head(self, data: str, pos: int) -> tuple[Rows, int]:
        end = self.head_end(data, pos)
        return self.head_rows(data[pos : end - 4]), end

    def parse_head(self, data: str) -> Rows:
        try:
            return self.head(data, self.skip_blank(data, 0))[0]
        except IncompleteError:
            return [["error", "incomplete"]]
        except BadRequestError as bad:
            return [["error", bad.code]]

    # --- level 2 and 4: framing
    def elements(self, values: list[str]) -> list[str]:
        return [item for item in LIST_SEPARATOR.split(",".join(values)) if item]

    def codings_ok(self, codings: list[str]) -> bool:
        return [coding.lower() for coding in codings] == ["chunked"]

    def both_framings(self, rows: Rows) -> None:
        raise BadRequestError("ambiguous-length")

    def length(self, values: list[str]) -> int:
        items = self.elements(values)
        if not items or not all(DIGITS.fullmatch(item) for item in items):
            raise BadRequestError("bad-content-length")
        if len(set(map(int, items))) > 1:
            raise BadRequestError("conflicting-content-length")
        return self.number(items[0], 10)

    def number(self, digits: str, base: int) -> int:
        return int(digits, base)

    def over(self, size: int, used: int) -> bool:
        return self.max_body is not None and used + size > self.max_body

    def length_over(self, size: int) -> bool:
        return self.over(size, 0)

    def framing(self, rows: Rows) -> tuple[str, int]:
        codings = [row[2] for row in rows if row[:2] == ["field", "transfer-encoding"]]
        lengths = [row[2] for row in rows if row[:2] == ["field", "content-length"]]
        if codings and lengths:
            return self.resolve_both(rows, codings, lengths)
        if codings:
            if not self.codings_ok(self.elements(codings)):
                raise BadRequestError("unsupported-transfer-coding")
            return "chunked", 0
        if lengths:
            size = self.length(lengths)
            if self.length_over(size):
                raise BadRequestError("body-too-large")
            return "length", size
        return "length", 0

    def resolve_both(self, rows: Rows, codings: list[str], lengths: list[str]) -> tuple[str, int]:
        self.both_framings(rows)
        return "length", 0

    def size_of_line(self, line: str) -> int:
        match = SIZE_LINE.fullmatch(line)
        if not match:
            raise BadRequestError("bad-chunk-size")
        return self.number(match.group(1), 16)

    def chunk_end_ok(self, data: str, pos: int) -> bool:
        return data[pos : pos + 2] == "\r\n"

    def trailer_rows(self, text: str) -> Rows:
        self.check_endings(text)
        return [["trailer", n, v] for n, v in self.fields(self.lines(text))]

    def chunked(self, data: str, pos: int) -> tuple[str, Rows, int]:
        content, total = "", 0
        while True:
            line_end = data.find("\r\n", pos)
            if line_end == -1:
                raise IncompleteError
            size = self.size_of_line(data[pos:line_end])
            if self.over(size, total):
                raise BadRequestError("body-too-large")
            pos = line_end + 2
            if size == 0:
                break
            if len(data) < pos + size + 2:
                raise IncompleteError
            if not self.chunk_end_ok(data, pos + size):
                raise BadRequestError("bad-chunk")
            content += data[pos : pos + size]
            total += size
            pos += size + 2
        if data[pos : pos + 2] == "\r\n":
            return content, [], pos + 2
        found = data.find(END, pos)
        if found == -1:
            raise IncompleteError
        return content, self.trailer_rows(data[pos:found]), found + 4

    def message(self, data: str, pos: int) -> tuple[Rows, int]:
        rows, end = self.head(data, pos)
        kind, size = self.framing(rows)
        if kind == "chunked":
            content, trailers, end = self.chunked(data, end)
            return [*rows, ["body", content], *trailers], end
        if len(data) < end + size:
            raise IncompleteError
        return [*rows, ["body", data[end : end + size]]], end + size

    def parse_message(self, data: str) -> Rows:
        try:
            return self.message(data, self.skip_blank(data, 0))[0]
        except IncompleteError:
            return [["error", "incomplete"]]
        except BadRequestError as bad:
            return [["error", bad.code]]

    # --- level 3: everything received so far, parsed from the start on every call
    def whole_stream(self) -> tuple[list[Rows], str | None, str]:
        """Every complete message, the error that ends the stream if any, and the bytes of
        the unfinished message."""
        messages: list[Rows] = []
        pos = 0
        while True:
            pos = self.skip_blank(self.stream, pos)
            try:
                rows, pos = self.message(self.stream, pos)
            except IncompleteError:
                return messages, None, self.stream[pos:]
            except BadRequestError as bad:
                return messages, bad.code, ""
            messages.append(rows)

    def new_rows(self, messages: list[Rows]) -> Rows:
        fresh = messages[self.reported :]
        self.reported = len(messages)
        return [row for rows in fresh for row in rows]

    def feed(self, data: str) -> Rows:
        if self.closed:
            return []
        self.stream += data
        messages, error, _ = self.whole_stream()
        rows = self.new_rows(messages)
        if error is None:
            return rows
        self.closed = True
        return [*rows, ["error", error]]

    def pending(self, rest: str) -> bool:
        return rest != ""

    def close(self) -> Rows:
        if self.closed:
            return []
        self.closed = True
        return [["error", "incomplete"]] if self.pending(self.whole_stream()[2]) else []

    # --- level 4
    def set_limits(self, max_head_bytes: int, max_body_bytes: int) -> None:
        self.max_head = max_head_bytes
        self.max_body = max_body_bytes


# --- level 1 mistakes
class NamesKeepTheirCase(Model):
    """Reports field names as received."""

    def name_of(self, name: str) -> str:
        return name


class ValuesLowercased(Model):
    """Lowercases field values along with the names."""

    def trim(self, value: str) -> str:
        return value.strip(" \t").lower()


class TrimsEveryWhitespace(Model):
    """Trims every whitespace character, not only spaces and tabs."""

    def trim(self, value: str) -> str:
        return value.strip()


class KeepsTrailingWhitespace(Model):
    """Removes the whitespace before a value but not after it."""

    def trim(self, value: str) -> str:
        return value.lstrip(" \t")


class SpaceBeforeColonAllowed(Model):
    """Trims whitespace between the name and the colon instead of rejecting it."""

    def split_field(self, line: str) -> tuple[str, str]:
        name, colon, value = line.partition(":")
        return super().split_field(name.rstrip(" \t") + colon + value)


class ControlCharactersAllowed(Model):
    """Accepts any character in a value."""

    def field(self, line: str) -> tuple[str, str]:
        if self.folded(line):
            raise BadRequestError("obs-fold")
        name, raw = self.split_field(line)
        return self.name_of(name), self.trim(raw)


class FoldedLinesJoined(Model):
    """Replaces obsolete folding with a space and joins the line to the previous value."""

    def fields(self, lines: list[str]) -> list[tuple[str, str]]:
        joined: list[str] = []
        for line in lines:
            if self.folded(line) and joined:
                joined[-1] += " " + line.strip(" \t")
            else:
                joined.append(line)
        return [self.field(line) for line in joined]


class LoneLineFeedsAccepted(Model):
    """Treats a lone LF as a line end, as a lenient recipient may."""

    def check_endings(self, text: str) -> None:
        if re.search(r"\r(?!\n)", text):
            raise BadRequestError("bad-line-ending")

    def lines(self, text: str) -> list[str]:
        return re.split(r"\r?\n", text)


class RequestLineSplitOnAnyWhitespace(Model):
    """Splits the request line on runs of whitespace."""

    def request_parts(self, line: str) -> list[str]:
        return line.split()


class VersionCaseInsensitive(Model):
    """Accepts the version in any case."""

    def version_ok(self, version: str) -> bool:
        return VERSION.fullmatch(version.upper()) is not None


class NoHostRule(Model):
    """Never checks Host."""

    def host_ok(self, version: str, hosts: int) -> bool:
        return True


class DuplicateHostOnlyForHttp11(Model):
    """Checks the number of Host lines only for HTTP/1.1."""

    def host_ok(self, version: str, hosts: int) -> bool:
        return version != "HTTP/1.1" or hosts == 1


class EmptyLinesNotSkipped(Model):
    """Reads an empty line before the request line as the request line."""

    def skip_blank(self, data: str, pos: int) -> int:
        return pos


# --- level 2 mistakes
class LenientContentLength(Model):
    """Reads Content-Length with a lenient integer conversion."""

    def length(self, values: list[str]) -> int:
        try:
            return int(values[0])
        except ValueError:
            raise BadRequestError("bad-content-length") from None


class ChunkedCaseSensitive(Model):
    """Accepts only the lowercase spelling of chunked."""

    def codings_ok(self, codings: list[str]) -> bool:
        return codings == ["chunked"]


class FinalChunkedIsEnough(Model):
    """Accepts any list whose last coding is chunked."""

    def codings_ok(self, codings: list[str]) -> bool:
        return bool(codings) and codings[-1].lower() == "chunked"


class ChunkSizeInDecimal(Model):
    """Reads the chunk size as a decimal number."""

    def size_of_line(self, line: str) -> int:
        match = SIZE_LINE.fullmatch(line)
        if not match or not DIGITS.fullmatch(match.group(1)):
            raise BadRequestError("bad-chunk-size")
        return int(match.group(1))


class ExtensionsNotIgnored(Model):
    """Reads the whole size line as the size."""

    def size_of_line(self, line: str) -> int:
        if not re.fullmatch(r"[0-9A-Fa-f]+", line):
            raise BadRequestError("bad-chunk-size")
        return int(line, 16)


class TrailersMergedIntoFields(Model):
    """Reports trailer lines as header fields."""

    def trailer_rows(self, text: str) -> Rows:
        return [["field", *row[1:]] for row in super().trailer_rows(text)]


class TrailersDropped(Model):
    """Reads the trailer section and reports nothing of it."""

    def trailer_rows(self, text: str) -> Rows:
        super().trailer_rows(text)
        return []


class ChunkEndNotChecked(Model):
    """Skips the two bytes after the chunk data without checking them."""

    def chunk_end_ok(self, data: str, pos: int) -> bool:
        return True


class TrailerLinesNotChecked(Model):
    """Reports trailer lines without the field rules."""

    def trailer_rows(self, text: str) -> Rows:
        rows = []
        for line in text.split("\r\n"):
            name, _, value = line.partition(":")
            rows.append(["trailer", name.strip().lower(), value.strip()])
        return rows


# --- level 3 mistakes
class OneMessagePerFeed(Model):
    """Reports at most one message per call."""

    def new_rows(self, messages: list[Rows]) -> Rows:
        fresh = messages[self.reported : self.reported + 1]
        self.reported += len(fresh)
        return [row for rows in fresh for row in rows]


class KeepsParsingAfterAnError(Model):
    """Stays open after an error and reports later messages."""

    def feed(self, data: str) -> Rows:
        rows = super().feed(data)
        self.closed = False
        if rows and rows[-1][0] == "error":
            self.stream, self.reported = "", 0
        return rows


class ErrorDropsEarlierMessages(Model):
    """Reports only the error when a call also completed messages before it."""

    def feed(self, data: str) -> Rows:
        rows = super().feed(data)
        return rows[-1:] if rows and rows[-1][0] == "error" else rows


class CloseNeverIncomplete(Model):
    """Never reports an unfinished message at close."""

    def pending(self, rest: str) -> bool:
        return False


class LoneCarriageReturnIsNothing(Model):
    """Ignores a lone CR at close, as if it were a skipped empty line."""

    def pending(self, rest: str) -> bool:
        return rest not in ("", "\r")


# --- level 4 mistakes
class TransferEncodingWins(Model):
    """Lets Transfer-Encoding override Content-Length instead of refusing the message."""

    def resolve_both(self, rows: Rows, codings: list[str], lengths: list[str]) -> tuple[str, int]:
        if not self.codings_ok(self.elements(codings)):
            raise BadRequestError("unsupported-transfer-coding")
        return "chunked", 0


class ContentLengthWins(Model):
    """Frames by Content-Length when both fields are present."""

    def resolve_both(self, rows: Rows, codings: list[str], lengths: list[str]) -> tuple[str, int]:
        return "length", self.length(lengths)


class FirstContentLengthWins(Model):
    """Uses the first Content-Length value when values differ."""

    def length(self, values: list[str]) -> int:
        items = self.elements(values)
        if not items or not all(DIGITS.fullmatch(item) for item in items):
            raise BadRequestError("bad-content-length")
        return int(items[0])


class RepeatedLengthRejected(Model):
    """Rejects a repeated Content-Length even when the values agree."""

    def length(self, values: list[str]) -> int:
        if len(self.elements(values)) > 1:
            raise BadRequestError("conflicting-content-length")
        return super().length(values)


class LengthsComparedAsText(Model):
    """Compares repeated lengths as text, so 5 and 005 conflict."""

    def length(self, values: list[str]) -> int:
        items = self.elements(values)
        if items and all(DIGITS.fullmatch(item) for item in items) and len(set(items)) > 1:
            raise BadRequestError("conflicting-content-length")
        return super().length(values)


class LenientChunkSize(Model):
    """Reads the chunk size with a lenient integer conversion."""

    def size_of_line(self, line: str) -> int:
        try:
            return int(line.split(";")[0].strip(), 16)
        except ValueError:
            raise BadRequestError("bad-chunk-size") from None


class HeadLimitCheckedWhenComplete(Model):
    """Checks the head limit only once the head has fully arrived."""

    def head_end(self, data: str, pos: int) -> int:
        found = data.find(END, pos)
        if found == -1:
            raise IncompleteError
        if self.max_head is not None and found + 4 - pos > self.max_head:
            raise BadRequestError("head-too-large")
        return found + 4


class HeadLimitExclusive(Model):
    """Refuses a head of exactly the limit."""

    def head_end(self, data: str, pos: int) -> int:
        end = super().head_end(data, pos)
        if self.max_head is not None and end - pos >= self.max_head:
            raise BadRequestError("head-too-large")
        return end


class SkippedLinesCountTowardTheHead(Model):
    """Counts the skipped empty lines as part of the head."""

    def head(self, data: str, pos: int) -> tuple[Rows, int]:
        rows, end = super().head(data, pos)
        start = pos
        while start >= 2 and data[start - 2 : start] == "\r\n":
            start -= 2
        if self.max_head is not None and end - start > self.max_head:
            raise BadRequestError("head-too-large")
        return rows, end


class BodyLimitCheckedAfterReading(Model):
    """Checks Content-Length against the limit only once the body has arrived."""

    def length_over(self, size: int) -> bool:
        return False

    def message(self, data: str, pos: int) -> tuple[Rows, int]:
        rows, end = super().message(data, pos)
        body = rows[-1][1] if rows[-1][0] == "body" else ""
        if self.max_body is not None and len(body) > self.max_body:
            raise BadRequestError("body-too-large")
        return rows, end


class LimitPerChunk(Model):
    """Compares each chunk size with the limit instead of the running total."""

    def over(self, size: int, used: int) -> bool:
        return self.max_body is not None and size > self.max_body


class SizesWrapAt64Bits(Model):
    """Converts sizes into a 64-bit integer that wraps around."""

    def number(self, digits: str, base: int) -> int:
        return int(digits, base) % 2**64


class LeadingZerosCountAsDigits(Model):
    """Calls any size with more than 18 digits too large, leading zeros included."""

    def number(self, digits: str, base: int) -> int:
        return 10**30 if len(digits) > 18 else int(digits, base)


class HeadChecksTheBodyLimit(Model):
    """Applies the body limit in parseHead too."""

    def parse_head(self, data: str) -> Rows:
        rows = super().parse_head(data)
        try:
            if rows[0][0] == "request":
                self.framing(rows)
        except BadRequestError as bad:
            return [["error", bad.code]]
        return rows


class LimitsOnlyOnTheConnection(Model):
    """Applies the limits in feed but not in the one-shot methods."""

    def parse_message(self, data: str) -> Rows:
        limits = self.max_head, self.max_body
        self.max_head = self.max_body = None
        try:
            return super().parse_message(data)
        finally:
            self.max_head, self.max_body = limits


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()

METHODS = {
    "parseHead": "parse_head",
    "parseMessage": "parse_message",
    "feed": "feed",
    "close": "close",
    "setLimits": "set_limits",
}


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, METHODS[op])(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, RecursionError):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_reach_every_error_code():
    codes = {
        row[1]
        for case in HIDDEN_CASES
        for result in case["expected"]
        if isinstance(result, list)
        for row in result
        if row and row[0] == "error"
    }
    assert codes == {
        "incomplete",
        "bad-line-ending",
        "bad-request-line",
        "obs-fold",
        "bad-field",
        "bad-host",
        "bad-content-length",
        "unsupported-transfer-coding",
        "bad-chunk",
        "ambiguous-length",
        "conflicting-content-length",
        "bad-chunk-size",
        "head-too-large",
        "body-too-large",
    }


def test_every_character_of_the_data_is_ascii():
    for case in CASES:
        for arguments in case["args"]:
            for value in arguments:
                assert not isinstance(value, str) or value.isascii(), case["id"]
