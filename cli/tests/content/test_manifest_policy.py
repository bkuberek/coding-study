"""manifest-policy promises that its hidden cases catch the classic mistakes of policy checks on
deployment manifests: a null or an empty text taken as present, a registry port read as a tag, a
digest ignored, manifests, rules or list items reported in the wrong order, a wildcard that walks
an object or invents a list, selectors that match too much, a port that one workload is enough to
serve, exceptions that end a day early, cover too much or vanish when they expire, and severities,
modes and fixes that are applied the wrong way. These tests replay every case against a model
written from the statement, which must give every expected output, and against that model with
one mistake planted at a time, which some hidden case must fail.

The model takes another route than the reference: it keeps each manifest as a flat map from
JSON Pointer to value, expands a pattern by matching the pointers of that map, and orders the
findings by walking the severities from the most severe."""

import json
import re
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0344-manifest-policy"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]
SEVERITIES = ("critical", "high", "medium", "low")
DATE_ARGUMENT = {"allow": 3, "check_on": 0, "findings": 0, "decide": 0}

Flat = dict[str, tuple[str, str]]


class Model:
    """The checker as the statement words it. Each mistake below overrides one method."""

    def __init__(self) -> None:
        self.manifests: dict[str, Flat] = {}
        self.rules: list[dict[str, Any]] = []
        self.exceptions: list[dict[str, Any]] = []

    # --- level 1
    def add_manifest(self, rows: list[list[str]]) -> bool:
        flat = {pointer: (kind, text) for pointer, kind, text in rows}
        manifest_id = self.identity(flat)
        new = manifest_id not in self.manifests
        self.manifests[manifest_id] = flat
        return new

    def identity(self, flat: Flat) -> str:
        return f"{flat['/kind'][1]}/{flat['/name'][1]}"

    def define(self, rule_id: str, **definition: Any) -> bool:
        for rule in self.rules:
            if rule["id"] == rule_id:
                self.redefine(rule, definition)
                return False
        self.rules.append(
            {"id": rule_id, "severity": "medium", "mode": "deny", "fix": "", **definition}
        )
        return True

    def redefine(self, rule: dict[str, Any], definition: dict[str, Any]) -> None:
        rule.update(definition)

    def require_field(self, rule_id: str, kind: str, pointer: str) -> bool:
        return self.define(rule_id, check="field", kind=kind, pointer=pointer, tags=[])

    def forbid_tags(self, rule_id: str, kind: str, pointer: str, tags: list[str]) -> bool:
        return self.define(rule_id, check="tags", kind=kind, pointer=pointer, tags=list(tags))

    def check(self) -> list[list[str]]:
        return [list(violation) for violation in self.violations()]

    def manifest_order(self) -> list[str]:
        return sorted(self.manifests)

    def rule_order(self) -> list[dict[str, Any]]:
        return self.rules

    def applies(self, rule: dict[str, Any], flat: Flat) -> bool:
        return rule["kind"] in ("*", flat["/kind"][1])

    def violations(self) -> list[tuple[str, str, str]]:
        found = []
        for manifest_id in self.manifest_order():
            flat = self.manifests[manifest_id]
            for rule in self.rule_order():
                if self.applies(rule, flat):
                    found += [(manifest_id, rule["id"], p) for p in self.failing(rule, flat)]
        return found

    def failing(self, rule: dict[str, Any], flat: Flat) -> list[str]:
        if rule["check"] == "ports":
            return self.port_problems(flat)
        pointers = self.order_pointers(self.expand(flat, rule["pointer"]))
        if rule["check"] == "field":
            return [p for p in pointers if self.missing(flat.get(p))]
        return [p for p in pointers if self.moving(flat.get(p), rule["tags"])]

    def order_pointers(self, pointers: list[str]) -> list[str]:
        return pointers

    def missing(self, value: tuple[str, str] | None) -> bool:
        return value is None or value[0] == "null" or value == ("string", "")

    def moving(self, value: tuple[str, str] | None, tags: list[str]) -> bool:
        if value is None or value[0] != "string":
            return self.non_text_image(value)
        image = value[1]
        if self.pinned(image):
            return False
        tag = self.tag(image)
        return tag is None or self.listed(tag, tags)

    def non_text_image(self, value: tuple[str, str] | None) -> bool:
        return False

    def pinned(self, image: str) -> bool:
        return "@" in image

    def tag(self, image: str) -> str | None:
        match = re.search(r":([^:/]*)$", image)
        return match.group(1) if match else None

    def listed(self, tag: str, tags: list[str]) -> bool:
        return tag in tags

    def expand(self, flat: Flat, pattern: str) -> list[str]:
        prefixes = [""]
        for segment in pattern.split("/")[1:]:
            if segment != "*":
                prefixes = [f"{prefix}/{segment}" for prefix in prefixes]
                continue
            prefixes = [item for prefix in prefixes for item in self.items_of(flat, prefix)]
        return prefixes

    def items_of(self, flat: Flat, prefix: str) -> list[str]:
        if flat.get(prefix, ("",))[0] != "array":
            return self.no_list(flat, prefix)
        count = sum(1 for p in flat if re.fullmatch(re.escape(prefix) + r"/\d+", p))
        return [f"{prefix}/{index}" for index in range(count)]

    def no_list(self, flat: Flat, prefix: str) -> list[str]:
        return []

    # --- level 2
    def require_port_targets(self, rule_id: str) -> bool:
        return self.define(rule_id, check="ports", kind="service", pointer="", tags=[])

    def port_problems(self, service: Flat) -> list[str]:
        selector = {
            p.rsplit("/", 1)[1]: value
            for p, value in service.items()
            if re.fullmatch(r"/selector/[^/]+", p)
        }
        picked = [m for m in self.manifests.values() if self.picked(selector, m)]
        if not picked or not self.selector_usable(service, selector):
            return ["/selector"]
        problems = []
        for port in self.items_of(service, "/ports"):
            target = service.get(f"{port}/target")
            if target is None or target[0] != "string":
                if self.unnamed_port_fails():
                    problems.append(f"{port}/target")
                continue
            if not self.served(target[1], picked):
                problems.append(f"{port}/target")
        return problems

    def unnamed_port_fails(self) -> bool:
        return False

    def selector_usable(self, service: Flat, selector: dict[str, tuple[str, str]]) -> bool:
        return service.get("/selector", ("",))[0] == "object" and bool(selector)

    def picked(self, selector: dict[str, tuple[str, str]], manifest: Flat) -> bool:
        if not self.selectable(manifest) or not selector:
            return False
        return all(self.label_matches(manifest.get(f"/labels/{k}"), v) for k, v in selector.items())

    def selectable(self, manifest: Flat) -> bool:
        return manifest.get("/kind") == ("string", "workload")

    def label_matches(self, label: tuple[str, str] | None, wanted: tuple[str, str]) -> bool:
        return label == wanted and wanted[0] == "string"

    def served(self, target: str, picked: list[Flat]) -> bool:
        return all(target in self.port_names(workload) for workload in picked)

    def port_names(self, workload: Flat) -> set[str]:
        names = set()
        for p in self.expand(workload, "/containers/*/ports/*/name"):
            if workload.get(p, ("",))[0] == "string":
                names.add(workload[p][1])
        return names

    # --- level 3
    def allow(self, rule_id: str, manifest_id: str, reason: str, expires: date) -> bool:
        for exception in self.exceptions:
            if exception["rule"] == rule_id and exception["manifest"] == manifest_id:
                self.update_exception(exception, reason, expires)
                return False
        self.exceptions.append(
            {"rule": rule_id, "manifest": manifest_id, "reason": reason, "expires": expires}
        )
        return True

    def update_exception(self, exception: dict[str, Any], reason: str, expires: date) -> None:
        exception.update(reason=reason, expires=expires)

    def active(self, exception: dict[str, Any], today: date) -> bool:
        return today <= exception["expires"]

    def covering(self, manifest_id: str, rule_id: str, today: date) -> dict[str, Any] | None:
        for exception in self.exceptions:
            if self.covers(exception, manifest_id, rule_id) and self.active(exception, today):
                return exception
        return None

    def covers(self, exception: dict[str, Any], manifest_id: str, rule_id: str) -> bool:
        return exception["manifest"] == manifest_id and exception["rule"] == rule_id

    def check_on(self, today: date) -> list[list[str]]:
        rows = []
        for manifest_id, rule_id, pointer in self.violations():
            exception = self.covering(manifest_id, rule_id, today)
            if exception is None:
                rows.append([manifest_id, rule_id, pointer, "violation", ""])
            else:
                rows.append([manifest_id, rule_id, pointer, "excepted", exception["reason"]])
        return rows + self.expired_rows(today)

    def expired_rows(self, today: date) -> list[list[str]]:
        expired = [e for e in self.exceptions if not self.active(e, today)]
        return [
            [e["manifest"], e["rule"], "", "expired", e["expires"].isoformat()]
            for e in self.order_expired(expired)
        ]

    def order_expired(self, expired: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(expired, key=lambda e: (e["manifest"], e["rule"]))

    # --- level 4
    def configure(self, rule_id: str, severity: str, mode: str, fix: str) -> bool:
        for rule in self.rules:
            if rule["id"] == rule_id:
                rule.update(severity=severity, mode=mode, fix=fix)
                return True
        return False

    def findings(self, today: date) -> list[list[str]]:
        rows = []
        for manifest_id, rule_id, pointer in self.violations():
            if self.covering(manifest_id, rule_id, today) is None:
                rule = next(r for r in self.rules if r["id"] == rule_id)
                fix = self.fix(rule, self.manifests[manifest_id], pointer)
                rows.append([manifest_id, rule_id, pointer, rule["severity"], rule["mode"], *fix])
        return [row for severity in self.severity_order() for row in rows if row[3] == severity]

    def severity_order(self) -> Sequence[str]:
        return SEVERITIES

    def fix(self, rule: dict[str, Any], flat: Flat, pointer: str) -> list[str]:
        if not rule["fix"] or not self.fixable(rule):
            return ["", ""]
        if rule["check"] == "tags":
            return ["replace", f"{self.repository(flat[pointer][1])}:{rule['fix']}"]
        if pointer in flat:
            return ["replace", rule["fix"]]
        if self.can_add(flat, pointer.rsplit("/", 1)[0]):
            return ["add", rule["fix"]]
        return ["", ""]

    def fixable(self, rule: dict[str, Any]) -> bool:
        return rule["check"] != "ports"

    def can_add(self, flat: Flat, parent: str) -> bool:
        return parent == "" or flat.get(parent, ("",))[0] == "object"

    def repository(self, image: str) -> str:
        tag = self.tag(image)
        return image if tag is None else image[: -len(tag) - 1]

    def decide(self, today: date) -> list[list[str]]:
        found = self.findings(today)
        rows = []
        for manifest_id in sorted(self.manifests):
            deny = sum(1 for row in found if row[0] == manifest_id and row[4] == "deny")
            warn = sum(1 for row in found if row[0] == manifest_id and row[4] == "warn")
            rows.append([manifest_id, self.verdict(deny, warn), str(deny), str(warn)])
        return self.decision_rows(rows)

    def verdict(self, deny: int, warn: int) -> str:
        return "reject" if deny else "admit"

    def decision_rows(self, rows: list[list[str]]) -> list[list[str]]:
        return rows


# --- level 1 mistakes
class NullIsPresent(Model):
    """Counts a null as a value that is there."""

    def missing(self, value: tuple[str, str] | None) -> bool:
        return value is None or value == ("string", "")


class EmptyTextIsPresent(Model):
    """Counts an empty text as a value that is there."""

    def missing(self, value: tuple[str, str] | None) -> bool:
        return value is None or value[0] == "null"


class FalsyValuesAreMissing(Model):
    """Counts "0", false, 0 and empty objects and lists as missing."""

    def missing(self, value: tuple[str, str] | None) -> bool:
        if value is not None and (value[1] in ("0", "false") or value[0] in ("object", "array")):
            return True
        return super().missing(value)


class KindIgnored(Model):
    """Applies every rule to every kind of manifest."""

    def applies(self, rule: dict[str, Any], flat: Flat) -> bool:
        return True


class RegistryPortIsATag(Model):
    """Takes everything after the last colon as the tag, even across a slash."""

    def tag(self, image: str) -> str | None:
        return image.rsplit(":", 1)[1] if ":" in image else None


class DigestNotTrusted(Model):
    """Drops the digest and checks the tag that is left."""

    def pinned(self, image: str) -> bool:
        return False

    def tag(self, image: str) -> str | None:
        return super().tag(image.split("@", 1)[0])


class TagsIgnoreCase(Model):
    """Compares tags without regard to case."""

    def listed(self, tag: str, tags: list[str]) -> bool:
        return tag.lower() in {t.lower() for t in tags}


class TagsMatchByPrefix(Model):
    """Forbids every tag that starts with a forbidden one."""

    def listed(self, tag: str, tags: list[str]) -> bool:
        return any(tag.startswith(t) for t in tags)


class NoTagIsFine(Model):
    """Lets an image without a tag pass."""

    def moving(self, value: tuple[str, str] | None, tags: list[str]) -> bool:
        if value is not None and value[0] == "string" and self.tag(value[1]) is None:
            return False
        return super().moving(value, tags)


class MissingImageIsMoving(Model):
    """Reports an image field that is missing or not a text."""

    def non_text_image(self, value: tuple[str, str] | None) -> bool:
        return True


class ManifestsInInsertionOrder(Model):
    """Reports manifests in the order they were added."""

    def manifest_order(self) -> list[str]:
        return list(self.manifests)


class ManifestsIgnoringCase(Model):
    """Sorts manifest ids without regard to case."""

    def manifest_order(self) -> list[str]:
        return sorted(self.manifests, key=str.lower)


class RulesSortedById(Model):
    """Reports rules sorted by id instead of in the order they were added."""

    def rule_order(self) -> list[dict[str, Any]]:
        return sorted(self.rules, key=lambda rule: rule["id"])


class RedefinedRuleMovesToTheEnd(Model):
    """Moves a redefined rule after the others."""

    def redefine(self, rule: dict[str, Any], definition: dict[str, Any]) -> None:
        super().redefine(rule, definition)
        self.rules.remove(rule)
        self.rules.append(rule)


class AddManifestAlwaysTrue(Model):
    """Reports every manifest as new."""

    def add_manifest(self, rows: list[list[str]]) -> bool:
        super().add_manifest(rows)
        return True


class ManifestsKnownByName(Model):
    """Keys manifests by name alone, so a service replaces a workload of the same name."""

    def add_manifest(self, rows: list[list[str]]) -> bool:
        flat = {pointer: (kind, text) for pointer, kind, text in rows}
        known = [m for m in self.manifests if m.split("/", 1)[1] == flat["/name"][1]]
        for old in known:
            del self.manifests[old]
        self.manifests[self.identity(flat)] = flat
        return not known


# --- level 2 mistakes
class ItemsSortedAsText(Model):
    """Sorts the pointers a pattern expands to as texts, so /containers/10 comes before /2."""

    def order_pointers(self, pointers: list[str]) -> list[str]:
        return sorted(pointers)


class WildcardWalksObjects(Model):
    """Lets a * walk the members of an object too."""

    def no_list(self, flat: Flat, prefix: str) -> list[str]:
        if flat.get(prefix, ("",))[0] == "object":
            return [p for p in flat if re.fullmatch(re.escape(prefix) + r"/[^/]+", p)]
        return []


class MissingListHasAFirstItem(Model):
    """Reads a * on a missing list as index 0, so the rest of the pattern is reported missing."""

    def no_list(self, flat: Flat, prefix: str) -> list[str]:
        return [f"{prefix}/0"] if prefix not in flat else []


class OnlyExistingFieldsChecked(Model):
    """Skips a pointer whose value is not there instead of reporting it missing."""

    def failing(self, rule: dict[str, Any], flat: Flat) -> list[str]:
        found = super().failing(rule, flat)
        if rule["check"] == "field" and "*" in rule["pointer"]:
            return [p for p in found if p in flat]
        return found


class SelectorMatchesAnyPair(Model):
    """Picks a workload that shares any one label with the selector."""

    def picked(self, selector: dict[str, tuple[str, str]], manifest: Flat) -> bool:
        if not self.selectable(manifest):
            return False
        return any(manifest.get(f"/labels/{k}") == v for k, v in selector.items())


class LabelsIgnoreCase(Model):
    """Compares label values without regard to case."""

    def label_matches(self, label: tuple[str, str] | None, wanted: tuple[str, str]) -> bool:
        return label is not None and label[1].lower() == wanted[1].lower()


class AnyWorkloadServes(Model):
    """Accepts a target that one selected workload has."""

    def served(self, target: str, picked: list[Flat]) -> bool:
        return any(target in self.port_names(workload) for workload in picked)


class FirstContainerOnly(Model):
    """Looks for port names in the first container only."""

    def port_names(self, workload: Flat) -> set[str]:
        return {
            workload[p][1]
            for p in self.expand(workload, "/containers/0/ports/*/name")
            if workload.get(p, ("",))[0] == "string"
        }


class EmptySelectorPicksAll(Model):
    """Lets an empty selector pick every workload."""

    def picked(self, selector: dict[str, tuple[str, str]], manifest: Flat) -> bool:
        if not selector:
            return self.selectable(manifest)
        return super().picked(selector, manifest)

    def selector_usable(self, service: Flat, selector: dict[str, tuple[str, str]]) -> bool:
        return True


class SelectorPicksServices(Model):
    """Lets a selector pick services as well as workloads."""

    def selectable(self, manifest: Flat) -> bool:
        return True


class PortWithoutTargetFails(Model):
    """Reports a port that names no target."""

    def unnamed_port_fails(self) -> bool:
        return True


class PortRuleOnEveryKind(Model):
    """Runs the port rule on workloads too."""

    def applies(self, rule: dict[str, Any], flat: Flat) -> bool:
        return rule["check"] == "ports" or super().applies(rule, flat)


# --- level 3 mistakes
class ExpiryDayExcluded(Model):
    """Ends an exception the day before its expiry date."""

    def active(self, exception: dict[str, Any], today: date) -> bool:
        return today < exception["expires"]


class ExpiredNotReported(Model):
    """Leaves expired exceptions out of the report."""

    def expired_rows(self, today: date) -> list[list[str]]:
        return []


class ExpiredOnlyWhenTheyMatch(Model):
    """Reports an expired exception only while its rule still fails in its manifest."""

    def expired_rows(self, today: date) -> list[list[str]]:
        failing = {(m, r) for m, r, _ in self.violations()}
        return [row for row in super().expired_rows(today) if (row[0], row[1]) in failing]


class ExpiredByDate(Model):
    """Sorts expired exceptions by their expiry date."""

    def order_expired(self, expired: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(expired, key=lambda e: (e["expires"], e["manifest"], e["rule"]))


class ExceptionCoversTheManifest(Model):
    """Lets an exception cover every rule of its manifest."""

    def covers(self, exception: dict[str, Any], manifest_id: str, rule_id: str) -> bool:
        return exception["manifest"] == manifest_id


class ExceptionCoversTheRule(Model):
    """Lets an exception cover its rule in every manifest."""

    def covers(self, exception: dict[str, Any], manifest_id: str, rule_id: str) -> bool:
        return exception["rule"] == rule_id


class FirstExceptionKept(Model):
    """Ignores a second allow for the same rule and manifest."""

    def update_exception(self, exception: dict[str, Any], reason: str, expires: date) -> None:
        pass


class CheckAppliesExceptions(Model):
    """Drops excepted violations from check, as of the expiry dates."""

    def check(self) -> list[list[str]]:
        return [
            [m, r, p]
            for m, r, p in self.violations()
            if not any(self.covers(e, m, r) for e in self.exceptions)
        ]


class ExceptionsDieWithTheRule(Model):
    """Drops a rule's exceptions when the rule is redefined."""

    def redefine(self, rule: dict[str, Any], definition: dict[str, Any]) -> None:
        super().redefine(rule, definition)
        self.exceptions = [e for e in self.exceptions if e["rule"] != rule["id"]]


class ExpiredStillExcepts(Model):
    """Keeps excepting violations after the exception expired."""

    def covering(self, manifest_id: str, rule_id: str, today: date) -> dict[str, Any] | None:
        for exception in self.exceptions:
            if self.covers(exception, manifest_id, rule_id):
                return exception
        return None


# --- level 4 mistakes
class LeastSevereFirst(Model):
    """Lists findings from low to critical."""

    def severity_order(self) -> Sequence[str]:
        return tuple(reversed(SEVERITIES))


class DefaultModeIsWarn(Model):
    """Gives an unconfigured rule the mode warn."""

    def define(self, rule_id: str, **definition: Any) -> bool:
        new = super().define(rule_id, **definition)
        if new:
            self.rules[-1]["mode"] = "warn"
        return new


class DefaultSeverityIsLow(Model):
    """Gives an unconfigured rule the severity low."""

    def define(self, rule_id: str, **definition: Any) -> bool:
        new = super().define(rule_id, **definition)
        if new:
            self.rules[-1]["severity"] = "low"
        return new


class CriticalAlwaysRejects(Model):
    """Rejects a manifest with a critical finding, even in warn mode."""

    def decide(self, today: date) -> list[list[str]]:
        critical = {row[0] for row in self.findings(today) if row[3] == "critical"}
        return [
            [m, "reject" if m in critical else verdict, deny, warn]
            for m, verdict, deny, warn in super().decide(today)
        ]


class RedefinitionResetsTheConfiguration(Model):
    """Puts a redefined rule back to medium, deny and no fix."""

    def redefine(self, rule: dict[str, Any], definition: dict[str, Any]) -> None:
        super().redefine(rule, definition)
        rule.update(severity="medium", mode="deny", fix="")


class FindingsKeepExcepted(Model):
    """Lists excepted violations among the findings."""

    def covering(self, manifest_id: str, rule_id: str, today: date) -> dict[str, Any] | None:
        if getattr(self, "in_findings", False):
            return None
        return super().covering(manifest_id, rule_id, today)

    def findings(self, today: date) -> list[list[str]]:
        self.in_findings = True
        try:
            return super().findings(today)
        finally:
            self.in_findings = False


class UnknownRuleConfigured(Model):
    """Reports configuring an unknown rule as done."""

    def configure(self, rule_id: str, severity: str, mode: str, fix: str) -> bool:
        super().configure(rule_id, severity, mode, fix)
        return True


class AddWithoutAParent(Model):
    """Suggests add even when the parent is missing or is a list."""

    def can_add(self, flat: Flat, parent: str) -> bool:
        return True


class AddForEveryMissingValue(Model):
    """Suggests add for a null or an empty text too."""

    def fix(self, rule: dict[str, Any], flat: Flat, pointer: str) -> list[str]:
        op, value = super().fix(rule, flat, pointer)
        return ["add" if op == "replace" and rule["check"] == "field" else op, value]


class TagFixLosesTheRegistryPort(Model):
    """Cuts the repository at its first colon."""

    def repository(self, image: str) -> str:
        return image.split(":", 1)[0]


class PortRuleGetsAFix(Model):
    """Suggests the port rule's fix as a replacement of its pointer."""

    def fixable(self, rule: dict[str, Any]) -> bool:
        return True

    def fix(self, rule: dict[str, Any], flat: Flat, pointer: str) -> list[str]:
        if rule["check"] == "ports" and rule["fix"]:
            return ["replace", rule["fix"]]
        return super().fix(rule, flat, pointer)


class DecisionsOnlyForFindings(Model):
    """Leaves manifests without findings out of the decision."""

    def decision_rows(self, rows: list[list[str]]) -> list[list[str]]:
        return [row for row in rows if row[2] != "0" or row[3] != "0"]


class WarningsReject(Model):
    """Rejects a manifest with any finding, warnings included."""

    def verdict(self, deny: int, warn: int) -> str:
        return "reject" if deny or warn else "admit"


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    results: list[Any] = [None]
    for op, arguments in zip(case["ops"][1:], case["args"][1:], strict=True):
        name = snake_case(op)
        values = list(arguments)
        if name in DATE_ARGUMENT:
            values[DATE_ARGUMENT[name]] = date.fromisoformat(values[DATE_ARGUMENT[name]])
        results.append(getattr(model, name)(*values))
    return results


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, StopIteration):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_reach_every_outcome_and_fix():
    outcomes, fixes = set(), set()
    for case in HIDDEN_CASES:
        for op, got in zip(case["ops"], case["expected"], strict=True):
            if op == "checkOn":
                outcomes.update(row[3] for row in got)
            if op == "findings":
                fixes.update(row[5] for row in got)
    assert outcomes == {"violation", "excepted", "expired"}
    assert fixes == {"add", "replace", ""}
