from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class Node:
    """One JSON value: an object (members), an array (items) or a scalar (kind and text)."""

    __slots__ = ("items", "kind", "members", "text")

    def __init__(self, kind: str, text: str = "") -> None:
        self.kind = kind
        self.text = text
        self.members: dict[str, Node] = {}
        self.items: list[Node] = []


@dataclass
class Rule:
    """A rule as data: what it checks, where, and how it is enforced."""

    check: str  # "field", "tags" or "ports"
    kind: str = "*"
    pointer: str = ""
    tags: list[str] = field(default_factory=list)
    severity: str = "medium"
    mode: str = "deny"
    fix: str = ""


@dataclass
class Allowance:
    reason: str
    expires: date


def decode(rows: list[list[str]]) -> Node:
    """Builds the tree from rows listed parent first; the root is an implicit object."""
    root = Node("object")
    for pointer, kind, text in rows:
        *parents, last = pointer.split("/")[1:]
        parent = root
        for segment in parents:
            parent = parent.members[segment] if parent.kind == "object" else parent.items[int(segment)]
        node = Node(kind, text)
        if parent.kind == "object":
            parent.members[last] = node
        else:
            parent.items.append(node)
    return root


def resolve(root: Node, pointer: str) -> Node | None:
    """The node at a JSON Pointer, or None when the path leaves the document."""
    node: Node | None = root
    for segment in pointer.split("/")[1:] if pointer else []:
        if node is None:
            return None
        if node.kind == "object":
            node = node.members.get(segment)
        elif node.kind == "array" and segment.isdigit() and int(segment) < len(node.items):
            node = node.items[int(segment)]
        else:
            return None
    return node


def expand(root: Node, pattern: str) -> list[str]:
    """Replaces each `*`, left to right, by every index of the list found there; a `*` where
    there is no list matches nothing."""
    pointers = [""]
    for segment in pattern.split("/")[1:]:
        if segment != "*":
            pointers = [f"{pointer}/{segment}" for pointer in pointers]
            continue
        expanded = []
        for pointer in pointers:
            node = resolve(root, pointer)
            if node is not None and node.kind == "array":
                expanded.extend(f"{pointer}/{index}" for index in range(len(node.items)))
        pointers = expanded
    return pointers


def tag_split(image: str) -> tuple[str, str | None]:
    """The repository and the tag of an image reference; the tag is None when there is none."""
    colon = image.rfind(":")
    if colon > image.rfind("/"):
        return image[:colon], image[colon + 1 :]
    return image, None


def text_of(root: Node, pointer: str) -> str | None:
    node = resolve(root, pointer)
    return node.text if node is not None and node.kind == "string" else None


class PolicyChecker:
    """Manifests are kept as trees by id, rules as data in the order they were added. A check
    expands each rule's pointer pattern over each manifest and tests the concrete pointers; a
    service's port rule looks up the workloads its selector picks. Exceptions, severities, modes
    and fixes are applied on top of the same list of violations."""

    def __init__(self) -> None:
        self._manifests: dict[str, Node] = {}
        self._rules: dict[str, Rule] = {}
        self._allowances: dict[tuple[str, str], Allowance] = {}

    # Level 1
    def add_manifest(self, rows: list[list[str]]) -> bool:
        root = decode(rows)
        manifest_id = f"{text_of(root, '/kind')}/{text_of(root, '/name')}"
        is_new = manifest_id not in self._manifests
        self._manifests[manifest_id] = root
        return is_new

    def require_field(self, rule_id: str, kind: str, pointer: str) -> bool:
        return self._define(rule_id, "field", kind, pointer, [])

    def forbid_tags(self, rule_id: str, kind: str, pointer: str, tags: list[str]) -> bool:
        return self._define(rule_id, "tags", kind, pointer, tags)

    def check(self) -> list[list[str]]:
        return [[m, r, p] for m, r, p in self._violations()]

    # Level 2
    def require_port_targets(self, rule_id: str) -> bool:
        return self._define(rule_id, "ports", "service", "", [])

    # Level 3
    def allow(self, rule_id: str, manifest_id: str, reason: str, expires: date) -> bool:
        is_new = (rule_id, manifest_id) not in self._allowances
        self._allowances[(rule_id, manifest_id)] = Allowance(reason, expires)
        return is_new

    def check_on(self, today: date) -> list[list[str]]:
        rows = []
        for manifest_id, rule_id, pointer in self._violations():
            exception = self._active(rule_id, manifest_id, today)
            if exception is None:
                rows.append([manifest_id, rule_id, pointer, "violation", ""])
            else:
                rows.append([manifest_id, rule_id, pointer, "excepted", exception.reason])
        expired = [
            (manifest_id, rule_id, exception)
            for (rule_id, manifest_id), exception in self._allowances.items()
            if today > exception.expires
        ]
        for manifest_id, rule_id, exception in sorted(expired, key=lambda e: (e[0], e[1])):
            rows.append([manifest_id, rule_id, "", "expired", exception.expires.isoformat()])
        return rows

    # Level 4
    def configure(self, rule_id: str, severity: str, mode: str, fix: str) -> bool:
        rule = self._rules.get(rule_id)
        if rule is None:
            return False
        rule.severity, rule.mode, rule.fix = severity, mode, fix
        return True

    def findings(self, today: date) -> list[list[str]]:
        rows = []
        for manifest_id, rule_id, pointer in self._violations():
            if self._active(rule_id, manifest_id, today) is not None:
                continue
            rule = self._rules[rule_id]
            op, value = self._fix(rule, self._manifests[manifest_id], pointer)
            rows.append([manifest_id, rule_id, pointer, rule.severity, rule.mode, op, value])
        return sorted(rows, key=lambda row: SEVERITY_RANK[row[3]])

    def decide(self, today: date) -> list[list[str]]:
        counts = {manifest_id: [0, 0] for manifest_id in self._manifests}
        for row in self.findings(today):
            counts[row[0]][0 if row[4] == "deny" else 1] += 1
        return [
            [manifest_id, "reject" if deny else "admit", str(deny), str(warn)]
            for manifest_id, (deny, warn) in sorted(counts.items())
        ]

    # Rules
    def _define(self, rule_id: str, check: str, kind: str, pointer: str, tags: list[str]) -> bool:
        rule = self._rules.get(rule_id)
        if rule is None:
            self._rules[rule_id] = Rule(check, kind, pointer, list(tags))
            return True
        rule.check, rule.kind, rule.pointer, rule.tags = check, kind, pointer, list(tags)
        return False

    def _violations(self) -> list[tuple[str, str, str]]:
        """Every violation in report order: manifest id, then rule order, then pointer order."""
        found = []
        for manifest_id in sorted(self._manifests):
            root = self._manifests[manifest_id]
            kind = text_of(root, "/kind")
            for rule_id, rule in self._rules.items():
                if rule.kind not in ("*", kind):
                    continue
                for pointer in self._broken(rule, root):
                    found.append((manifest_id, rule_id, pointer))
        return found

    def _broken(self, rule: Rule, root: Node) -> list[str]:
        if rule.check == "ports":
            return self._unserved_ports(root)
        broken = []
        for pointer in expand(root, rule.pointer):
            node = resolve(root, pointer)
            if rule.check == "field":
                if node is None or node.kind == "null" or (node.kind == "string" and node.text == ""):
                    broken.append(pointer)
            elif node is not None and node.kind == "string" and "@" not in node.text:
                tag = tag_split(node.text)[1]
                if tag is None or tag in rule.tags:
                    broken.append(pointer)
        return broken

    def _unserved_ports(self, service: Node) -> list[str]:
        selector = resolve(service, "/selector")
        if selector is None or selector.kind != "object" or not selector.members:
            return ["/selector"]
        selected = [
            root
            for root in self._manifests.values()
            if text_of(root, "/kind") == "workload" and self._selects(selector, root)
        ]
        if not selected:
            return ["/selector"]
        served = [
            {text_of(root, p) for p in expand(root, "/containers/*/ports/*/name")} for root in selected
        ]
        broken = []
        for pointer in expand(service, "/ports/*"):
            target = text_of(service, f"{pointer}/target")
            if target is not None and any(target not in names for names in served):
                broken.append(f"{pointer}/target")
        return broken

    @staticmethod
    def _selects(selector: Node, workload: Node) -> bool:
        return all(
            value.kind == "string" and text_of(workload, f"/labels/{key}") == value.text
            for key, value in selector.members.items()
        )

    def _active(self, rule_id: str, manifest_id: str, today: date) -> Allowance | None:
        exception = self._allowances.get((rule_id, manifest_id))
        return exception if exception is not None and today <= exception.expires else None

    @staticmethod
    def _fix(rule: Rule, root: Node, pointer: str) -> tuple[str, str]:
        if rule.fix == "" or rule.check == "ports":
            return "", ""
        node = resolve(root, pointer)
        if rule.check == "tags":
            return "replace", f"{tag_split(node.text)[0]}:{rule.fix}"
        if node is not None:
            return "replace", rule.fix
        parent = resolve(root, pointer[: pointer.rfind("/")])
        if parent is not None and parent.kind == "object":
            return "add", rule.fix
        return "", ""
