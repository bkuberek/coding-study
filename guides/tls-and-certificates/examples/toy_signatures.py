"""What a signature on a certificate proves, with textbook RSA on small numbers.

The numbers are far too small to be secure, and real signatures add padding: this shows the
idea only. Signing uses the private exponent d, which only the key's owner has; checking uses
the public pair (n, e), which anyone may have.
"""

import hashlib


def is_prime(n: int) -> bool:
    return n > 1 and all(n % k for k in range(2, int(n**0.5) + 1))


def make_key(p: int, q: int, e: int = 65537) -> dict:
    assert is_prime(p) and is_prime(q)
    return {"n": p * q, "e": e, "d": pow(e, -1, (p - 1) * (q - 1))}


def digest(text: str, n: int) -> int:
    return int.from_bytes(hashlib.sha256(text.encode()).digest()) % n


def sign(text: str, key: dict) -> int:
    return pow(digest(text, key["n"]), key["d"], key["n"])


def checks(text: str, signature: int, public: dict) -> bool:
    return pow(signature, public["e"], public["n"]) == digest(text, public["n"])


ca = make_key(1_000_003, 1_000_033)
attacker = make_key(1_000_037, 1_000_039)
ca_public = {"n": ca["n"], "e": ca["e"]}

certificate = "subject=shop.example; issuer=Example CA; key=<shop's public key>"
signature = sign(certificate, ca)
print("genuine certificate checks:", checks(certificate, signature, ca_public))

edited = certificate.replace("shop.example", "bank.example")
print("edited after signing:      ", checks(edited, signature, ca_public))

forged = "subject=bank.example; issuer=Example CA; key=<attacker's public key>"
print("names the CA, signed by someone else:", checks(forged, sign(forged, attacker), ca_public))
