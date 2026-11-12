"""cert-chain-validator promises that its hidden cases catch the classic mistakes of certificate
validation: an exclusive end date, a wildcard that covers too much or sits in the wrong place, the
common name used as a hostname, links made by name or by signature alone, a search that loops,
does not backtrack or breaks ties by insertion order, checks run in another order than RFC 5280's,
the leaf or the trust anchor checked as if it were an intermediate, an off-by-one or misordered
path length, key usage misread, revocation ignored or applied to the anchor, and a verify that
stops too early or too late. These tests replay every case against a model of the validator
written from the statement, which must give every expected output, and against that model with
one mistake planted at a time, which some hidden case must fail. A mistake that crashes fails its
case, as a thrown exception does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0351-cert-chain-validator"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

LABEL = r"[a-z0-9\-]+"


class Model:
    """The validator as the statement words it: a regular expression per DNS name, chains found
    breadth-first one length at a time, and path length decided per certificate from the
    constraints above it. Each mistake below overrides one of these steps."""

    def __init__(self) -> None:
        self.certs: dict[str, dict[str, Any]] = {}
        self.good: set[tuple[str, str]] = set()
        self.anchors: list[str] = []
        self.revoked: list[str] = []

    # --- level 1
    def add_certificate(self, cert_id, subject, issuer, not_before, not_after, dns_names) -> bool:
        if cert_id in self.certs:
            return False
        self.certs[cert_id] = {
            "subject": subject,
            "issuer": issuer,
            "from": not_before,
            "to": not_after,
            "names": dns_names,
            "ca": False,
            "len": -1,
            "usage": [],
        }
        return True

    def name_regex(self, name: str) -> str | None:
        """The hostnames a DNS name covers, as a regular expression, or None if it is invalid."""
        labels = name.lower().split(".")
        if "*" not in name:
            return re.escape(name.lower())
        if labels[0] != "*" or name.count("*") != 1 or len(labels) < 3:
            return None
        return LABEL + re.escape("." + ".".join(labels[1:]))

    def matched_name(self, cert_id: str, hostname: str) -> str:
        for name in self.certs.get(cert_id, {}).get("names", []):
            pattern = self.name_regex(name)
            if pattern is not None and re.fullmatch(pattern, hostname.lower()):
                return self.shown(name)
        return ""

    def shown(self, name: str) -> str:
        return name

    def too_early(self, cert: dict[str, Any], now: int) -> bool:
        return now < cert["from"]

    def too_late(self, cert: dict[str, Any], now: int) -> bool:
        return now > cert["to"]

    def dates(self, cert: dict[str, Any], now: int) -> str | None:
        if self.too_early(cert, now):
            return "not-yet-valid"
        return "expired" if self.too_late(cert, now) else None

    def check_leaf(self, cert_id: str, hostname: str, now: int) -> str:
        if cert_id not in self.certs:
            return "unknown-certificate"
        reason = self.dates(self.certs[cert_id], now)
        if reason:
            return reason
        return "ok" if self.matched_name(cert_id, hostname) else "hostname-mismatch"

    # --- level 2
    def add_signature(self, signer_id: str, cert_id: str, valid: bool) -> None:
        self.good.discard((signer_id, cert_id))
        if valid:
            self.good.add((signer_id, cert_id))

    def add_trust_anchor(self, cert_id: str) -> bool:
        if cert_id not in self.certs or cert_id in self.anchors:
            return False
        self.anchors.append(cert_id)
        return True

    def is_anchor(self, cert_id: str) -> bool:
        return cert_id in self.anchors

    def links(self, cert_id: str) -> list[str]:
        issuer = self.certs[cert_id]["issuer"]
        return [
            s
            for s in self.certs
            if self.certs[s]["subject"] == issuer and (s, cert_id) in self.good
        ]

    def extend(self, chain: list[str], signer: str) -> bool:
        return signer not in chain

    def chains(self, leaf_id: str) -> list[list[str]]:
        if leaf_id not in self.certs:
            return []
        found: list[list[str]] = []
        frontier = [[leaf_id]]
        while frontier:
            done = [chain for chain in frontier if len(chain) > 1 and self.is_anchor(chain[-1])]
            found += self.order(done)
            growing = [chain for chain in frontier if not self.is_anchor(chain[-1])]
            frontier = [[*c, s] for c in growing for s in self.links(c[-1]) if self.extend(c, s)]
        return found

    def order(self, chains: list[list[str]]) -> list[list[str]]:
        return sorted(chains)

    def build_chain(self, leaf_id: str) -> list[str]:
        return next(iter(self.chains(leaf_id)), [])

    # --- level 3
    def set_constraints(self, cert_id, is_ca, path_len, key_usage) -> bool:
        if cert_id not in self.certs:
            return False
        self.certs[cert_id].update(ca=is_ca, len=path_len, usage=key_usage)
        return True

    def structure(self, path: list[str]) -> list[str] | None:
        if self.is_anchor(path[0]):
            return ["leaf-is-anchor", path[0]]
        for cert_id in path:
            if cert_id not in self.certs:
                return ["unknown-certificate", cert_id]
        for index, cert_id in enumerate(path):
            if cert_id in path[:index]:
                return ["repeated-certificate", cert_id]
        return None if self.is_anchor(path[-1]) else ["not-trusted", path[-1]]

    def self_issued(self, cert_id: str) -> bool:
        return self.certs[cert_id]["subject"] == self.certs[cert_id]["issuer"]

    def too_deep(self, down: list[str], index: int) -> bool:
        """Some certificate above has a pathLen that the intermediates since then used up."""
        for above in range(index):
            limit = self.certs[down[above]]["len"]
            used = sum(not self.self_issued(c) for c in down[above + 1 : index])
            if limit >= 0 and used >= limit:
                return True
        return False

    def basic(self, signer: str, cert_id: str, now: int) -> str | None:
        if (signer, cert_id) not in self.good:
            return "bad-signature"
        reason = self.dates(self.certs[cert_id], now)
        if reason:
            return reason
        if self.is_revoked(cert_id):
            return "revoked"
        if self.certs[cert_id]["issuer"] != self.certs[signer]["subject"]:
            return "name-mismatch"
        return None

    def as_issuer(self, down: list[str], index: int) -> str | None:
        cert = self.certs[down[index]]
        if not cert["ca"]:
            return "not-a-ca"
        if not self.self_issued(down[index]) and self.too_deep(down, index):
            return "path-too-long"
        if cert["usage"] and "keyCertSign" not in cert["usage"]:
            return "missing-key-cert-sign"
        return None

    def walk(self, path: list[str], now: int) -> list[str] | None:
        down = path[:-1][::-1]
        signers = [path[-1], *down]
        for index, cert_id in enumerate(down):
            reason = self.basic(signers[index], cert_id, now)
            if reason is None and index < len(down) - 1:
                reason = self.as_issuer(down, index)
            if reason:
                return [reason, cert_id]
        return None

    def validate_path(self, path: list[str], hostname: str, now: int) -> list[str]:
        problem = self.structure(path) or self.walk(path, now)
        if problem:
            return problem
        return (
            ["ok", ""] if self.matched_name(path[0], hostname) else ["hostname-mismatch", path[0]]
        )

    # --- level 4
    def revoke(self, cert_id: str) -> bool:
        if cert_id not in self.certs or cert_id in self.revoked:
            return False
        self.revoked.append(cert_id)
        return True

    def is_revoked(self, cert_id: str) -> bool:
        return cert_id in self.revoked

    def verify(self, leaf_id: str, hostname: str, now: int) -> list[list[str]]:
        if leaf_id not in self.certs:
            return [["unknown-certificate", leaf_id]]
        if self.is_anchor(leaf_id):
            return [["leaf-is-anchor", leaf_id]]
        rows: list[list[str]] = []
        for chain in self.chains(leaf_id):
            rows.append(self.validate_path(chain, hostname, now) + chain)
            if self.done(rows):
                break
        return rows or [["no-path", leaf_id]]

    def done(self, rows: list[list[str]]) -> bool:
        return rows[-1][0] == "ok"


# --- level 1 mistakes
class EndDateExclusive(Model):
    """A certificate is already expired at `notAfter`."""

    def too_late(self, cert: dict[str, Any], now: int) -> bool:
        return now >= cert["to"]


class StartDateExclusive(Model):
    """A certificate is not yet valid at `notBefore`."""

    def too_early(self, cert: dict[str, Any], now: int) -> bool:
        return now <= cert["from"]


class HostnameBeforeDates(Model):
    """`checkLeaf` looks at the name before the dates."""

    def check_leaf(self, cert_id: str, hostname: str, now: int) -> str:
        if cert_id in self.certs and not self.matched_name(cert_id, hostname):
            return "hostname-mismatch"
        return super().check_leaf(cert_id, hostname, now)


class NamesCaseSensitive(Model):
    """`Shop.EXAMPLE` does not match `shop.example`."""

    def matched_name(self, cert_id: str, hostname: str) -> str:
        for name in self.certs.get(cert_id, {}).get("names", []):
            pattern = self.name_regex(name)
            if pattern is not None and name == name.lower() and re.fullmatch(pattern, hostname):
                return name
        return ""


class MatchedNameLowercased(Model):
    """The matching entry is returned in lowercase instead of as written."""

    def shown(self, name: str) -> str:
        return name.lower()


class LastMatchingName(Model):
    """The last matching entry is returned, not the first."""

    def matched_name(self, cert_id: str, hostname: str) -> str:
        names = self.certs.get(cert_id, {}).get("names", [])
        self.certs.get(cert_id, {})["names"] = names[::-1]
        try:
            return super().matched_name(cert_id, hostname)
        finally:
            self.certs.get(cert_id, {})["names"] = names


class WildcardCoversSeveralLabels(Model):
    """`*.shop.example` also matches `a.b.shop.example`."""

    def name_regex(self, name: str) -> str | None:
        pattern = super().name_regex(name)
        return pattern.replace(LABEL, r"[a-z0-9.\-]+", 1) if pattern and "*" in name else pattern


class WildcardCoversTheApex(Model):
    """`*.shop.example` also matches `shop.example`."""

    def name_regex(self, name: str) -> str | None:
        pattern = super().name_regex(name)
        if pattern and "*" in name:
            return "(?:" + LABEL + r"\.)?" + re.escape(".".join(name.lower().split(".")[1:]))
        return pattern


class PartialWildcards(Model):
    """`f*.shop.example` matches `foo.shop.example`, as the older rules allowed."""

    def name_regex(self, name: str) -> str | None:
        labels = name.lower().split(".")
        if name.count("*") == 1 and "*" in labels[0] and labels[0] != "*" and len(labels) >= 3:
            left = re.escape(labels[0]).replace(r"\*", r"[a-z0-9\-]*")
            return left + re.escape("." + ".".join(labels[1:]))
        return super().name_regex(name)


class WildcardInAnyLabel(Model):
    """`www.*.shop.example` matches `www.x.shop.example`."""

    def name_regex(self, name: str) -> str | None:
        labels = name.lower().split(".")
        if name.count("*") == 1 and "*" in labels[1:] and len(labels) >= 3:
            return r"\.".join(LABEL if label == "*" else re.escape(label) for label in labels)
        return super().name_regex(name)


class NoTwoLabelRule(Model):
    """`*.example` is accepted."""

    def name_regex(self, name: str) -> str | None:
        labels = name.lower().split(".")
        if labels[0] == "*" and name.count("*") == 1 and len(labels) == 2:
            return LABEL + re.escape("." + labels[1])
        return super().name_regex(name)


class CommonNameFallback(Model):
    """With no DNS names, the subject's `CN=` is used as one."""

    def matched_name(self, cert_id: str, hostname: str) -> str:
        cert = self.certs.get(cert_id)
        if cert and not cert["names"] and cert["subject"].lower() == "cn=" + hostname.lower():
            return cert["subject"][3:]
        return super().matched_name(cert_id, hostname)


class SuffixMatch(Model):
    """A hostname matches a name it ends with."""

    def name_regex(self, name: str) -> str | None:
        pattern = super().name_regex(name)
        return ".*" + pattern if pattern is not None and "*" not in name else pattern


class TakenIdReplaced(Model):
    """A second certificate with the same id replaces the first."""

    def add_certificate(self, cert_id, subject, issuer, not_before, not_after, dns_names) -> bool:
        self.certs.pop(cert_id, None)
        return super().add_certificate(cert_id, subject, issuer, not_before, not_after, dns_names)


# --- level 2 mistakes
class LinksByNameOnly(Model):
    """Any certificate with the right subject is an issuer, signature or not."""

    def links(self, cert_id: str) -> list[str]:
        issuer = self.certs[cert_id]["issuer"]
        return [s for s in self.certs if self.certs[s]["subject"] == issuer]


class LinksBySignatureOnly(Model):
    """Any certificate with a valid signature is an issuer, whatever its name."""

    def links(self, cert_id: str) -> list[str]:
        return [s for s in self.certs if (s, cert_id) in self.good]


class SignatureEitherWay(Model):
    """A signature recorded in the other direction also links."""

    def links(self, cert_id: str) -> list[str]:
        issuer = self.certs[cert_id]["issuer"]
        return [
            s
            for s in self.certs
            if self.certs[s]["subject"] == issuer
            and ((s, cert_id) in self.good or (cert_id, s) in self.good)
        ]


class NamesWithoutCase(Model):
    """Subject and issuer names are compared without case."""

    def links(self, cert_id: str) -> list[str]:
        issuer = self.certs[cert_id]["issuer"].lower()
        return [
            s
            for s in self.certs
            if self.certs[s]["subject"].lower() == issuer and (s, cert_id) in self.good
        ]


class FirstIssuerOnly(Model):
    """The search follows the first issuer it finds and never backtracks."""

    def chains(self, leaf_id: str) -> list[list[str]]:
        if leaf_id not in self.certs:
            return []
        chain = [leaf_id]
        while not self.is_anchor(chain[-1]):
            options = [s for s in self.links(chain[-1]) if s not in chain]
            if not options:
                return []
            chain.append(options[0])
        return [chain]


class TiesInInsertionOrder(Model):
    """Equally short chains keep the order in which their certificates were added."""

    def order(self, chains: list[list[str]]) -> list[list[str]]:
        return chains


class IdsBeforeLength(Model):
    """Chains are sorted by their ids first, so a longer chain can win."""

    def build_chain(self, leaf_id: str) -> list[str]:
        return min(self.chains(leaf_id), default=[])


class NoLoopCheck(Model):
    """The search may revisit a certificate, and runs in circles."""

    def extend(self, chain: list[str], signer: str) -> bool:
        if len(chain) > 40:
            raise RecursionError("loop")
        return True


class AnchorsMustBeSelfSigned(Model):
    """Only a self-signed certificate can end a chain."""

    def is_anchor(self, cert_id: str) -> bool:
        return super().is_anchor(cert_id) and self.self_issued(cert_id)


class AnchorAddedTwice(Model):
    """`addTrustAnchor` reports success for an anchor it already has."""

    def add_trust_anchor(self, cert_id: str) -> bool:
        if cert_id in self.anchors:
            return True
        return super().add_trust_anchor(cert_id)


# --- level 3 mistakes
class TrustBeforeUnknown(Model):
    """An untrusted end is reported before an unknown certificate."""

    def structure(self, path: list[str]) -> list[str] | None:
        if path[-1] in self.certs and not self.is_anchor(path[-1]):
            return ["not-trusted", path[-1]]
        return super().structure(path)


class FromTheLeafUp(Model):
    """Certificates are checked from the leaf towards the anchor."""

    def walk(self, path: list[str], now: int) -> list[str] | None:
        down = path[:-1][::-1]
        signers = [path[-1], *down]
        for index in reversed(range(len(down))):
            reason = self.basic(signers[index], down[index], now)
            if reason is None and index < len(down) - 1:
                reason = self.as_issuer(down, index)
            if reason:
                return [reason, down[index]]
        return None


class NameBeforeSignature(Model):
    """The issuer name is compared before the signature is checked."""

    def basic(self, signer: str, cert_id: str, now: int) -> str | None:
        if self.certs[cert_id]["issuer"] != self.certs[signer]["subject"]:
            return "name-mismatch"
        return super().basic(signer, cert_id, now)


class HostnameFirst(Model):
    """The hostname is checked before the path."""

    def validate_path(self, path: list[str], hostname: str, now: int) -> list[str]:
        problem = self.structure(path)
        if problem is None and not self.matched_name(path[0], hostname):
            return ["hostname-mismatch", path[0]]
        return super().validate_path(path, hostname, now)


class LeafCheckedAsIssuer(Model):
    """The leaf must also be a CA allowed to sign certificates."""

    def walk(self, path: list[str], now: int) -> list[str] | None:
        problem = super().walk(path, now)
        if problem is None:
            reason = self.as_issuer(path[:-1][::-1], len(path) - 2)
            if reason:
                return [reason, path[0]]
        return problem


class AnchorChecked(Model):
    """The trust anchor's dates and constraints are checked like an intermediate's."""

    def walk(self, path: list[str], now: int) -> list[str] | None:
        anchor = self.certs[path[-1]]
        reason = self.dates(anchor, now) or (None if anchor["ca"] else "not-a-ca")
        return [reason, path[-1]] if reason else super().walk(path, now)


class NoCaCheck(Model):
    """Any certificate may sign certificates."""

    def as_issuer(self, down: list[str], index: int) -> str | None:
        reason = super().as_issuer(down, index)
        return None if reason == "not-a-ca" else reason


class AbsentKeyUsageForbids(Model):
    """A certificate without the key usage extension may not sign certificates."""

    def as_issuer(self, down: list[str], index: int) -> str | None:
        reason = super().as_issuer(down, index)
        if reason is None and not self.certs[down[index]]["usage"]:
            return "missing-key-cert-sign"
        return reason


class KeyUsageIgnored(Model):
    """`keyCertSign` is never required."""

    def as_issuer(self, down: list[str], index: int) -> str | None:
        reason = super().as_issuer(down, index)
        return None if reason == "missing-key-cert-sign" else reason


class SelfIssuedCounts(Model):
    """Self-issued intermediates count against `pathLen`."""

    def self_issued(self, cert_id: str) -> bool:
        return False


class PathLenOffByOne(Model):
    """`pathLen` 0 still allows one more intermediate."""

    def too_deep(self, down: list[str], index: int) -> bool:
        for above in range(index):
            limit = self.certs[down[above]]["len"]
            used = sum(not self.self_issued(c) for c in down[above + 1 : index])
            if limit >= 0 and used > limit:
                return True
        return False


class PathLenCountsItself(Model):
    """A certificate's own `pathLen` already limits it, as if it were applied before the step."""

    def too_deep(self, down: list[str], index: int) -> bool:
        own = self.certs[down[index]]["len"]
        return super().too_deep(down, index) or own == 0


class AnchorPathLenApplies(Model):
    """The trust anchor's `pathLen` limits the chain."""

    def walk(self, path: list[str], now: int) -> list[str] | None:
        limit = self.certs[path[-1]]["len"]
        down = path[:-1][::-1]
        for index in range(1, len(down) - 1):
            used = sum(not self.self_issued(c) for c in down[:index])
            if limit >= 0 and used >= limit and not self.self_issued(down[index]):
                return ["path-too-long", down[index]]
        return super().walk(path, now)


class ConstraintsForUnknownIds(Model):
    """`setConstraints` reports success for an unknown id."""

    def set_constraints(self, cert_id, is_ca, path_len, key_usage) -> bool:
        return super().set_constraints(cert_id, is_ca, path_len, key_usage) or True


# --- level 4 mistakes
class RevocationIgnored(Model):
    """Revoked certificates are accepted."""

    def is_revoked(self, cert_id: str) -> bool:
        return False


class RevocationBeforeDates(Model):
    """Revocation is checked before the dates."""

    def basic(self, signer: str, cert_id: str, now: int) -> str | None:
        if (signer, cert_id) in self.good and self.is_revoked(cert_id):
            return "revoked"
        return super().basic(signer, cert_id, now)


class RevokedAnchorRejected(Model):
    """A revoked trust anchor fails the chain."""

    def walk(self, path: list[str], now: int) -> list[str] | None:
        return ["revoked", path[-1]] if self.is_revoked(path[-1]) else super().walk(path, now)


class CheckLeafSeesRevocation(Model):
    """`checkLeaf` also reports a revoked leaf."""

    def check_leaf(self, cert_id: str, hostname: str, now: int) -> str:
        reason = super().check_leaf(cert_id, hostname, now)
        return "revoked" if reason == "ok" and self.is_revoked(cert_id) else reason


class VerifyStopsAtTheFirstFailure(Model):
    """`verify` gives up after the first chain, whatever its result."""

    def done(self, rows: list[list[str]]) -> bool:
        return True


class VerifyTriesEveryChain(Model):
    """`verify` goes on after a valid chain."""

    def done(self, rows: list[list[str]]) -> bool:
        return False


class UnknownLeafHasNoPath(Model):
    """An unknown leaf is reported as having no chain."""

    def verify(self, leaf_id: str, hostname: str, now: int) -> list[list[str]]:
        return (
            [["no-path", leaf_id]]
            if leaf_id not in self.certs
            else super().verify(leaf_id, hostname, now)
        )


class NoPathReportsNothing(Model):
    """A leaf without any chain gets no rows."""

    def verify(self, leaf_id: str, hostname: str, now: int) -> list[list[str]]:
        rows = super().verify(leaf_id, hostname, now)
        return [] if rows[0][0] == "no-path" else rows


class AnchoredLeafIsItsOwnChain(Model):
    """A leaf that is a trust anchor is a chain of one."""

    def build_chain(self, leaf_id: str) -> list[str]:
        return [leaf_id] if self.is_anchor(leaf_id) else super().build_chain(leaf_id)


class AnchoredLeafSearchesOn(Model):
    """A leaf that is a trust anchor is treated like any leaf, and the search goes past it."""

    def chains(self, leaf_id: str) -> list[list[str]]:
        if not self.is_anchor(leaf_id):
            return super().chains(leaf_id)
        self.anchors.remove(leaf_id)
        try:
            return super().chains(leaf_id)
        finally:
            self.anchors.append(leaf_id)

    def verify(self, leaf_id: str, hostname: str, now: int) -> list[list[str]]:
        rows: list[list[str]] = []
        for chain in self.chains(leaf_id):
            rows.append(self.walk(chain, now) or ["ok", ""])
            rows[-1] += chain
            if self.done(rows):
                break
        return rows or super().verify(leaf_id, hostname, now)


class AnchoredLeafChecksOnlyTheHostname(Model):
    """`verify` on a leaf that is a trust anchor checks nothing but its name."""

    def verify(self, leaf_id: str, hostname: str, now: int) -> list[list[str]]:
        if leaf_id in self.certs and self.is_anchor(leaf_id):
            if self.matched_name(leaf_id, hostname):
                return [["ok", "", leaf_id]]
            return [["hostname-mismatch", leaf_id, leaf_id]]
        return super().verify(leaf_id, hostname, now)


class AnchoredLeafCheckedLast(Model):
    """`validatePath` looks for a trusted leaf only after the other structure checks."""

    def structure(self, path: list[str]) -> list[str] | None:
        anchors, self.anchors = self.anchors, [a for a in self.anchors if a != path[0]]
        try:
            problem = super().structure(path)
        finally:
            self.anchors = anchors
        if problem is not None and problem[0] != "not-trusted":
            return problem
        return super().structure(path)


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, RecursionError):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_visible_and_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_give_every_reason():
    reasons = set()
    for case in HIDDEN_CASES:
        for op, got in zip(case["ops"], case["expected"], strict=True):
            if op == "checkLeaf":
                reasons.add(got)
            elif op == "validatePath":
                reasons.add(got[0])
            elif op == "verify":
                reasons.update(row[0] for row in got)
    assert reasons == {
        "ok",
        "unknown-certificate",
        "repeated-certificate",
        "not-trusted",
        "bad-signature",
        "not-yet-valid",
        "expired",
        "revoked",
        "name-mismatch",
        "not-a-ca",
        "path-too-long",
        "missing-key-cert-sign",
        "hostname-mismatch",
        "no-path",
        "leaf-is-anchor",
    }
