"""SHA-256 digests, the encodings that make them trustworthy, and a hash chain over a log."""

import hashlib
import hmac


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


# 1. A digest has a fixed size, and a one-letter change scrambles it.
first, second = sha256(b"backup.tar"), sha256(b"backup.tas")
changed = bin(int.from_bytes(first) ^ int.from_bytes(second)).count("1")
print("digest bytes:", len(first), "| hex:", first.hex()[:16] + "...")
print(f"one letter changed: {changed} of 256 bits differ")


# 2. Encodings. Joining fields loses where one ends and the next begins.
def joined(fields: list[str]) -> bytes:
    return "".join(fields).encode()


def with_separator(fields: list[str]) -> bytes:
    return "|".join(fields).encode()


def length_prefixed(fields: list[str]) -> bytes:
    """Each field as its byte length, a colon, its bytes and a comma: 2:ab,1:c,"""
    return b"".join(b"%d:%s," % (len(raw), raw) for raw in (field.encode() for field in fields))


pairs = [(["ab", "c"], ["a", "bc"]), (["a|b", "c"], ["a", "b|c"])]
for encode in (joined, with_separator, length_prefixed):
    collisions = [sha256(encode(one)) == sha256(encode(other)) for one, other in pairs]
    print(f"{encode.__name__:>15}: collisions {collisions}")


# 3. A hash chain: each chain digest covers its entry and every chain digest before it.
def chain_digests(entries: list[str]) -> list[bytes]:
    digest = sha256(b"audit-log v1")  # a fixed starting value
    chain = []
    for entry in entries:
        digest = sha256(digest + sha256(entry.encode()))
        chain.append(digest)
    return chain


log = ["alice logs in", "alice reads report", "bob logs in", "alice logs out"]
tampered = [*log]
tampered[1] = "alice deletes report"
original, edited = chain_digests(log), chain_digests(tampered)
print("chain digests equal per entry:", [a == b for a, b in zip(original, edited, strict=True)])

# 4. Anyone can recompute a plain hash after editing. A MAC needs the secret key: the receiver
# recomputes the tag of the message it received and compares it with the tag it received.
KEY = b"server-secret"


def tag_of(message: bytes, key: bytes = KEY) -> bytes:
    return hmac.new(key, message, hashlib.sha256).digest()


def accept(received_message: bytes, received_tag: bytes) -> bool:
    return hmac.compare_digest(tag_of(received_message), received_tag)


message = b"amount=10"
tag = tag_of(message)
edited = b"amount=99"
print("edited message, tag made with a guessed key:", accept(edited, tag_of(edited, b"guess")))
print("edited message, the original tag:", accept(edited, tag))
print("the original message and tag:", accept(message, tag))
