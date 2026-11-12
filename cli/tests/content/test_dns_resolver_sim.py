"""dns-resolver-sim promises that its hidden cases catch the classic mistakes of answering and
resolving DNS names: case-sensitive or suffix-by-text name matching, the wrong zone, an empty
non-terminal taken for a missing name, SOA TTLs not lowered to the MINIMUM, CNAME loops found
too late or not at all, a resolver without a cache, TTLs that never count down, glue returned as
an answer, delegations without glue left unresolved, bogus referrals followed, negative answers
not cached or cached for the wrong key, and glue for unrelated names trusted. These tests replay
every case against a model of the servers and the resolver written from the statement, which must
give every expected output, and against that model with one mistake planted at a time, which some
hidden case must fail. A mistake that crashes or recurses without end fails its case, as a thrown
exception does in the grader.

The model keeps each server's data as a flat set of records and resolves recursively, so it
shares no data structure with the reference solutions."""

import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0357-dns-resolver-sim"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

ROOT = "."
CHAIN_LIMIT = 8
ANY = "*"

Record = tuple[str, str, int, str]
Rows = list[list[str]]


def labels(name: str) -> list[str]:
    return [] if name == ROOT else name.split(".")


def lineage(name: str) -> list[str]:
    """The root, then each name on the way down to `name`."""
    parts = labels(name)
    return [ROOT] + [".".join(parts[i:]) for i in range(len(parts) - 1, -1, -1)]


class Model:
    """The servers and the resolver as the statement words them. Each mistake below overrides
    one method."""

    def __init__(self) -> None:
        self.data: dict[str, set[Record]] = defaultdict(set)
        self.hints: dict[str, set[str]] = defaultdict(set)
        self.answers: dict[tuple[str, str], tuple[int, list[str]]] = {}
        self.delegations: dict[str, tuple[int, list[str]]] = {}
        self.glue: dict[tuple[str, str], tuple[int, list[str]]] = {}
        self.negative: dict[tuple[str, str], int] = {}
        self.sent: Rows = []
        self.clock = 0

    # --- names and records
    def norm(self, name: str) -> str:
        return name.lower()

    def under(self, name: str, zone: str) -> bool:
        tail = labels(zone)
        return not tail or labels(name)[-len(tail) :] == tail

    def stored_data(self, rtype: str, data: str) -> str:
        return data.lower() if rtype in ("CNAME", "NS", "MX", "SOA") else data

    def add_record(self, server: str, name: str, rtype: str, ttl: int, data: str) -> None:
        self.data[server].add((self.norm(name), rtype, ttl, self.stored_data(rtype, data)))

    def order(self, values: list[str]) -> list[str]:
        return sorted(set(values))

    def rrset(self, server: str, name: str, rtype: str) -> tuple[int, list[str]] | None:
        found = [(ttl, data) for n, t, ttl, data in self.data[server] if n == name and t == rtype]
        if not found:
            return None
        return found[0][0], self.order([data for _, data in found])

    def rows(self, section: str, server: str, name: str, rtype: str) -> Rows:
        ttl, values = self.rrset(server, name, rtype) or (0, [])
        return [[section, name, rtype, str(ttl), value] for value in values]

    # --- level 1: the server
    def zone_of(self, server: str, name: str) -> str | None:
        zones = [n for n, t, _, _ in self.data[server] if t == "SOA" and self.under(name, n)]
        return max(zones, key=lambda zone: len(labels(zone))) if zones else None

    def cut_below(self, server: str, zone: str, name: str) -> str | None:
        for node in lineage(name):
            if node != zone and self.under(node, zone) and self.rrset(server, node, "NS"):
                return node
        return None

    def exists(self, server: str, name: str) -> bool:
        return any(self.under(owner, name) for owner, _, _, _ in self.data[server])

    def alias_for(self, qtype: str) -> bool:
        return qtype != "CNAME"

    def negative_ttl(self, ttl: int, soa: str) -> int:
        return min(ttl, int(soa.split()[6]))

    def soa_row(self, server: str, zone: str) -> list[str]:
        ttl, (soa,) = self.rrset(server, zone, "SOA")  # type: ignore[misc]
        return ["authority", zone, "SOA", str(self.negative_ttl(ttl, soa)), soa]

    def referral(self, server: str, cut: str) -> Rows:
        authority = self.rows("authority", server, cut, "NS")
        additional = sorted(
            (
                row
                for *_, target in authority
                for rtype in ("A", "AAAA")
                for row in self.rows("additional", server, target, rtype)
            ),
            key=lambda row: (row[1], row[2], row[4]),
        )
        return [["NOERROR"], *authority, *additional]

    def lookup(self, server: str, name: str, qtype: str) -> Rows:
        name = self.norm(name)
        zone = self.zone_of(server, name)
        if zone is None:
            return [["REFUSED"]]
        cut = self.cut_below(server, zone, name)
        if cut is not None:
            return self.referral(server, cut)
        if self.rrset(server, name, qtype):
            return [["NOERROR"], *self.rows("answer", server, name, qtype)]
        if self.alias_for(qtype) and self.rrset(server, name, "CNAME"):
            return [["NOERROR"], *self.rows("answer", server, name, "CNAME")]
        code = "NOERROR" if self.exists(server, name) else "NXDOMAIN"
        return [[code], self.soa_row(server, zone)]

    # --- level 2: chains
    def repeated(self, target: str, seen: list[str]) -> bool:
        return target in seen

    def too_long(self, chain: Rows) -> bool:
        return len(chain) > CHAIN_LIMIT

    def is_alias(self, response: Rows, qtype: str) -> bool:
        rows = response[1:]
        return (
            qtype != "CNAME" and len(rows) == 1 and rows[0][0] == "answer" and rows[0][2] == "CNAME"
        )

    def follow(self, server: str, name: str, qtype: str) -> Rows:
        seen = [self.norm(name)]
        chain: Rows = []
        while True:
            response = self.lookup(server, seen[-1], qtype)
            if response == [["REFUSED"]]:
                return self.refused_chain(chain, response)
            if not self.is_alias(response, qtype):
                return [response[0], *chain, *response[1:]]
            chain.append(response[1])
            if self.repeated(response[1][4], seen) or self.too_long(chain):
                return [["SERVFAIL"], *chain]
            seen.append(response[1][4])

    def refused_chain(self, chain: Rows, response: Rows) -> Rows:
        return [["NOERROR"], *chain] if chain else response

    # --- level 3: the resolver
    def add_root_hint(self, name: str, address: str) -> None:
        self.hints[self.norm(name)].add(address)

    def fresh(self, expiry: int) -> bool:
        return self.clock < expiry

    def shown_ttl(self, expiry: int, ttl: int) -> int:
        return expiry - self.clock

    def cached_answer(self, name: str, rtype: str) -> Rows | None:
        if (name, rtype) not in self.answers:
            return None
        expiry, values = self.answers[(name, rtype)]
        if not self.fresh(expiry):
            return None
        return [["answer", name, rtype, str(self.shown_ttl(expiry, 0)), v] for v in values]

    def store_answer(self, rows: Rows) -> None:
        self.answers[(rows[0][1], rows[0][2])] = (
            self.clock + int(rows[0][3]),
            [row[4] for row in rows],
        )

    def server_names(self, zone: str) -> list[str] | None:
        if zone == ROOT:
            return sorted(self.hints) or None
        for cache, key in ((self.answers, (zone, "NS")), (self.delegations, zone)):
            entry = cache.get(key)  # type: ignore[attr-defined]
            if entry and self.fresh(entry[0]):
                return list(entry[1])
        return None

    def addresses_of(self, zone: str, server: str) -> list[str]:
        if zone == ROOT:
            return sorted(self.hints.get(server, ()))
        for cache in self.address_sources():
            found: list[str] = []
            for rtype in ("A", "AAAA"):
                entry = cache.get((server, rtype))
                if entry and self.fresh(entry[0]):
                    found += entry[1]
            if found:
                return found
        return []

    def address_sources(self) -> list[dict]:
        return [self.answers, self.glue]

    def first_known(self, zone: str, names: list[str]) -> list[str]:
        """Names whose addresses are known come first."""
        return [n for n in names if self.addresses_of(zone, n)] + [
            n for n in names if not self.addresses_of(zone, n)
        ]

    def lookup_address(self, server: str, busy: frozenset[str]) -> list[str]:
        if server in busy:
            return []
        _, rows = self.walk(server, "A", busy | {server})
        return [row[4] for row in rows if row[2] == "A"]

    def candidates(self, zone: str, names: list[str], busy: frozenset[str]):
        asked: set[str] = set()
        for server in self.first_known(zone, names):
            found = self.addresses_of(zone, server) or self.lookup_address(server, busy)
            for address in found:
                if self.ask_again(address, asked):
                    asked.add(address)
                    yield address

    def ask_again(self, address: str, asked: set[str]) -> bool:
        return address not in asked

    def closer(self, cut: str, zone: str, name: str) -> bool:
        return cut != zone and self.under(cut, zone) and self.under(name, cut)

    def keep_glue(self, name: str, zone: str) -> bool:
        return self.under(name, zone)

    def remember_referral(self, response: Rows, zone: str) -> None:
        ns = [row for row in response if row[0] == "authority"]
        self.delegations[ns[0][1]] = (self.clock + int(ns[0][3]), [row[4] for row in ns])
        grouped: dict[tuple[str, str], list[list[str]]] = defaultdict(list)
        for row in response[1:]:
            if row[0] == "additional" and self.keep_glue(row[1], zone):
                grouped[(row[1], row[2])].append(row)
        for key, rows in grouped.items():
            self.glue[key] = (self.clock + int(rows[0][3]), [row[4] for row in rows])

    def start_zone(self, name: str) -> str:
        for zone in reversed(lineage(name)):
            if self.server_names(zone) is not None:
                return zone
        return ROOT

    def ask_servers(self, name: str, qtype: str, busy: frozenset[str]) -> Rows | None:
        zone = self.start_zone(name)
        while True:
            for address in self.candidates(zone, self.server_names(zone) or [], busy):
                self.sent.append([address, name, qtype])
                response = self.lookup(address, name, qtype)
                if response == [["REFUSED"]]:
                    continue
                kind = self.kind(response)
                if kind != "referral":
                    return response
                cut = response[1][1]
                if self.closer(cut, zone, name):
                    self.remember_referral(response, zone)
                    zone = cut
                    break
                if self.bad_referral_is_final():
                    return response
            else:
                return None

    def bad_referral_is_final(self) -> bool:
        return False

    def kind(self, response: Rows) -> str:
        rows = response[1:]
        no_answer = response[0] == ["NOERROR"] and rows and all(row[0] != "answer" for row in rows)
        if no_answer and rows[0][0] == "authority" and rows[0][2] == "NS":
            return "referral"
        return "final"

    def negative_key(self, name: str, qtype: str, code: str) -> tuple[str, str]:
        return (name, ANY if code == "NXDOMAIN" else qtype)

    def store_negative(self, name: str, qtype: str, response: Rows) -> None:
        soa = [row for row in response[1:] if row[2] == "SOA"]
        if soa:
            key = self.negative_key(name, qtype, response[0][0])
            self.negative[key] = self.clock + int(soa[0][3])

    def cached_negative(self, name: str, qtype: str) -> str | None:
        if self.fresh(self.negative.get((name, ANY), -1)):
            return "NXDOMAIN"
        if self.fresh(self.negative.get((name, qtype), -1)):
            return "NOERROR"
        return None

    def walk(self, name: str, qtype: str, busy: frozenset[str]) -> tuple[str, Rows]:
        chain: Rows = []
        seen = [name]
        while True:
            found = self.cached_answer(name, qtype)
            if found is not None:
                return "NOERROR", chain + found
            link = self.cached_answer(name, "CNAME") if qtype != "CNAME" else None
            if link is None:
                negative = self.cached_negative(name, qtype)
                if negative is not None:
                    return negative, chain
                response = self.ask_servers(name, qtype, busy)
                if response is None:
                    return "SERVFAIL", chain
                answers = [row for row in response[1:] if row[0] == "answer"]
                if answers:
                    self.store_answer(answers)
                if not self.is_alias(response, qtype):
                    if not answers:
                        self.store_negative(name, qtype, response)
                    return response[0][0], chain + answers
                link = answers
            chain.append(link[0])
            name = link[0][4]
            if self.repeated(name, seen) or self.too_long(chain):
                return "SERVFAIL", chain
            seen.append(name)

    def resolve(self, name: str, qtype: str, now: int) -> Rows:
        self.clock = now
        self.sent = []
        code, rows = self.walk(self.norm(name), qtype, frozenset())
        return [[code], *rows]

    def trace(self) -> Rows:
        return self.sent

    # --- level 4
    def negatives(self, now: int) -> Rows:
        return sorted(
            [name, rtype, str(expiry - now)]
            for (name, rtype), expiry in self.negative.items()
            if now < expiry
        )


# --- level 1 mistakes
class NamesCompareWithCase(Model):
    """Compares names as given, without lowercasing them."""

    def norm(self, name: str) -> str:
        return name


class DataKeepsItsCase(Model):
    """Leaves the names inside CNAME, NS, MX and SOA data as given."""

    def stored_data(self, rtype: str, data: str) -> str:
        return data


class AddressesLowercased(Model):
    """Lowercases every data, addresses included."""

    def stored_data(self, rtype: str, data: str) -> str:
        return data.lower()


class SuffixMatchedAsText(Model):
    """Treats any name that ends with the zone's letters as inside the zone."""

    def under(self, name: str, zone: str) -> bool:
        return zone == ROOT or name.endswith(zone)


class FarthestZoneAnswers(Model):
    """Answers from the zone with the fewest labels instead of the closest one."""

    def zone_of(self, server: str, name: str) -> str | None:
        zones = [n for n, t, _, _ in self.data[server] if t == "SOA" and self.under(name, n)]
        return min(zones, key=lambda zone: len(labels(zone))) if zones else None


class EmptyNonTerminalIsMissing(Model):
    """Says a name exists only when it owns a record itself."""

    def exists(self, server: str, name: str) -> bool:
        return any(owner == name for owner, _, _, _ in self.data[server])


class SoaKeepsItsTtl(Model):
    """Puts the SOA in a negative answer with its own TTL."""

    def negative_ttl(self, ttl: int, soa: str) -> int:
        return ttl


class SoaTtlIsTheMinimumField(Model):
    """Uses the MINIMUM field even when the SOA's TTL is smaller."""

    def negative_ttl(self, ttl: int, soa: str) -> int:
        return int(soa.split()[6])


class AliasOnlyForAddresses(Model):
    """Answers with the CNAME only when an address type is asked."""

    def alias_for(self, qtype: str) -> bool:
        return qtype in ("A", "AAAA")


class RecordsInArrivalOrder(Model):
    """Keeps a name's records in the order they were added, duplicates included."""

    def __init__(self) -> None:
        super().__init__()
        self.arrival: dict[str, list[Record]] = defaultdict(list)

    def add_record(self, server: str, name: str, rtype: str, ttl: int, data: str) -> None:
        super().add_record(server, name, rtype, ttl, data)
        self.arrival[server].append((self.norm(name), rtype, ttl, self.stored_data(rtype, data)))

    def rrset(self, server: str, name: str, rtype: str) -> tuple[int, list[str]] | None:
        found = [(t, d) for n, r, t, d in self.arrival[server] if n == name and r == rtype]
        return (found[0][0], [d for _, d in found]) if found else None


# --- level 2 mistakes
class LoopsOnlyAgainstTheFirstName(Model):
    """Checks a CNAME's target only against the name asked."""

    def repeated(self, target: str, seen: list[str]) -> bool:
        return target == seen[0]


class NoLoopCheck(Model):
    """Relies on the chain limit alone."""

    def repeated(self, target: str, seen: list[str]) -> bool:
        return False


class ChainLimitOffByOne(Model):
    """Stops at 8 CNAME records instead of after them."""

    def too_long(self, chain: Rows) -> bool:
        return len(chain) >= CHAIN_LIMIT


class RefusedTargetReportsRefused(Model):
    """Reports REFUSED when a chain leaves the server's zones."""

    def refused_chain(self, chain: Rows, response: Rows) -> Rows:
        return [["REFUSED"], *chain]


class CnameQueriesFollowed(Model):
    """Follows the chain even when the CNAME type itself is asked."""

    def is_alias(self, response: Rows, qtype: str) -> bool:
        rows = response[1:]
        return len(rows) == 1 and rows[0][0] == "answer" and rows[0][2] == "CNAME"


# --- level 3 mistakes
class NothingCached(Model):
    """Never keeps an answer."""

    def store_answer(self, rows: Rows) -> None:
        pass


class TtlNeverCountsDown(Model):
    """Returns cached records with the TTL they arrived with."""

    def cached_answer(self, name: str, rtype: str) -> Rows | None:
        rows = super().cached_answer(name, rtype)
        if rows is None:
            return None
        expiry, _ = self.answers[(name, rtype)]
        origin = self.arrived[(name, rtype)]
        return [[*row[:3], str(expiry - origin), row[4]] for row in rows]

    def store_answer(self, rows: Rows) -> None:
        super().store_answer(rows)
        self.arrived[(rows[0][1], rows[0][2])] = self.clock

    def __init__(self) -> None:
        super().__init__()
        self.arrived: dict[tuple[str, str], int] = {}


class UsableAtExpiry(Model):
    """Still uses an entry at the second its TTL runs out."""

    def fresh(self, expiry: int) -> bool:
        return self.clock <= expiry


class AlwaysFromTheRoot(Model):
    """Ignores the zones it knows and starts every walk at the root."""

    def start_zone(self, name: str) -> str:
        return ROOT


class GlueReturnedAsAnswers(Model):
    """Answers from the addresses learned in referrals."""

    def cached_answer(self, name: str, rtype: str) -> Rows | None:
        found = super().cached_answer(name, rtype)
        entry = self.glue.get((name, rtype))
        if found is None and entry and self.fresh(entry[0]):
            return [["answer", name, rtype, str(entry[0] - self.clock), v] for v in entry[1]]
        return found


class ReferralNsReturnedAsAnswers(Model):
    """Answers NS questions from the NS records learned in referrals."""

    def cached_answer(self, name: str, rtype: str) -> Rows | None:
        found = super().cached_answer(name, rtype)
        entry = self.delegations.get(name)
        if found is None and rtype == "NS" and entry and self.fresh(entry[0]):
            return [["answer", name, "NS", str(entry[0] - self.clock), v] for v in entry[1]]
        return found


class GluelessDelegationsFail(Model):
    """Never looks up the address of a server that came without glue."""

    def lookup_address(self, server: str, busy: frozenset[str]) -> list[str]:
        return []


class ServerNamesInSortedOrderOnly(Model):
    """Asks the servers in name order, looking an address up before trying known ones."""

    def first_known(self, zone: str, names: list[str]) -> list[str]:
        return list(names)


class SharedAddressAskedTwice(Model):
    """Asks an address again for each server name that has it."""

    def ask_again(self, address: str, asked: set[str]) -> bool:
        return True


class AnyReferralIsAnAnswer(Model):
    """Takes a referral that leads no closer as the final response."""

    def bad_referral_is_final(self) -> bool:
        return True


class NoGuardOnNestedLookups(Model):
    """Starts a lookup for a server name it is already looking up."""

    def lookup_address(self, server: str, busy: frozenset[str]) -> list[str]:
        _, rows = self.walk(server, "A", busy)
        return [row[4] for row in rows if row[2] == "A"]


class CnameNotCached(Model):
    """Keeps answers but not CNAME records."""

    def store_answer(self, rows: Rows) -> None:
        if rows[0][2] != "CNAME":
            super().store_answer(rows)


class TraceKeepsEarlierQueries(Model):
    """Keeps the queries of every resolve in the trace."""

    def resolve(self, name: str, qtype: str, now: int) -> Rows:
        earlier = self.sent
        rows = super().resolve(name, qtype, now)
        self.sent = earlier + self.sent
        return rows


class NestedQueriesNotTraced(Model):
    """Leaves the queries sent to find a server's address out of the trace."""

    def lookup_address(self, server: str, busy: frozenset[str]) -> list[str]:
        mark = len(self.sent)
        found = super().lookup_address(server, busy)
        del self.sent[mark:]
        return found


# --- level 4 mistakes
class NoNegativeCache(Model):
    """Never remembers a negative answer."""

    def store_negative(self, name: str, qtype: str, response: Rows) -> None:
        pass


class NameErrorsCachedPerType(Model):
    """Remembers a name error only for the type that was asked."""

    def negative_key(self, name: str, qtype: str, code: str) -> tuple[str, str]:
        return (name, qtype)


class NoDataCachedForEveryType(Model):
    """Remembers a no data answer for every type of the name."""

    def negative_key(self, name: str, qtype: str, code: str) -> tuple[str, str]:
        return (name, ANY)


class NegativeTtlFromTheMinimumField(Model):
    """Times a negative answer by the SOA's MINIMUM field instead of the row's TTL."""

    def store_negative(self, name: str, qtype: str, response: Rows) -> None:
        soa = [row for row in response[1:] if row[2] == "SOA"]
        if soa:
            key = self.negative_key(name, qtype, response[0][0])
            self.negative[key] = self.clock + int(soa[0][4].split()[6])


class NegativeKeptForTheAlias(Model):
    """Remembers a negative answer at the end of a chain under the name asked."""

    def walk(self, name: str, qtype: str, busy: frozenset[str]) -> tuple[str, Rows]:
        before = dict(self.negative)
        code, rows = super().walk(name, qtype, busy)
        added = {key: expiry for key, expiry in self.negative.items() if key not in before}
        if rows and added:
            for key, expiry in added.items():
                del self.negative[key]
                self.negative[(name, key[1])] = expiry
        return code, rows


class UnrelatedGlueTrusted(Model):
    """Keeps every address a referral carries."""

    def keep_glue(self, name: str, zone: str) -> bool:
        return True


class OnlyInDomainGlue(Model):
    """Keeps only glue under the delegated zone, refusing sibling names."""

    def remember_referral(self, response: Rows, zone: str) -> None:
        self.keep_under = response[1][1]
        super().remember_referral(response, zone)

    def keep_glue(self, name: str, zone: str) -> bool:
        return self.under(name, self.keep_under)


class NegativesListExpired(Model):
    """Lists negative entries whose time has run out."""

    def negatives(self, now: int) -> Rows:
        return sorted(
            [name, rtype, str(max(expiry - now, 0))]
            for (name, rtype), expiry in self.negative.items()
        )


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


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_reach_every_response_code():
    codes = {
        result[0][0]
        for case in HIDDEN_CASES
        for op, result in zip(case["ops"], case["expected"], strict=True)
        if op in ("lookup", "follow", "resolve")
    }
    assert codes == {"NOERROR", "NXDOMAIN", "REFUSED", "SERVFAIL"}


def test_every_ttl_is_positive_and_time_never_goes_back():
    for case in CASES:
        times = [
            args[-1]
            for op, args in zip(case["ops"], case["args"], strict=True)
            if op in ("resolve", "negatives")
        ]
        assert times == sorted(times), case["id"]
        for op, args in zip(case["ops"], case["args"], strict=True):
            if op == "addRecord":
                assert args[3] >= 1, case["id"]
