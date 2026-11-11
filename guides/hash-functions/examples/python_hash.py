"""Python's own hash(): equal values hash alike, and str hashes change between runs."""

import os
import subprocess
import sys

print("1 == 1.0 == True:", 1 == 1.0 == True)
print("hash(1) == hash(1.0) == hash(True):", hash(1) == hash(1.0) == hash(True))
print("a tuple of hashable values is hashable:", hash((1, "a")) == hash((1, "a")))

try:
    hash([1, 2])
except TypeError as error:
    print("a list is not hashable:", type(error).__name__)


def hash_in_new_process(expression: str, seed: str) -> str:
    """hash(expression) in a fresh interpreter whose PYTHONHASHSEED is `seed`."""
    environment = {**os.environ, "PYTHONHASHSEED": seed}
    command = [sys.executable, "-c", f"print(hash({expression}))"]
    return subprocess.run(command, env=environment, capture_output=True, text=True).stdout


pear = "'pear'"
print("str, same seed:", hash_in_new_process(pear, "1") == hash_in_new_process(pear, "1"))
print("str, other seed:", hash_in_new_process(pear, "1") == hash_in_new_process(pear, "2"))
print("int, other seed:", hash_in_new_process("12345", "1") == hash_in_new_process("12345", "2"))
pair = "('pear', 'plum')"
print("tuple of str, other seed:", hash_in_new_process(pair, "1") == hash_in_new_process(pair, "2"))
