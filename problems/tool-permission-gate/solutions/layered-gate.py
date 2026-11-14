import re
from dataclasses import dataclass

ALLOW, DENY, ASK = "allow", "deny", "ask"
STRICTNESS = {ALLOW: 0, ASK: 1, DENY: 2}
MAX_LINK_HOPS = 40
USER = "user"
PATTERN = re.compile(r"[a-z0-9_]+\*?|\*")
REQUEST_ID = re.compile(r"[1-9][0-9]*")
PORT = re.compile(r"[0-9]*")
HOST_CHARS = re.compile(r"[a-z0-9.-]+")
URL = re.compile(r"(?i)(https?)://([^/?#]*)")
ANSWERS = {
    "yes": (ALLOW, None),
    "no": (DENY, None),
    "yes-tool": (ALLOW, "tool"),
    "no-tool": (DENY, "tool"),
    "yes-exact": (ALLOW, "exact"),
    "no-exact": (DENY, "exact"),
}


@dataclass(slots=True)
class _Request:
    tool: str
    args: list[list[str]]
    status: str = "pending"


@dataclass(slots=True)
class _Verdict:
    decision: str
    reason: str
    asks: bool = False


def _matches(pattern: str, tool: str) -> bool:
    if pattern.endswith("*"):
        return tool.startswith(pattern[:-1])
    return pattern == tool


def _specificity(pattern: str) -> tuple[int, int]:
    """Exact names beat wildcards; a longer prefix beats a shorter one."""
    if pattern.endswith("*"):
        return (0, len(pattern) - 1)
    return (1, len(pattern))


def _host_of(value: str) -> str | None:
    """The lower-cased host of an http or https URL, or None when it cannot be trusted."""
    if any(ord(ch) <= 32 or ord(ch) == 127 or ch == "\\" for ch in value):
        return None
    found = URL.match(value)
    if found is None or found.group(2).count("@") > 1:
        return None
    host_port = found.group(2).rsplit("@", 1)[-1]
    host, _, port = host_port.partition(":")
    if not PORT.fullmatch(port):
        return None
    host = host.lower().removesuffix(".")
    return host if HOST_CHARS.fullmatch(host) else None


def _host_allowed(host: str, allowed: list[str]) -> bool:
    for entry in allowed:
        if entry.startswith("*."):
            if host.endswith(entry[1:]) and len(host) > len(entry) - 1:
                return True
        elif host == entry:
            return True
    return False


class PermissionGate:
    def __init__(self) -> None:
        self._rules: set[tuple[str, str]] = set()
        self._scopes: dict[str, dict[str, tuple[str, list[str]]]] = {}
        self._aliases: dict[str, str] = {}
        self._read_only: set[str] = set()
        self._risks: set[tuple[str, str, str]] = set()
        self._remembered_exact: dict[tuple[str, tuple[tuple[str, str], ...]], str] = {}
        self._remembered_tool: dict[str, str] = {}
        self._requests: list[_Request] = []
        self._audit: list[list[str]] = []

    # Level 1
    def add_rule(self, effect: str, pattern: str) -> bool:
        if (effect, pattern) in self._rules:
            return False
        self._rules.add((effect, pattern))
        return True

    def remove_rule(self, effect: str, pattern: str) -> bool:
        if (effect, pattern) not in self._rules:
            return False
        self._rules.remove((effect, pattern))
        return True

    def decide(self, tool: str) -> str:
        rule = self._best_rule(tool)
        return rule[0] if rule else ASK

    # Level 2
    def set_scope(self, tool: str, param: str, kind: str, allowed: list[str]) -> None:
        self._scopes.setdefault(tool, {})[param] = (kind, list(allowed))

    def add_alias(self, link: str, target: str) -> None:
        self._aliases[link] = target

    def check(self, tool: str, args: list[list[str]]) -> str:
        verdict = self._judge(tool, args)
        request = ""
        if verdict.decision == ASK:
            self._requests.append(_Request(tool, [list(row) for row in args]))
            request = str(len(self._requests))
        self._log("check", tool, _render(args), verdict.decision, verdict.reason, request)
        return verdict.decision

    # Level 3
    def mark_read_only(self, tool: str) -> bool:
        if tool in self._read_only:
            return False
        self._read_only.add(tool)
        return True

    def add_risk(self, tool: str, param: str, text: str) -> bool:
        if (tool, param, text) in self._risks:
            return False
        self._risks.add((tool, param, text))
        return True

    def remember(self, tool: str, args: list[list[str]], decision: str, scope: str) -> bool:
        if not self._judge(tool, args, use_memory=False).asks:
            return False
        if scope == "tool":
            self._remembered_tool[tool] = decision
        else:
            self._remembered_exact[(tool, _key(args))] = decision
        return True

    def end_session(self) -> None:
        self._remembered_exact.clear()
        self._remembered_tool.clear()

    # Level 4
    def receive(self, channel: str, text: str) -> str:
        outcome, reason, request = self._interpret(channel, text)
        self._log("receive", channel, text, outcome, reason, request)
        return outcome

    def status(self, request: int) -> str:
        if not 1 <= request <= len(self._requests):
            return "unknown"
        return self._requests[request - 1].status

    def audit_log(self) -> list[list[str]]:
        return self._audit

    def _best_rule(self, tool: str) -> tuple[str, str] | None:
        matching = [rule for rule in self._rules if _matches(rule[1], tool)]
        if not matching:
            return None
        return max(matching, key=lambda rule: (*_specificity(rule[1]), STRICTNESS[rule[0]]))

    def _judge(self, tool: str, args: list[list[str]], use_memory: bool = True) -> _Verdict:
        """The decision for a call and the reason; `asks` says that only the user can settle it."""
        violated = self._scope_violation(tool, args)
        if violated:
            return _Verdict(DENY, f"scope:{violated}")
        rule = self._best_rule(tool)
        if rule and rule[0] == DENY:
            return _Verdict(DENY, f"rule:{DENY}:{rule[1]}")
        risk = self._risk_param(tool, args)
        if risk:
            base = _Verdict(ASK, f"risk:{risk}", asks=True)
        elif rule and rule[0] == ALLOW:
            return _Verdict(ALLOW, f"rule:{ALLOW}:{rule[1]}")
        elif rule:
            base = _Verdict(ASK, f"rule:{ASK}:{rule[1]}", asks=True)
        elif tool in self._read_only:
            return _Verdict(ALLOW, "read-only")
        else:
            base = _Verdict(ASK, "default", asks=True)
        if not use_memory:
            return base
        remembered = self._remembered_exact.get((tool, _key(args)))
        if remembered:
            return _Verdict(remembered, "remembered:exact")
        remembered = self._remembered_tool.get(tool)
        if remembered and (remembered == DENY or not risk):
            return _Verdict(remembered, "remembered:tool")
        return base

    def _risk_param(self, tool: str, args: list[list[str]]) -> str:
        values = dict(args)
        for risk_tool, param, text in sorted(self._risks):
            if risk_tool == tool and text in values.get(param, ""):
                return param
        return ""

    def _scope_violation(self, tool: str, args: list[list[str]]) -> str:
        values = dict(args)
        for param, (kind, allowed) in sorted(self._scopes.get(tool, {}).items()):
            value = values.get(param)
            if value is None:
                return param
            if kind == "path":
                inside = self._path_under(value, allowed)
            else:
                host = _host_of(value)
                inside = host is not None and _host_allowed(host, allowed)
            if not inside:
                return param
        return ""

    def _resolve(self, path: str) -> list[str] | None:
        """The components of an absolute path with `.`, `..` and aliases resolved, as a file
        system would: an alias is replaced by its target as soon as it is reached, so a `..` that
        follows it applies to the target."""
        if not path.startswith("/"):
            return None
        pending = path.split("/")
        resolved: list[str] = []
        hops = 0
        while pending:
            part = pending.pop(0)
            if part in ("", "."):
                continue
            if part == "..":
                if resolved:
                    resolved.pop()
                continue
            resolved.append(part)
            target = self._aliases.get("/" + "/".join(resolved))
            if target is not None:
                hops += 1
                if hops > MAX_LINK_HOPS:
                    return None
                pending = target.split("/") + pending
                resolved = []
        return resolved

    def _path_under(self, value: str, roots: list[str]) -> bool:
        resolved = self._resolve(value)
        if resolved is None:
            return False
        for root in roots:
            base = self._resolve(root)
            if base is not None and resolved[: len(base)] == base:
                return True
        return False

    def _interpret(self, channel: str, text: str) -> tuple[str, str, str]:
        if channel != USER:
            return "ignored", "untrusted-channel", ""
        words = text.split(" ")
        if len(words) != 2 or not words[1]:
            return "ignored", "not-a-directive", ""
        verb, argument = words
        if verb in STRICTNESS and PATTERN.fullmatch(argument):
            changed = self.add_rule(verb, argument)
            return ("applied", "rule-added", "") if changed else ("ignored", "no-change", "")
        if verb in ANSWERS and REQUEST_ID.fullmatch(argument):
            return self._answer(verb, int(argument))
        return "ignored", "not-a-directive", ""

    def _answer(self, verb: str, request_id: int) -> tuple[str, str, str]:
        if self.status(request_id) != "pending":
            return "ignored", "not-pending", str(request_id)
        decision, scope = ANSWERS[verb]
        request = self._requests[request_id - 1]
        request.status = decision
        if scope is None:
            return "applied", "answered", str(request_id)
        remembered = self.remember(request.tool, request.args, decision, scope)
        reason = f"answered:{scope}" if remembered else "answered"
        return "applied", reason, str(request_id)

    def _log(self, kind: str, subject: str, detail: str, outcome: str, reason: str, request: str):
        row = [str(len(self._audit) + 1), kind, subject, detail, outcome, reason, request]
        self._audit.append(row)


def _key(args: list[list[str]]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((row[0], row[1]) for row in args))


def _render(args: list[list[str]]) -> str:
    return ";".join(f"{name}={value}" for name, value in _key(args))
