"""tool-permission-gate promises that its hidden cases catch the classic mistakes of a gate between
a model and its tools: first match instead of most specific, a wildcard that outranks an exact name,
a path compared as text instead of resolved, an alias that does not change where `..` climbs, a
host read from the wrong part of a URL, a scope that gives way to a rule, a read-only mark or a
memory that overrides what it should not, a tool-wide answer that covers a risky call, and a
channel check that trusts text. These tests replay every case against a model of the gate written
from the statement, which must give every expected output, and against that model with one
mistake planted at a time, which some hidden case must fail. A mistake that crashes fails its case,
as a thrown exception does in the grader."""

import copy
import json
import re
from collections.abc import Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0324-tool-permission-gate"
CASES: Sequence[dict[str, Any]] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))[
    "cases"
]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]

STRICT = {"allow": 0, "ask": 1, "deny": 2}
ANSWERS = {
    "yes": ("allow", None),
    "no": ("deny", None),
    "yes-tool": ("allow", "tool"),
    "no-tool": ("deny", "tool"),
    "yes-exact": ("allow", "exact"),
    "no-exact": ("deny", "exact"),
}
HOST_LETTERS = "abcdefghijklmnopqrstuvwxyz0123456789.-"
Verdict = tuple[str, str, bool]


class Model:
    """The gate as the statement words it: a few facts about a call, and a fixed order of
    questions over them. Each mistake below overrides one hook."""

    def __init__(self) -> None:
        self.rules: list[tuple[str, str]] = []
        self.scopes: dict[str, dict[str, tuple[str, list[str]]]] = {}
        self.aliases: dict[str, str] = {}
        self.read_only: list[str] = []
        self.risks: list[tuple[str, str, str]] = []
        self.exact_memory: dict[Any, str] = {}
        self.tool_memory: dict[str, str] = {}
        self.questions: list[dict[str, Any]] = []
        self.log: list[list[str]] = []

    # --- level 1
    def matches(self, pattern: str, tool: str) -> bool:
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return tool.startswith(pattern[:-1])
        return pattern == tool

    def rank(self, rule: tuple[str, str]) -> tuple[int, ...]:
        effect, pattern = rule
        return (int(not pattern.endswith("*")), len(pattern.rstrip("*")), STRICT[effect])

    def best_rule(self, tool: str) -> tuple[str, str] | None:
        found = [rule for rule in self.rules if self.matches(rule[1], tool)]
        return max(found, key=self.rank) if found else None

    def add_rule(self, effect: str, pattern: str) -> bool:
        if (effect, pattern) in self.rules:
            return False
        self.rules.append((effect, pattern))
        return True

    def remove_rule(self, effect: str, pattern: str) -> bool:
        if (effect, pattern) not in self.rules:
            return False
        self.rules.remove((effect, pattern))
        return True

    def default_effect(self) -> str:
        return "ask"

    def decide(self, tool: str) -> str:
        rule = self.best_rule(tool)
        return rule[0] if rule else self.default_effect()

    # --- level 2
    def set_scope(self, tool: str, param: str, kind: str, allowed: list[str]) -> None:
        self.scopes.setdefault(tool, {})[param] = (kind, list(allowed))

    def add_alias(self, link: str, target: str) -> None:
        self.aliases[link] = target

    def walk(self, pieces: list[str], names: list[str], budget: list[int]) -> bool:
        for index, piece in enumerate(pieces):
            if piece in ("", "."):
                continue
            if piece == "..":
                if names:
                    names.pop()
                continue
            names.append(piece)
            target = self.aliases.get("/" + "/".join(names))
            if target is not None:
                if budget[0] == 0:
                    return False
                budget[0] -= 1
                names.clear()
                return self.walk(target.split("/") + pieces[index + 1 :], names, budget)
        return True

    def resolve(self, path: str) -> list[str] | None:
        if not path.startswith("/"):
            return None
        names: list[str] = []
        return names if self.walk(path.split("/"), names, [40]) else None

    def under(self, resolved: list[str], base: list[str]) -> bool:
        return len(resolved) >= len(base) and resolved[: len(base)] == base

    def path_in_scope(self, value: str, roots: list[str]) -> bool:
        resolved = self.resolve(value)
        if resolved is None:
            return False
        for root in roots:
            base = self.resolve(root)
            if base is not None and self.under(resolved, base):
                return True
        return False

    def strip_userinfo(self, authority: str) -> str | None:
        if authority.count("@") > 1:
            return None
        return authority.split("@")[-1]

    def cut_authority(self, rest: str) -> str:
        cut = len(rest)
        for mark in "/?#":
            at = rest.find(mark)
            if at != -1:
                cut = min(cut, at)
        return rest[:cut]

    def scheme_rest(self, value: str) -> str | None:
        lowered = value.lower()
        for scheme in ("http://", "https://"):
            if lowered.startswith(scheme):
                return value[len(scheme) :]
        return None

    def has_forbidden_char(self, value: str) -> bool:
        return re.search(r"[\x00-\x20\x7f\\]", value) is not None

    def host_of(self, value: str) -> str | None:
        if self.has_forbidden_char(value):
            return None
        rest = self.scheme_rest(value)
        if rest is None:
            return None
        hostport = self.strip_userinfo(self.cut_authority(rest))
        if hostport is None:
            return None
        host, _, port = hostport.partition(":")
        if not all(ch in "0123456789" for ch in port):
            return None
        host = self.fold(host)
        if host.endswith("."):
            host = host[:-1]
        if not host or any(ch not in HOST_LETTERS for ch in host):
            return None
        return host

    def fold(self, host: str) -> str:
        return host.lower()

    def host_matches(self, host: str, entry: str) -> bool:
        if entry.startswith("*."):
            domain = entry[2:]
            return host.endswith("." + domain) and len(host) > len(domain) + 1
        return host == entry

    def host_in_scope(self, value: str, allowed: list[str]) -> bool:
        host = self.host_of(value)
        return host is not None and any(self.host_matches(host, entry) for entry in allowed)

    def value_in_scope(self, kind: str, value: str, allowed: list[str]) -> bool:
        if kind == "path":
            return self.path_in_scope(value, allowed)
        return self.host_in_scope(value, allowed)

    def out_of_scope_params(self, tool: str, args: list[list[str]]) -> list[str]:
        values = {row[0]: row[1] for row in args}
        bad = []
        for param, (kind, allowed) in self.scopes.get(tool, {}).items():
            if param not in values or not self.value_in_scope(kind, values[param], allowed):
                bad.append(param)
        return sorted(bad)

    # --- level 3
    def risky_params(self, tool: str, args: list[list[str]]) -> list[str]:
        values = {row[0]: row[1] for row in args}
        return sorted(
            param
            for risk_tool, param, text in self.risks
            if risk_tool == tool and param in values and self.contains(values[param], text)
        )

    def contains(self, value: str, text: str) -> bool:
        return text in value

    def exact_key(self, tool: str, args: list[list[str]]) -> Any:
        return (tool, tuple(sorted((name, value) for name, value in args)))

    def facts(self, tool: str, args: list[list[str]]) -> dict[str, Any]:
        bad = self.out_of_scope_params(tool, args)
        risky = self.risky_params(tool, args)
        return {
            "scope": bad[0] if bad else "",
            "rule": self.best_rule(tool),
            "risk": risky[0] if risky else "",
            "read_only": tool in self.read_only,
        }

    def base_verdict(self, facts: dict[str, Any]) -> Verdict:
        rule = facts["rule"]
        if facts["scope"]:
            return ("deny", "scope:" + facts["scope"], False)
        if rule and rule[0] == "deny":
            return ("deny", "rule:deny:" + rule[1], False)
        if facts["risk"]:
            return ("ask", "risk:" + facts["risk"], True)
        if rule and rule[0] == "allow":
            return ("allow", "rule:allow:" + rule[1], False)
        if rule:
            return ("ask", "rule:ask:" + rule[1], True)
        if facts["read_only"]:
            return ("allow", "read-only", False)
        return (self.default_effect(), "default", True)

    def tool_memory_applies(self, decision: str, risky: bool) -> bool:
        return decision == "deny" or not risky

    def memory_settles(self, base: Verdict) -> bool:
        return base[2]

    def memory_verdict(
        self, tool: str, args: list[list[str]], facts: dict[str, Any], base: Verdict
    ):
        if not self.memory_settles(base):
            return base
        exact = self.exact_memory.get(self.exact_key(tool, args))
        if exact is not None:
            return (exact, "remembered:exact", False)
        wide = self.tool_memory.get(tool)
        if wide is not None and self.tool_memory_applies(wide, bool(facts["risk"])):
            return (wide, "remembered:tool", False)
        return base

    def verdict(self, tool: str, args: list[list[str]], memory: bool = True) -> Verdict:
        facts = self.facts(tool, args)
        base = self.base_verdict(facts)
        return self.memory_verdict(tool, args, facts, base) if memory else base

    def check(self, tool: str, args: list[list[str]]) -> str:
        decision, reason, asks = self.verdict(tool, args)
        request = ""
        if self.opens_question(decision, asks):
            self.questions.append({"tool": tool, "args": args, "status": "pending"})
            request = str(len(self.questions))
        self.write("check", tool, self.detail(args), decision, reason, request)
        return decision

    def opens_question(self, decision: str, asks: bool) -> bool:
        return decision == "ask"

    def detail(self, args: list[list[str]]) -> str:
        return ";".join(f"{name}={value}" for name, value in sorted((a, b) for a, b in args))

    def mark_read_only(self, tool: str) -> bool:
        if tool in self.read_only:
            return False
        self.read_only.append(tool)
        return True

    def add_risk(self, tool: str, param: str, text: str) -> bool:
        if (tool, param, text) in self.risks:
            return False
        self.risks.append((tool, param, text))
        return True

    def can_remember(self, tool: str, args: list[list[str]]) -> bool:
        return self.verdict(tool, args, memory=False)[2]

    def remember(self, tool: str, args: list[list[str]], decision: str, scope: str) -> bool:
        if not self.can_remember(tool, args):
            return False
        if scope == "tool":
            self.tool_memory[tool] = decision
        else:
            self.exact_memory[self.exact_key(tool, args)] = decision
        return True

    def end_session(self) -> None:
        self.exact_memory.clear()
        self.tool_memory.clear()

    # --- level 4
    def trusted(self, channel: str) -> bool:
        return channel == "user"

    def write(self, kind: str, subject: str, detail: str, outcome: str, reason: str, request: str):
        self.log.append([str(len(self.log) + 1), kind, subject, detail, outcome, reason, request])

    def valid_pattern(self, word: str) -> bool:
        return re.fullmatch(r"[a-z0-9_]+\*?|\*", word) is not None

    def valid_number(self, word: str) -> bool:
        return re.fullmatch(r"[1-9][0-9]*", word) is not None

    def split_directive(self, text: str) -> list[str]:
        return text.split(" ")

    def pending(self, number: int) -> bool:
        return (
            1 <= number <= len(self.questions) and self.questions[number - 1]["status"] == "pending"
        )

    def apply_rule_word(self, verb: str, word: str) -> tuple[str, str]:
        if self.add_rule(verb, word):
            return "applied", "rule-added"
        return "ignored", "no-change"

    def answer_reason(self, remembered: bool, scope: str | None) -> str:
        return f"answered:{scope}" if remembered and scope else "answered"

    def answer(self, verb: str, number: int) -> tuple[str, str, str]:
        if not self.pending(number):
            return "ignored", "not-pending", str(number)
        decision, scope = ANSWERS[verb]
        question = self.questions[number - 1]
        question["status"] = decision
        remembered = False
        if scope is not None:
            remembered = self.remember(question["tool"], question["args"], decision, scope)
        return "applied", self.answer_reason(remembered, scope), str(number)

    def interpret(self, channel: str, text: str) -> tuple[str, str, str]:
        if not self.trusted(channel):
            return "ignored", "untrusted-channel", ""
        words = self.split_directive(text)
        if len(words) != 2:
            return "ignored", "not-a-directive", ""
        verb, word = words
        if verb in STRICT and self.valid_pattern(word):
            outcome, reason = self.apply_rule_word(verb, word)
            return outcome, reason, ""
        if verb in ANSWERS and self.valid_number(word):
            return self.answer(verb, int(word))
        return "ignored", "not-a-directive", ""

    def receive(self, channel: str, text: str) -> str:
        outcome, reason, request = self.interpret(channel, text)
        self.write("receive", channel, text, outcome, reason, request)
        return outcome

    def status(self, request: int) -> str:
        if 1 <= request <= len(self.questions):
            return self.questions[request - 1]["status"]
        return "unknown"

    def audit_log(self) -> list[list[str]]:
        return self.log


# ---------------------------------------------------------------- level 1
class FirstMatchWins(Model):
    """Uses the first rule that matches, in the order the rules were added."""

    def best_rule(self, tool):
        return next((rule for rule in self.rules if self.matches(rule[1], tool)), None)


class LastMatchWins(Model):
    """Uses the last rule that matches."""

    def best_rule(self, tool):
        found = [rule for rule in self.rules if self.matches(rule[1], tool)]
        return found[-1] if found else None


class LongestPatternWins(Model):
    """Ranks by the length of the pattern, so a long prefix beats an exact name."""

    def rank(self, rule):
        return (len(rule[1]), STRICT[rule[0]])


class WildcardBeatsExactOnEqualPrefix(Model):
    """Lets `read_file*` beat `read_file` for the tool `read_file`."""

    def rank(self, rule):
        effect, pattern = rule
        return (len(pattern.rstrip("*")), int(pattern.endswith("*")), STRICT[effect])


class AllowBeatsDenyOnATie(Model):
    """On the same pattern, the more permissive effect wins."""

    def rank(self, rule):
        effect, pattern = rule
        return (int(not pattern.endswith("*")), len(pattern.rstrip("*")), -STRICT[effect])


class AskBeatsDenyOnATie(Model):
    """On the same pattern, ask is stricter than deny."""

    def rank(self, rule):
        effect, pattern = rule
        order = {"allow": 0, "deny": 1, "ask": 2}
        return (int(not pattern.endswith("*")), len(pattern.rstrip("*")), order[effect])


class PrefixMatchesAnywhere(Model):
    """Reads `read*` as 'contains read'."""

    def matches(self, pattern, tool):
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return pattern[:-1] in tool
        return pattern == tool


class PrefixNeedsOneMoreCharacter(Model):
    """Does not let `read_*` match `read_`."""

    def matches(self, pattern, tool):
        if pattern.endswith("*") and pattern != "*":
            return tool.startswith(pattern[:-1]) and len(tool) > len(pattern) - 1
        return super().matches(pattern, tool)


class DuplicateRulesAddedTwice(Model):
    """Reports true for a rule that is already there."""

    def add_rule(self, effect, pattern):
        super().add_rule(effect, pattern)
        return True


class RemoveDropsEveryEffect(Model):
    """Removes the pattern with all its effects."""

    def remove_rule(self, effect, pattern):
        found = [rule for rule in self.rules if rule[1] == pattern]
        self.rules = [rule for rule in self.rules if rule[1] != pattern]
        return bool(found)


class UnmatchedToolIsAllowed(Model):
    """Allows a tool that no rule names."""

    def default_effect(self):
        return "allow"


class UnmatchedToolIsDenied(Model):
    """Denies a tool that no rule names."""

    def default_effect(self):
        return "deny"


# ---------------------------------------------------------------- level 2
class PathsComparedAsText(Model):
    """Compares the text of the path with the text of the root."""

    def path_in_scope(self, value, roots):
        return any(value.startswith(root) for root in roots)


class PathsNormalizedButPrefixOfText(Model):
    """Resolves the path and then compares as text, so /work2 is inside /work."""

    def under(self, resolved, base):
        return "/".join(resolved).startswith("/".join(base))


class DotDotIgnored(Model):
    """Reads `..` as an ordinary name."""

    def walk(self, pieces, names, budget):
        return super().walk([piece if piece != ".." else "_up_" for piece in pieces], names, budget)


class DotDotAboveRootFails(Model):
    """Refuses a path that climbs above the root."""

    def walk(self, pieces, names, budget):
        depth = 0
        for piece in pieces:
            if piece == "..":
                depth -= 1
                if depth < 0:
                    return False
            elif piece not in ("", "."):
                depth += 1
        return super().walk(pieces, names, budget)


class DotDotBeforeAliasesAreSeen(Model):
    """Removes `..` lexically first and follows aliases afterwards."""

    def resolve(self, path):
        if not path.startswith("/"):
            return None
        kept: list[str] = []
        for piece in path.split("/"):
            if piece in ("", "."):
                continue
            if piece == "..":
                if kept:
                    kept.pop()
                continue
            kept.append(piece)
        return super().resolve("/" + "/".join(kept))


class AliasesIgnored(Model):
    """Never follows an alias."""

    def walk(self, pieces, names, budget):
        saved, self.aliases = self.aliases, {}
        try:
            return super().walk(pieces, names, budget)
        finally:
            self.aliases = saved


class AliasOnlyOnTheLastPiece(Model):
    """Follows an alias only when it is the last name of the path."""

    def walk(self, pieces, names, budget):
        names_only = [piece for piece in pieces if piece not in ("", ".", "..")]
        last = names_only[-1] if names_only else ""
        for index, piece in enumerate(pieces):
            if piece in ("", "."):
                continue
            if piece == "..":
                if names:
                    names.pop()
                continue
            names.append(piece)
            target = self.aliases.get("/" + "/".join(names))
            if target is not None and piece == last and index == len(pieces) - 1:
                names.clear()
                return super().walk(target.split("/"), names, budget)
        return True


class AliasReplacedAsText(Model):
    """Replaces an alias by its target as text before reading the path."""

    def resolve(self, path):
        for link, target in self.aliases.items():
            if path.startswith(link):
                path = target + path[len(link) :]
        return super().resolve(path)


class AliasLoopsFailOpen(Model):
    """Treats a path that never settles as inside."""

    def path_in_scope(self, value, roots):
        if self.resolve(value) is None and value.startswith("/"):
            return True
        return super().path_in_scope(value, roots)


class AliasRootsNotResolved(Model):
    """Uses the roots as written."""

    def path_in_scope(self, value, roots):
        resolved = self.resolve(value)
        if resolved is None:
            return False
        return any(self.under(resolved, [p for p in root.split("/") if p]) for root in roots)


class RelativePathsAreInside(Model):
    """Reads a relative path as relative to the root."""

    def path_in_scope(self, value, roots):
        if not value.startswith("/") and roots:
            return super().path_in_scope(roots[0] + "/" + value, roots)
        return super().path_in_scope(value, roots)


class MissingArgumentPasses(Model):
    """Skips a scope whose argument is absent."""

    def out_of_scope_params(self, tool, args):
        present = {name for name, _ in args}
        return [p for p in super().out_of_scope_params(tool, args) if p in present]


class OnlyTheFirstScopeIsChecked(Model):
    """Checks one scope of a tool."""

    def out_of_scope_params(self, tool, args):
        bad = super().out_of_scope_params(tool, args)
        first = next(iter(self.scopes.get(tool, {})), None)
        return [p for p in bad if p == first]


class AllowRuleBeatsTheScope(Model):
    """Lets an allow rule override a failed scope."""

    def base_verdict(self, facts):
        rule = facts["rule"]
        if facts["scope"] and rule and rule[0] == "allow":
            return ("allow", "rule:allow:" + rule[1], False)
        return super().base_verdict(facts)


class ScopeMakesAskIntoAllow(Model):
    """Lets an in-scope call skip the question."""

    def base_verdict(self, facts):
        verdict = super().base_verdict(facts)
        if self.scopes and verdict[0] == "ask" and not facts["scope"] and facts["rule"]:
            return ("allow", verdict[1], False)
        return verdict


class EmptyRootsAllowEverything(Model):
    """Reads an empty list of roots as no restriction."""

    def path_in_scope(self, value, roots):
        return not roots or super().path_in_scope(value, roots)


class HostIsAnywhereInTheUrl(Model):
    """Looks for the allowed name anywhere in the text."""

    def host_in_scope(self, value, allowed):
        return any(entry.lstrip("*.") in value for entry in allowed)


class UserNameTakenAsHost(Model):
    """Reads the text before the @ as the host."""

    def strip_userinfo(self, authority):
        return authority.split("@")[0]


class LastAtIgnoredForSeveral(Model):
    """Accepts an authority with several @ and uses the last."""

    def strip_userinfo(self, authority):
        return authority.split("@")[-1]


class AuthorityRunsToTheSlash(Model):
    """Cuts the authority at the first slash only, not at ? or #."""

    def cut_authority(self, rest):
        return rest.split("/")[0]


class PortStaysInTheHost(Model):
    """Leaves the port in the host."""

    def host_of(self, value):
        host = super().host_of(value)
        rest = self.scheme_rest(value)
        if host is None or rest is None:
            return host
        authority = self.cut_authority(rest).split("@")[-1].lower()
        return authority.rstrip(".")


class HostCaseSensitive(Model):
    """Compares the host as written."""

    def fold(self, host):
        return host


class TrailingDotRefused(Model):
    """Refuses a host with a final dot."""

    def host_of(self, value):
        host = super().host_of(value)
        rest = self.scheme_rest(value)
        if rest is not None and self.cut_authority(rest).split("@")[-1].split(":")[0].endswith("."):
            return None
        return host


class WildcardAllowsTheBareDomain(Model):
    """Lets `*.example.org` match `example.org`."""

    def host_matches(self, host, entry):
        if entry.startswith("*."):
            return host == entry[2:] or host.endswith(entry[1:])
        return host == entry


class WildcardWithoutTheDot(Model):
    """Lets `*.example.org` match `notexample.org`."""

    def host_matches(self, host, entry):
        if entry.startswith("*."):
            return host.endswith(entry[2:]) and host != entry[2:]
        return host == entry


class AnySchemeAccepted(Model):
    """Takes the host of ftp and other URLs."""

    def scheme_rest(self, value):
        found = re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://(.*)$", value)
        return found.group(1) if found else None


class BackslashAllowed(Model):
    """Does not refuse a backslash."""

    def has_forbidden_char(self, value):
        return re.search(r"[\x00-\x20\x7f]", value) is not None


class SpacesAllowed(Model):
    """Does not refuse a space."""

    def has_forbidden_char(self, value):
        return re.search(r"[\x00-\x1f\x7f\\]", value) is not None


class BadPortAccepted(Model):
    """Accepts any text as a port."""

    def host_of(self, value):
        fixed = re.sub(r"(://[^/?#:]*):[^/?#]*", r"\1", value)
        return super().host_of(fixed)


class ScopeReasonNotAlphabetical(Model):
    """Names the last violated argument in the order the scopes were set."""

    def out_of_scope_params(self, tool, args):
        values = {row[0]: row[1] for row in args}
        bad = []
        for param, (kind, allowed) in self.scopes.get(tool, {}).items():
            if param not in values or not self.value_in_scope(kind, values[param], allowed):
                bad.append(param)
        return bad


# ---------------------------------------------------------------- level 3
class ReadOnlyBeatsExplicitAsk(Model):
    """Allows a read-only tool even when a rule says ask."""

    def base_verdict(self, facts):
        rule = facts["rule"]
        if facts["read_only"] and rule and rule[0] == "ask" and not facts["scope"]:
            return ("allow", "read-only", False)
        return super().base_verdict(facts)


class ReadOnlyBeatsDeny(Model):
    """Allows a read-only tool even when a rule denies it."""

    def base_verdict(self, facts):
        rule = facts["rule"]
        if facts["read_only"] and rule and rule[0] == "deny" and not facts["scope"]:
            return ("allow", "read-only", False)
        return super().base_verdict(facts)


class ReadOnlyBeatsRisk(Model):
    """Allows a read-only tool even for a risky call."""

    def base_verdict(self, facts):
        if facts["read_only"] and facts["risk"] and not facts["scope"]:
            return ("allow", "read-only", False)
        return super().base_verdict(facts)


class ReadOnlyNeedsNoRuleButAsks(Model):
    """Does not auto-approve read-only tools."""

    def base_verdict(self, facts):
        return super().base_verdict({**facts, "read_only": False})


class RiskIgnoredUnderAnAllowRule(Model):
    """Lets an allow rule override a risk."""

    def base_verdict(self, facts):
        rule = facts["rule"]
        if facts["risk"] and rule and rule[0] == "allow":
            return super().base_verdict({**facts, "risk": ""})
        return super().base_verdict(facts)


class RiskBeatsDenyRule(Model):
    """Turns a deny rule into a question when the call is risky."""

    def base_verdict(self, facts):
        rule = facts["rule"]
        if facts["risk"] and rule and rule[0] == "deny" and not facts["scope"]:
            return ("ask", "risk:" + facts["risk"], True)
        return super().base_verdict(facts)


class RiskCaseInsensitive(Model):
    """Ignores the letter case when looking for the risky text."""

    def contains(self, value, text):
        return text.lower() in value.lower()


class RiskMatchesWholeWordsOnly(Model):
    """Looks for the risky text as a word."""

    def contains(self, value, text):
        return text in value.split(" ")


class RiskLooksInEveryArgument(Model):
    """Looks for the text in all the arguments, not the named one."""

    def risky_params(self, tool, args):
        hits = []
        for risk_tool, param, text in self.risks:
            if risk_tool == tool and any(text in value for _, value in args):
                hits.append(param)
        return sorted(hits)


class RiskReasonFirstDeclared(Model):
    """Names the first declared risk and not the first in alphabetical order."""

    def risky_params(self, tool, args):
        values = {row[0]: row[1] for row in args}
        return [
            param
            for risk_tool, param, text in self.risks
            if risk_tool == tool and text in values.get(param, "")
        ]


class ToolAnswerCoversRiskyCalls(Model):
    """Lets a remembered allow for a tool cover a risky call."""

    def tool_memory_applies(self, decision, risky):
        return True


class ToolDenyDoesNotCoverRiskyCalls(Model):
    """Lets a remembered deny for a tool give way to a risky call."""

    def tool_memory_applies(self, decision, risky):
        return not risky


class ToolMemoryBeatsExact(Model):
    """Looks at the tool memory before the exact one."""

    def memory_verdict(self, tool, args, facts, base):
        if base[2]:
            wide = self.tool_memory.get(tool)
            if wide is not None and self.tool_memory_applies(wide, bool(facts["risk"])):
                return (wide, "remembered:tool", False)
        return super().memory_verdict(tool, args, facts, base)


class MemorySettlesDeniedCalls(Model):
    """Lets a remembered allow turn a deny into allow."""

    def memory_settles(self, base):
        return True


class RememberStoresWhateverIsAsked(Model):
    """Stores an answer for any call and says true."""

    def can_remember(self, tool, args):
        return True


class RememberRefusesRiskyCalls(Model):
    """Refuses to remember an answer for a risky call."""

    def can_remember(self, tool, args):
        return super().can_remember(tool, args) and not self.risky_params(tool, args)


class ExactKeyKeepsTheOrder(Model):
    """Keys the exact memory by the arguments in the order given."""

    def exact_key(self, tool, args):
        return (tool, tuple((name, value) for name, value in args))


class ExactKeyIgnoresExtraArguments(Model):
    """Matches an exact answer when the call has at least its arguments."""

    def memory_verdict(self, tool, args, facts, base):
        if base[2]:
            have = {(n, v) for n, v in args}
            for key, decision in self.exact_memory.items():
                if key[0] == tool and set(key[1]) <= have:
                    return (decision, "remembered:exact", False)
        return super().memory_verdict(tool, args, facts, base)


class FirstAnswerStays(Model):
    """Keeps the first remembered answer."""

    def remember(self, tool, args, decision, scope):
        if not self.can_remember(tool, args):
            return False
        if scope == "tool":
            self.tool_memory.setdefault(tool, decision)
        else:
            self.exact_memory.setdefault(self.exact_key(tool, args), decision)
        return True


class EndSessionForgetsTheRules(Model):
    """Clears the rules, the marks and the risks with the memory."""

    def end_session(self):
        super().end_session()
        self.rules, self.read_only, self.risks = [], [], []


class EndSessionKeepsTheExactMemory(Model):
    """Clears the tool memory only."""

    def end_session(self):
        self.tool_memory.clear()


class MarkReadOnlyAlwaysTrue(Model):
    """Reports true for a tool that is already marked."""

    def mark_read_only(self, tool):
        super().mark_read_only(tool)
        return True


class AddRiskAlwaysTrue(Model):
    """Reports true for a risk that is already declared."""

    def add_risk(self, tool, param, text):
        super().add_risk(tool, param, text)
        return True


# ---------------------------------------------------------------- level 4
class ChannelCaseInsensitive(Model):
    """Trusts USER and User."""

    def trusted(self, channel):
        return channel.lower() == "user"


class ChannelTrimmed(Model):
    """Trusts `user ` with a space."""

    def trusted(self, channel):
        return channel.strip() == "user"


class ChannelPrefix(Model):
    """Trusts any channel that starts or ends with user."""

    def trusted(self, channel):
        return "user" in channel


class ToolChannelMayAnswer(Model):
    """Lets the tool channel answer questions but not add rules."""

    def interpret(self, channel, text):
        if channel in ("tool", "model") and text.split(" ")[0] in ANSWERS:
            return super().interpret("user", text)
        return super().interpret(channel, text)


class ToolChannelMayAddRules(Model):
    """Lets the tool channel add rules but not answer."""

    def interpret(self, channel, text):
        if channel == "tool" and text.split(" ")[0] in STRICT:
            return super().interpret("user", text)
        return super().interpret(channel, text)


class DirectiveTextIsTrimmed(Model):
    """Strips white space around a directive."""

    def split_directive(self, text):
        return text.strip().split(" ")


class DirectiveSplitsOnAnyWhiteSpace(Model):
    """Splits on runs of white space."""

    def split_directive(self, text):
        return text.split()


class DirectiveVerbIgnoresCase(Model):
    """Reads ALLOW like allow."""

    def split_directive(self, text):
        words = text.split(" ")
        return [words[0].lower(), *words[1:]]


class DirectiveMayHaveTrailingWords(Model):
    """Reads the first two words and ignores the rest."""

    def split_directive(self, text):
        return text.split(" ")[:2] if text.count(" ") >= 1 else [text]


class PatternNotValidated(Model):
    """Accepts any word as a pattern."""

    def valid_pattern(self, word):
        return bool(word)


class NumberAcceptsLeadingZeros(Model):
    """Reads 01 as 1."""

    def valid_number(self, word):
        return word.isdigit() and int(word) > 0


class AnswersAreRepeatable(Model):
    """Lets a question be answered again."""

    def pending(self, number):
        return 1 <= number <= len(self.questions)


class AnswerAlwaysSaysRemembered(Model):
    """Names the scope in the reason even when nothing was stored."""

    def answer_reason(self, remembered, scope):
        return f"answered:{scope}" if scope else "answered"


class QuestionForEveryCheck(Model):
    """Numbers every check, not only the asks."""

    def opens_question(self, decision, asks):
        return True


class RuleDirectiveAlwaysApplied(Model):
    """Says applied for a rule that was already there."""

    def apply_rule_word(self, verb, word):
        self.add_rule(verb, word)
        return "applied", "rule-added"


class LogSkipsIgnoredText(Model):
    """Writes no row for text that was ignored."""

    def write(self, kind, subject, detail, outcome, reason, request):
        if kind == "receive" and outcome == "ignored":
            return
        super().write(kind, subject, detail, outcome, reason, request)


class LogDetailKeepsTheOrderGiven(Model):
    """Writes the arguments in the order they were given."""

    def detail(self, args):
        return ";".join(f"{name}={value}" for name, value in args)


class LogRowsRestartAfterTheSession(Model):
    """Clears the log with the memory."""

    def end_session(self):
        super().end_session()
        self.log = []


class QuestionsRestartAfterTheSession(Model):
    """Forgets the questions with the memory."""

    def end_session(self):
        super().end_session()
        self.questions = []


class DecideWritesToTheLog(Model):
    """Writes a row for decide."""

    def decide(self, tool):
        result = super().decide(tool)
        self.write("check", tool, "", result, "decide", "")
        return result


class RememberWritesToTheLog(Model):
    """Writes a row for each call of remember."""

    def remember(self, tool, args, decision, scope):
        result = super().remember(tool, args, decision, scope)
        if result:
            self.write("remember", tool, "", decision, scope, "")
        return result


class StatusOfZeroIsPending(Model):
    """Reads question 0 as the first."""

    def status(self, request):
        return super().status(max(request, 1)) if request == 0 else super().status(request)


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: dict[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [
        None,
        *(copy.deepcopy(getattr(model, snake_case(op))(*arguments)) for op, arguments in calls),
    ]


def passes(model_type: type[Model], case: dict[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, AttributeError, RecursionError):
        return False


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_visible_and_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert any(case.get("visible") for case in at_level)
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_reach_every_decision_and_every_reason():
    decisions: set[str] = set()
    reasons: set[str] = set()
    for case in HIDDEN_CASES:
        for op, got in zip(case["ops"], case["expected"], strict=True):
            if op == "check":
                decisions.add(got)
            elif op == "auditLog":
                reasons.update(re.sub(r":.*", "", row[5]) for row in got)
    assert decisions == {"allow", "deny", "ask"}
    assert reasons >= {
        "scope",
        "rule",
        "risk",
        "read-only",
        "default",
        "remembered",
        "untrusted-channel",
        "not-a-directive",
        "rule-added",
        "no-change",
        "answered",
        "not-pending",
    }
