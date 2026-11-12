"""A program gets a copy of its parent's environment, and ends with an exit status."""

import os
import subprocess
import sys


def run(code: str) -> subprocess.CompletedProcess[str]:
    """Run a small Python program as a child process, the way a shell runs a command."""
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)


os.environ["GREETING"] = "hello"
child = run("import os; print(os.environ.get('GREETING'))")
print("the child sees GREETING =", child.stdout.strip())

child = run("import os; os.environ['GREETING'] = 'changed'; print(os.environ['GREETING'])")
print("the child changed its copy to", child.stdout.strip())
print("the parent still has GREETING =", os.environ["GREETING"])

child = run("import os; print(os.environ.get('NOT_SET_ANYWHERE', '(not set)'))")
print("a variable nobody set:", child.stdout.strip())

success = run("print('all good')")
print("success: exit status", success.returncode, "| output:", success.stdout.strip())

failure = run("print(10 / 0)")
print("failure: exit status", failure.returncode, "| output:", repr(failure.stdout))
print("the error went to standard error; its last line is:")
print(" ", failure.stderr.strip().splitlines()[-1])
