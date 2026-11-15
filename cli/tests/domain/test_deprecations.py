"""The deprecation registry and its warning line (docs/specs/compatibility.md#deprecation)."""

from coding_study.domain.deprecations import (
    DEPRECATIONS,
    DeprecatedSurface,
    Deprecation,
    deprecated_names,
    deprecation_notice,
    is_deprecated_flag,
)

FLAG = Deprecation(DeprecatedSurface.FLAG, "cstudy stats --since", "0.60.0", "cstudy stats --from")
KEY = Deprecation(DeprecatedSurface.CONFIG_KEY, "next.old", "0.61.0")
VARIABLE = Deprecation(DeprecatedSurface.ENV_VAR, "CSTUDY_OLD", "0.62.0", "CSTUDY_NEW")
FIELD = Deprecation(DeprecatedSurface.JSON_FIELD, "stats.old", "0.63.0")
REGISTRY = (FLAG, KEY, VARIABLE, FIELD)


def test_the_registry_is_empty_in_this_release() -> None:
    assert DEPRECATIONS == ()


def test_the_notice_names_the_version_the_removal_and_the_replacement() -> None:
    assert deprecation_notice(FLAG) == (
        "warning: cstudy stats --since is deprecated since cstudy 0.60.0"
        " and is removed in 2.0; use cstudy stats --from"
    )


def test_the_notice_has_no_use_clause_without_a_replacement() -> None:
    assert deprecation_notice(KEY) == (
        "warning: next.old is deprecated since cstudy 0.61.0 and is removed in 2.0"
    )


def test_names_are_those_of_one_surface() -> None:
    assert deprecated_names(DeprecatedSurface.ENV_VAR, REGISTRY) == {"CSTUDY_OLD"}
    assert deprecated_names(DeprecatedSurface.CONFIG_KEY, REGISTRY) == {"next.old"}
    assert deprecated_names(DeprecatedSurface.FLAG, ()) == frozenset()


def test_a_flag_is_deprecated_by_its_command_and_name() -> None:
    assert is_deprecated_flag("cstudy stats", "--since", REGISTRY)
    assert not is_deprecated_flag("cstudy stats", "--from", REGISTRY)
    assert not is_deprecated_flag("cstudy history", "--since", REGISTRY)


def test_nothing_is_deprecated_in_the_empty_registry() -> None:
    assert not is_deprecated_flag("cstudy stats", "--json")
