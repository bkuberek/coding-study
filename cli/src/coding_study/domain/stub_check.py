"""Checking that generated stubs compile or import (`cstudy verify` D1).

A stub is built and loaded through the runner like a reference approach under a reserved
approach id. JVM references declare no package (the materializer prepends one), so the stub's
`package practice.<snake_slug>` line is dropped first.
"""

import re
from typing import assert_never

from coding_study.domain.problem import Language

STUB_APPROACH_ID = "generated-stub"
STUB_DIRECTORY = ".cs/build/stubs"
_PACKAGE_LINE = re.compile(r"^package [\w.]+;?[ \t]*\n", re.MULTILINE)


def stub_as_reference(stub: str, language: Language) -> str:
    match language:
        case Language.PYTHON | Language.TYPESCRIPT:
            return stub
        case Language.JAVA | Language.KOTLIN:
            return _PACKAGE_LINE.sub("", stub, count=1)
        case _:
            assert_never(language)
