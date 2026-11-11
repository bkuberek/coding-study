"""A hash function maps a key to a number, and the number picks a bucket."""

BUCKETS = 8


def letter_sum(key: str) -> int:
    """A poor hash: it ignores the order of the letters."""
    return sum(ord(character) for character in key)


def polynomial(key: str) -> int:
    """A better one: each letter is weighted by its position (31 is a common multiplier)."""
    value = 0
    for character in key:
        value = (value * 31 + ord(character)) % 2**32
    return value


def bucket(key: str, hash_function) -> int:
    return hash_function(key) % BUCKETS


print("same key, same bucket:", bucket("pear", polynomial) == bucket("pear", polynomial))
for word in ("pear", "plum", "fig"):
    print(f"{word:>5} -> hash {polynomial(word):>10} -> bucket {bucket(word, polynomial)}")

print("letter_sum: listen", bucket("listen", letter_sum), "silent", bucket("silent", letter_sum))
print("polynomial: listen", bucket("listen", polynomial), "silent", bucket("silent", polynomial))

nine = ["ash", "elm", "fir", "oak", "yew", "bay", "box", "fig", "lime"]
used = {bucket(word, polynomial) for word in nine}
print(f"{len(nine)} keys, {BUCKETS} buckets, {len(used)} buckets used: a collision is certain")

keys = [f"user{number}" for number in range(1000)]
for name, function in (("letter_sum", letter_sum), ("polynomial", polynomial)):
    sizes = [0] * 64
    for key in keys:
        sizes[function(key) % 64] += 1
    print(f"{name:>10}: 1000 keys in 64 buckets, largest bucket {max(sizes)}, empty {sizes.count(0)}")

no_collision = 1.0
for placed in range(23):
    no_collision *= (365 - placed) / 365
print(f"23 keys in 365 buckets, hashed at random: a collision {1 - no_collision:.1%} of the time")
