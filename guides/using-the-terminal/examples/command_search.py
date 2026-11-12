"""How a shell finds a command: a builtin first, then each directory of PATH in order."""

BUILTINS = {"cd", "pwd", "export"}

# A pretend computer: each directory and the programs it holds.
PROGRAMS = {
    "/opt/homebrew/bin": {"python3", "uv"},
    "/usr/local/bin": {"python3"},
    "/usr/bin": {"python3", "git", "ls"},
    "/bin": {"cat", "ls"},
}


def find(name: str, path: str) -> str:
    if name in BUILTINS:
        return f"{name}: a shell builtin, no search needed"
    for checked, directory in enumerate(path.split(":"), start=1):
        if name in PROGRAMS.get(directory, set()):
            return f"{name}: runs {directory}/{name} (directory {checked} of PATH)"
    return f"{name}: command not found (searched all {len(path.split(':'))} directories)"


path = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
print("PATH =", path)
for name in ("python3", "git", "cat", "cd", "pyhton3"):
    print(" ", find(name, path))

reordered = "/usr/bin:/opt/homebrew/bin:/usr/local/bin:/bin"
print("PATH =", reordered)
print(" ", find("python3", reordered))

short = "/usr/bin:/bin"
print("PATH =", short)
print(" ", find("uv", short))
