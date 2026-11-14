"""Build the bytes of a DNS query the way RFC 1035 lays them out, and read them back.

A message is a 12-byte header, then the question: the name as labels, each a length byte and
that many letters, ending with the empty label of the root, then a two-byte type and a two-byte
class. Every number is sent with its most significant byte first.
"""

import struct

TYPES = {"A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "MX": 15, "AAAA": 28}
CLASS_IN = 1  # the Internet
FLAG_RD = 0x0100  # Recursion Desired: "do the whole walk for me"


def encode_name(name: str) -> bytes:
    encoded = b""
    for label in name.split("."):
        if not 1 <= len(label) <= 63:
            raise ValueError(f"a label has 1 to 63 octets, not {len(label)}")
        encoded += bytes([len(label)]) + label.encode("ascii")
    encoded += b"\x00"  # the root's label is empty
    if len(encoded) > 255:
        raise ValueError("a name has at most 255 octets")
    return encoded


def build_query(message_id: int, name: str, qtype: str) -> bytes:
    header = struct.pack("!HHHHHH", message_id, FLAG_RD, 1, 0, 0, 0)  # one question, no records
    return header + encode_name(name) + struct.pack("!HH", TYPES[qtype], CLASS_IN)


def decode_name(data: bytes, offset: int) -> tuple[str, int]:
    labels = []
    while (length := data[offset]) != 0:
        labels.append(data[offset + 1 : offset + 1 + length].decode("ascii"))
        offset += 1 + length
    return ".".join(labels), offset + 1


query = build_query(0x1234, "www.example.org", "AAAA")
print(f"{len(query)} bytes:")
for start in range(0, len(query), 16):
    print("  " + query[start : start + 16].hex(" "))

message_id, flags, questions, answers, authority, additional = struct.unpack("!HHHHHH", query[:12])
print(f"id {message_id:#06x}, QR {flags >> 15} (a query), RD {(flags & FLAG_RD) >> 8}")
print(
    f"sections: {questions} question, {answers} answer, {authority} authority, "
    f"{additional} additional"
)
name, offset = decode_name(query, 12)
qtype, qclass = struct.unpack("!HH", query[offset : offset + 4])
print(f"question: {name}, type {qtype}, class {qclass}")
try:
    encode_name("a" * 64 + ".example.org")
except ValueError as error:
    print("refused:", error)
