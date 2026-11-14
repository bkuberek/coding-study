"""Storing a hash of a random token is safe; hashing a value with few possibilities hides nothing."""

import hashlib
import hmac
import secrets

# A session or reset token: 32 random bytes. The database keeps only its SHA-256.
token = secrets.token_urlsafe(32)
stored = hashlib.sha256(token.encode()).hexdigest()
print("token length:", len(token), "characters; stored hash length:", len(stored))


def matches(presented: str) -> bool:
    return hmac.compare_digest(hashlib.sha256(presented.encode()).hexdigest(), stored)


print("the real token matches:", matches(token))
print("a guess matches:       ", matches(secrets.token_urlsafe(32)))

# A four-digit code "redacted" by hashing it. There are only 10,000 codes to try.
leaked = hashlib.sha256(b"4071").hexdigest()
for n in range(10_000):
    guess = f"{n:04d}"
    if hashlib.sha256(guess.encode()).hexdigest() == leaked:
        print("code recovered from its hash:", guess, "after", n + 1, "tries")
        break
