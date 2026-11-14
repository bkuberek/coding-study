"""A file name crossing into a command line: as one item of a list, then glued into shell text."""

import shlex
import subprocess
import sys

name = "notes.txt; rm -rf ~"

# As one item of a list, the name reaches the program as one argument, and no shell reads it.
# The program here is a second Python that prints the arguments it received.
child = subprocess.run(
    [sys.executable, "-c", "import sys; print(sys.argv[1:])", name],
    capture_output=True,
    text=True,
    check=True,
)
print("the program received:", child.stdout.strip())

# Glued into one string for a shell, the same name splits at ';' into a second command.
tokens = shlex.shlex("wc -l " + name, posix=True, punctuation_chars=True)
tokens.whitespace_split = True
print("a shell would read:  ", list(tokens))
