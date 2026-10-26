"""Checking that generated stubs compile or import (`cstudy verify` D1).

A stub is built and loaded through the runner like a reference approach under a reserved
approach id. JVM references declare no package (the materializer prepends one), so the stub's
`package practice.<snake_slug>` line is dropped first.
"""

import re

from coding_study.domain.layout import JVM_LANGUAGES
from coding_study.domain.problem import Language

STUB_APPROACH_ID = "generated-stub"
STUB_DIRECTORY = ".cs/build/stubs"
_PACKAGE_LINE = re.compile(r"^package [\w.]+;?[ \t]*\n", re.MULTILINE)


def stub_as_reference(stub: str, language: Language) -> str:
    if language not in JVM_LANGUAGES:
        return stub
    return _PACKAGE_LINE.sub("", stub, count=1)
