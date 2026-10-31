"""The grading job of a project problem (docs/specs/runners.md#grading-job).

A grading job is a class job whose target is the project folder. The runner checks, when the job
loads, that every method the request declares exists, so the request declares only the methods
of the levels it grades: a method of a locked level never has to exist.
"""

from dataclasses import replace

from coding_study.domain.signature import ClassSignature, Signature


def graded_signature(signature: Signature, level: int) -> ClassSignature:
    """The entry class with the methods of levels 1 to `level`, and any method without a level.

    Raises ValueError for a function signature, which has no levels.
    """
    if not isinstance(signature, ClassSignature):
        raise ValueError(f"a graded signature is a class signature, not {signature.name}()")
    methods = tuple(
        method for method in signature.methods if method.level is None or method.level <= level
    )
    return replace(signature, methods=methods)
