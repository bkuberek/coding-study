"""Split the responses that arrive on one persistent connection, using only their framing.

A client sent three GET requests one after another without waiting, and the server answered
them in the same order. Nothing in the bytes says where a response ends except its head: here,
each head's Content-Length. This reader trusts its input and handles only that one framing; a
real one checks every rule of RFC 9112 and refuses what it cannot frame.
"""

CRLF = "\r\n"
RECEIVED = (
    "HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\npears"
    "HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n"
    "HTTP/1.1 200 OK\r\nContent-Length: 13\r\n\r\nplums\r\n\r\nfigs"
)


def split_responses(data: str) -> list[tuple[str, str]]:
    responses = []
    while data:
        head_end = data.index(CRLF + CRLF)
        status_line, *field_lines = data[:head_end].split(CRLF)
        fields = {}
        for line in field_lines:
            name, value = line.split(":", 1)
            fields[name.lower()] = value.strip(" \t")
        length = int(fields["content-length"])
        body_start = head_end + len(CRLF + CRLF)
        responses.append((status_line, data[body_start : body_start + length]))
        data = data[body_start + length :]
    return responses


for request, (status, body) in zip(
    ["/pears", "/apples", "/plums"], split_responses(RECEIVED), strict=True
):
    print(f"GET {request:<8} -> {status:<22} body {body!r}")
naive = RECEIVED.split(CRLF + CRLF)
print(f"cutting at every empty line instead gives {len(naive)} pieces, not 3 heads and bodies")
