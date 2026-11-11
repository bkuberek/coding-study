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


# 3. A hash chain: each head covers its entry and every head before it.
def heads(entries: list[str]) -> list[bytes]:
    head = sha256(b"audit-log v1")  # a fixed starting value
    chain = []
    for entry in entries:
        head = sha256(head + sha256(entry.encode()))
        chain.append(head)
    return chain


log = ["alice logs in", "alice reads report", "bob logs in", "alice logs out"]
tampered = [*log]
tampered[1] = "alice deletes report"
original, edited = heads(log), heads(tampered)
print("heads equal per entry:", [a == b for a, b in zip(original, edited, strict=True)])

# 4. Anyone can recompute a plain hash after editing. A keyed MAC needs the secret.
key = b"server-secret"
tag = hmac.new(key, b"amount=10", hashlib.sha256).digest()
forged = hmac.new(b"guessed-key", b"amount=99", hashlib.sha256).digest()
genuine = hmac.new(key, b"amount=10", hashlib.sha256).digest()
print("MAC of the edit with a guessed key accepted:", hmac.compare_digest(tag, forged))
print("MAC recomputed with the real key accepted:", hmac.compare_digest(tag, genuine))
