"""A permission gate between an agent's proposed actions and the tools that would carry them out.

Rules are checked in a fixed order of strictness: any matching deny wins, then any matching ask,
then any matching allow; an action that no rule matches is denied. The user's answers are scripted.
"""

from pathlib import PurePosixPath

KNOWN_CHECKS = {"pytest -q", "ruff check ."}


def escapes(path: str) -> bool:
    """True when the path, taken from the workspace root, leaves the workspace."""
    depth = 0
    for part in PurePosixPath(path).parts:
        if part == "/":
            return True
        depth += -1 if part == ".." else 0 if part == "." else 1
        if depth < 0:
            return True
    return False


RULES = [  # (decision, tool, test on the argument, reason)
    ("deny", "read_file", escapes, "outside the workspace"),
    ("deny", "write_file", escapes, "outside the workspace"),
    ("deny", "write_file", lambda path: PurePosixPath(path).name == ".env", "secrets are never written"),
    ("deny", "run", lambda command: command.split()[0] in {"rm", "curl", "sudo"}, "never run"),
    ("ask", "write_file", lambda path: True, "a file would change"),
    ("ask", "run", lambda command: command not in KNOWN_CHECKS, "an unknown command"),
    ("allow", "read_file", lambda path: True, "reading inside the workspace"),
    ("allow", "run", lambda command: command in KNOWN_CHECKS, "a known check"),
]


def decide(tool: str, argument: str) -> tuple[str, str]:
    for strictness in ("deny", "ask", "allow"):
        for decision, rule_tool, test, reason in RULES:
            if decision == strictness and rule_tool == tool and test(argument):
                return decision, reason
    return "deny", "no rule allows it"


proposed = [
    ("read_file", "src/app.py"),
    ("run", "pytest -q"),
    ("write_file", "src/app.py"),
    ("write_file", "config/.env"),
    ("read_file", "docs/../../secrets.txt"),
    ("read_file", "/etc/passwd"),
    ("run", "rm -rf build"),
    ("run", "make deploy"),
    ("send_email", "team@example.com"),
]
user_says_yes = {("write_file", "src/app.py"): True, ("run", "make deploy"): False}
for tool, argument in proposed:
    decision, reason = decide(tool, argument)
    if decision == "ask":
        decision = "allowed by the user" if user_says_yes[(tool, argument)] else "declined by the user"
    print(f"{tool}({argument}): {decision}, {reason}")
