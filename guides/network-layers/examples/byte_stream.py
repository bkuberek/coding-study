"""Three messages carried two ways: as datagrams, and as one byte stream.

A datagram channel delivers each message whole or not at all; this one loses the second. A stream
channel delivers every byte, in order, but in pieces of its own sizes, so the receiver's reads do
not line up with the sender's writes. The messages end with a newline, which is how the receiver
finds them again in the stream.
"""

MESSAGES = [b"PING 1\n", b"PRICE apples=3\n", b"BYE\n"]
PIECE_SIZES = [5, 9, 3]  # how many bytes each read happens to get, used in turn


def datagram_channel(datagrams: list[bytes], lost: set[int]) -> list[bytes]:
    return [datagram for number, datagram in enumerate(datagrams) if number not in lost]


def stream_channel(writes: list[bytes]) -> list[bytes]:
    stream = b"".join(writes)
    reads, position, turn = [], 0, 0
    while position < len(stream):
        size = PIECE_SIZES[turn % len(PIECE_SIZES)]
        reads.append(stream[position : position + size])
        position, turn = position + size, turn + 1
    return reads


print("datagrams sent:     ", MESSAGES)
print("datagrams received: ", datagram_channel(MESSAGES, lost={1}))
reads = stream_channel(MESSAGES)
print("stream writes:      ", MESSAGES)
print("stream reads:       ", reads)
received = b"".join(reads)
print("same bytes, in order:", received == b"".join(MESSAGES))
print("messages, cut at each newline:", [line + b"\n" for line in received.split(b"\n")[:-1]])
