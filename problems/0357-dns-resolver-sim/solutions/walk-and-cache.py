from collections.abc import Iterator

ROOT = "."
MAX_CHAIN = 8
NAME_DATA = ("CNAME", "NS", "MX", "SOA")
NXDOMAIN_KEY = "*"

Rows = list[list[str]]


def ancestors(name: str) -> list[str]:
    """The name, its parent, and so on up to the root."""
    if name == ROOT:
        return [ROOT]
    labels = name.split(".")
    return [".".join(labels[i:]) for i in range(len(labels))] + [ROOT]


def within(name: str, zone: str) -> bool:
    return zone == ROOT or name == zone or name.endswith("." + zone)


def soa_minimum(data: str) -> int:
    return int(data.split(" ")[6])


class DnsResolver:
    """Servers answer from their own records the way an authoritative server does: an answer,
    a referral to a delegated child zone, or a negative answer with the zone's SOA. The resolver
    walks from the closest zone whose servers it knows (the root at first) down the referrals,
    and keeps three caches: answers, which it may return; referral data (NS sets and glue),
    which it only uses to find servers; and negative answers. Every entry expires on the
    virtual clock.
    """

    def __init__(self) -> None:
        self._servers: dict[str, dict[tuple[str, str], tuple[int, list[str]]]] = {}
        self._hints: dict[str, list[str]] = {}
        self._answers: dict[tuple[str, str], tuple[int, list[str]]] = {}
        self._referrals: dict[str, tuple[int, list[str]]] = {}
        self._glue: dict[tuple[str, str], tuple[int, list[str]]] = {}
        self._negative: dict[tuple[str, str], int] = {}
        self._trace: Rows = []
        self._now = 0

    # Level 1
    def add_record(self, server: str, name: str, rtype: str, ttl: int, data: str) -> None:
        records = self._servers.setdefault(server, {})
        if rtype in NAME_DATA:
            data = data.lower()
        key = (name.lower(), rtype)
        values = records.get(key, (ttl, []))[1]
        if data not in values:
            values = sorted([*values, data])
        records[key] = (ttl, values)

    def lookup(self, server: str, name: str, qtype: str) -> Rows:
        records = self._servers.get(server, {})
        name = name.lower()
        zones = [owner for owner, rtype in records if rtype == "SOA" and within(name, owner)]
        if not zones:
            return [["REFUSED"]]
        zone = max(zones, key=lambda owner: len(ancestors(owner)))
        for node in reversed(ancestors(name)):
            if node != zone and within(node, zone) and (node, "NS") in records:
                return self._referral(records, node)
        if (name, qtype) in records:
            return [["NOERROR"], *self._section(records, "answer", name, qtype)]
        if qtype != "CNAME" and (name, "CNAME") in records:
            return [["NOERROR"], *self._section(records, "answer", name, "CNAME")]
        ttl, (soa,) = records[(zone, "SOA")]
        authority = ["authority", zone, "SOA", str(min(ttl, soa_minimum(soa))), soa]
        exists = any(within(owner, name) for owner, _ in records)
        return [["NOERROR" if exists else "NXDOMAIN"], authority]

    # Level 2
    def follow(self, server: str, name: str, qtype: str) -> Rows:
        current = name.lower()
        visited = {current}
        chain: Rows = []
        while True:
            response = self.lookup(server, current, qtype)
            if response[0] == ["REFUSED"]:
                return [["NOERROR"], *chain] if chain else response
            alias = self._alias(response, qtype)
            if alias is None:
                return [response[0], *chain, *response[1:]]
            chain.append(alias)
            current = alias[4]
            if current in visited or len(chain) > MAX_CHAIN:
                return [["SERVFAIL"], *chain]
            visited.add(current)

    # Level 3
    def add_root_hint(self, name: str, address: str) -> None:
        addresses = self._hints.setdefault(name.lower(), [])
        if address not in addresses:
            addresses.append(address)
            addresses.sort()

    def resolve(self, name: str, qtype: str, now: int) -> Rows:
        self._now = now
        self._trace = []
        rcode, rows = self._resolve(name.lower(), qtype, frozenset())
        return [[rcode], *rows]

    def trace(self) -> Rows:
        return [list(query) for query in self._trace]

    # Level 4
    def negatives(self, now: int) -> Rows:
        return [
            [name, rtype, str(expiry - now)]
            for (name, rtype), expiry in sorted(self._negative.items())
            if now < expiry
        ]

    # Server side
    def _section(self, records: dict, section: str, owner: str, rtype: str) -> Rows:
        ttl, values = records[(owner, rtype)]
        return [[section, owner, rtype, str(ttl), value] for value in values]

    def _referral(self, records: dict, cut: str) -> Rows:
        authority = self._section(records, "authority", cut, "NS")
        additional = [
            row
            for target in records[(cut, "NS")][1]
            for rtype in ("A", "AAAA")
            if (target, rtype) in records
            for row in self._section(records, "additional", target, rtype)
        ]
        additional.sort(key=lambda row: (row[1], row[2], row[4]))
        return [["NOERROR"], *authority, *additional]

    @staticmethod
    def _alias(response: Rows, qtype: str) -> list[str] | None:
        answers = [row for row in response[1:] if row[0] == "answer"]
        if qtype != "CNAME" and len(answers) == 1 and answers[0][2] == "CNAME":
            return answers[0]
        return None

    # Resolver side
    def _valid(self, entry: tuple[int, list[str]] | None) -> list[str] | None:
        return entry[1] if entry is not None and self._now < entry[0] else None

    def _cached(self, name: str, rtype: str) -> Rows | None:
        entry = self._answers.get((name, rtype))
        if entry is None or self._now >= entry[0]:
            return None
        expiry, values = entry
        return [["answer", name, rtype, str(expiry - self._now), value] for value in values]

    def _resolve(self, qname: str, qtype: str, pending: frozenset[str]) -> tuple[str, Rows]:
        chain: Rows = []
        visited = {qname}
        current = qname
        while True:
            found = self._cached(current, qtype)
            if found is not None:
                return "NOERROR", chain + found
            alias = self._cached(current, "CNAME") if qtype != "CNAME" else None
            if alias is None:
                negative = self._negative_answer(current, qtype)
                if negative is not None:
                    return negative, chain
                response = self._ask(current, qtype, pending)
                if response is None:
                    return "SERVFAIL", chain
                alias = self._absorb(response, current, qtype)
                if alias is None:
                    rcode = response[0][0]
                    rows = [row for row in response[1:] if row[0] == "answer"]
                    return rcode, chain + rows
                alias = [alias]
            chain.append(alias[0])
            current = alias[0][4]
            if current in visited or len(chain) > MAX_CHAIN:
                return "SERVFAIL", chain
            visited.add(current)

    def _absorb(self, response: Rows, qname: str, qtype: str) -> list[str] | None:
        """Caches a final response and returns its CNAME when it is an alias."""
        answers = [row for row in response[1:] if row[0] == "answer"]
        if answers:
            rtype = answers[0][2]
            self._answers[(qname, rtype)] = (
                self._now + int(answers[0][3]),
                [row[4] for row in answers],
            )
            return self._alias(response, qtype)
        soa = [row for row in response[1:] if row[2] == "SOA"]
        if soa:
            key = (qname, NXDOMAIN_KEY if response[0] == ["NXDOMAIN"] else qtype)
            self._negative[key] = self._now + int(soa[0][3])
        return None

    def _negative_answer(self, name: str, qtype: str) -> str | None:
        if self._now < self._negative.get((name, NXDOMAIN_KEY), self._now):
            return "NXDOMAIN"
        if self._now < self._negative.get((name, qtype), self._now):
            return "NOERROR"
        return None

    def _ns_names(self, zone: str) -> list[str] | None:
        if zone == ROOT:
            return sorted(self._hints) or None
        answered = self._valid(self._answers.get((zone, "NS")))
        if answered is not None:
            return answered
        return self._valid(self._referrals.get(zone))

    def _known_addresses(self, zone: str, server: str) -> list[str]:
        if zone == ROOT:
            return self._hints.get(server, [])
        for source in (self._answers, self._glue):
            found = [
                address
                for rtype in ("A", "AAAA")
                for address in self._valid(source.get((server, rtype))) or []
            ]
            if found:
                return found
        return []

    def _addresses(self, zone: str, names: list[str], pending: frozenset[str]) -> Iterator[str]:
        """Addresses to ask, in order: those of the servers whose addresses are known, then the
        others, each looked up first; an address is asked once per zone."""
        seen: set[str] = set()
        known = [(server, self._known_addresses(zone, server)) for server in names]
        for _, addresses in known:
            for address in addresses:
                if address not in seen:
                    seen.add(address)
                    yield address
        for server, addresses in known:
            if addresses:
                continue
            addresses = self._known_addresses(zone, server)
            if not addresses and server not in pending:
                _, rows = self._resolve(server, "A", pending | {server})
                addresses = [row[4] for row in rows if row[2] == "A"]
            for address in addresses:
                if address not in seen:
                    seen.add(address)
                    yield address

    def _ask(self, qname: str, qtype: str, pending: frozenset[str]) -> Rows | None:
        """Walks down from the closest zone with known servers to a final response."""
        zone = next(z for z in ancestors(qname) if self._ns_names(z) is not None or z == ROOT)
        while True:
            names = self._ns_names(zone) or []
            child = None
            for address in self._addresses(zone, names, pending):
                self._trace.append([address, qname, qtype])
                response = self.lookup(address, qname, qtype)
                if response[0] == ["REFUSED"]:
                    continue
                cut = self._referral_zone(response)
                if cut is None:
                    return response
                if cut != zone and within(cut, zone) and within(qname, cut):
                    self._remember_referral(response, zone)
                    child = cut
                    break
            if child is None:
                return None
            zone = child

    @staticmethod
    def _referral_zone(response: Rows) -> str | None:
        if any(row[0] == "answer" for row in response[1:]):
            return None
        cuts = [row[1] for row in response[1:] if row[0] == "authority" and row[2] == "NS"]
        return cuts[0] if cuts else None

    def _remember_referral(self, response: Rows, zone: str) -> None:
        ns = [row for row in response[1:] if row[0] == "authority"]
        self._referrals[ns[0][1]] = (self._now + int(ns[0][3]), [row[4] for row in ns])
        groups: dict[tuple[str, str], list[list[str]]] = {}
        for row in response[1:]:
            if row[0] == "additional" and within(row[1], zone):
                groups.setdefault((row[1], row[2]), []).append(row)
        for key, rows in groups.items():
            self._glue[key] = (self._now + int(rows[0][3]), [row[4] for row in rows])
