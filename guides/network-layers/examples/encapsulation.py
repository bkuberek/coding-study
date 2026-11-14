"""Wrap an HTTP request in a TCP header and an IPv4 header, then unwrap it again.

Each layer puts its own header in front of what the layer above handed it, and on the way back
up each layer reads only its own header. The headers follow the field layouts of RFC 9293 (TCP)
and RFC 791 (IPv4); the checksums and control bits are left at zero, since nothing here crosses
a real wire.
"""

import struct

PROTOCOL_TCP = 6  # the IPv4 Protocol field's value for a TCP segment


def address_bytes(address: str) -> bytes:
    return bytes(int(part) for part in address.split("."))


def address_text(raw: bytes) -> str:
    return ".".join(str(part) for part in raw)


def tcp_segment(source_port: int, destination_port: int, seq: int, payload: bytes) -> bytes:
    offset_words = 5  # header length in 32-bit words: 5 * 4 = 20 bytes, no options
    header = struct.pack(
        "!HHIIBBHHH",
        source_port,
        destination_port,
        seq,
        0,  # acknowledgement number
        offset_words << 4,  # data offset in the high 4 bits
        0,  # control bits
        65535,  # window
        0,  # checksum
        0,  # urgent pointer
    )
    return header + payload


def ipv4_datagram(source: str, destination: str, payload: bytes) -> bytes:
    header_words = 5
    total_length = header_words * 4 + len(payload)
    header = struct.pack(
        "!BBHHHBBH4s4s",
        (4 << 4) | header_words,  # version 4, header length in 32-bit words
        0,  # type of service
        total_length,
        0,  # identification
        0,  # flags and fragment offset
        64,  # time to live
        PROTOCOL_TCP,
        0,  # header checksum
        address_bytes(source),
        address_bytes(destination),
    )
    return header + payload


message = b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"
segment = tcp_segment(50000, 80, 1000, message)
datagram = ipv4_datagram("192.0.2.10", "198.51.100.80", segment)
print(f"HTTP message:  {len(message)} bytes  {message!r}")
print(f"TCP segment:   {len(segment)} bytes  (a 20-byte header, then the message)")
print(f"IPv4 datagram: {len(datagram)} bytes  (a 20-byte header, then the segment)")
print("the IPv4 header on the wire:", datagram[:20].hex(" "))

first, _, total, _, _, ttl, protocol, _, source, destination = struct.unpack(
    "!BBHHHBBH4s4s", datagram[:20]
)
ip_header = (first & 0x0F) * 4
print(
    f"IPv4 reads: version {first >> 4}, header {ip_header} bytes, total {total} bytes, "
    f"TTL {ttl}, protocol {protocol}, {address_text(source)} -> {address_text(destination)}"
)
inner = datagram[ip_header:total]
source_port, destination_port, seq, _, offset, *_ = struct.unpack("!HHIIBBHHH", inner[:20])
tcp_header = (offset >> 4) * 4
print(
    f"TCP reads: port {source_port} -> port {destination_port}, sequence number {seq}, "
    f"header {tcp_header} bytes"
)
print("HTTP reads:", inner[tcp_header:].split(b"\r\n")[0].decode("ascii"))
