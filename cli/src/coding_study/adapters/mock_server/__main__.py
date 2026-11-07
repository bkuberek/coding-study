"""Runs the mock server from this folder alone: `python -I <this folder> <config.json>`.

Running a folder puts the folder itself on `sys.path`, but its modules import each other relatively,
so they need its parent there, to load as a package named after the folder.
"""

import importlib
import sys
from pathlib import Path

FOLDER = Path(__file__).resolve().parent

if __name__ == "__main__":
    sys.path[0] = str(FOLDER.parent)
    program = importlib.import_module(f"{FOLDER.name}.program")
    sys.exit(program.main(sys.argv[1:]))
