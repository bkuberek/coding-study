"""Write an HTTP/1.1 request and response as bytes, each body framed a different way.

The request's body has a known length, so a Content-Length field announces it. The response's
body is produced in pieces, so it is sent with the chunked transfer coding: each chunk is its
size in hexadecimal, CRLF, the data and CRLF, and a chunk of size zero ends the body.
"""

CRLF = "\r\n"


def head(start_line: str, fields: list[tuple[str, str]]) -> str:
    lines = [start_line] + [f"{name}: {value}" for name, value in fields]
    return CRLF.join(lines) + CRLF + CRLF  # the empty line ends the head


def chunked(pieces: list[str]) -> str:
    body = "".join(f"{len(piece):x}{CRLF}{piece}{CRLF}" for piece in pieces)
    return body + "0" + CRLF + CRLF  # the last chunk, then an empty trailer section


def show(label: str, message: str) -> None:
    print(f"{label} ({len(message)} bytes):")
    *lines, rest = message.split(CRLF)
    for line in lines:
        print(f"  {line}\\r\\n")
    if rest:
        print(f"  {rest}")


content = '{"item": "pear", "qty": 3}'
request = (
    head(
        "POST /orders HTTP/1.1",
        [
            ("Host", "example.com"),
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(content))),
        ],
    )
    + content
)
show("request", request)

pieces = ["order 41: ", "3 pears, ", "confirmed"]
response = head(
    "HTTP/1.1 201 Created",
    [("Content-Type", "text/plain"), ("Transfer-Encoding", "chunked")],
) + chunked(pieces)
show("response", response)
body = chunked(pieces)
print(f"chunk sizes: {[f'{len(piece):x}' for piece in pieces]} in hexadecimal")
print(f"the content is {len(''.join(pieces))} bytes; chunked, the body is {len(body)} bytes")
