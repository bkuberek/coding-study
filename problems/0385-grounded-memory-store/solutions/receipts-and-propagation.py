import hashlib
import re

RECEIPT_LENGTH = 12
TRUSTED = "trusted"
STALE = "stale"
UNSUPPORTED = "unsupported"
CONTRADICTED = "contradicted"
RANK = {TRUSTED: 0, STALE: 1, UNSUPPORTED: 2, CONTRADICTED: 3}
STATUSES = (TRUSTED, STALE, UNSUPPORTED, CONTRADICTED)
USABLE = {"strict": {TRUSTED}, "lenient": {TRUSTED, STALE}}
WORD = re.compile(r"[a-z0-9]+")


def receipt(text: str) -> str:
    """The first 12 hexadecimal characters of the SHA-256 digest of the text's UTF-8 bytes."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:RECEIPT_LENGTH]


def words(text: str) -> set[str]:
    """Claim texts and queries are printable ASCII, so lower() only changes A to Z."""
    return set(WORD.findall(text.lower()))


class _Source:
    """A source's current text, the receipts of its versions, and the last position of each
    receipt in that history, whose keys are the receipts of every text it has held."""

    __slots__ = ("history", "last", "text")

    def __init__(self, text: str) -> None:
        self.text = text
        self.history: list[str] = []
        self.last: dict[str, int] = {}
        self.append(text)

    def append(self, text: str) -> None:
        self.text = text
        self.last[receipt(text)] = len(self.history)
        self.history.append(receipt(text))

    def current(self) -> str:
        return self.history[-1]

    def behind(self, cited: str) -> int:
        """Versions since the cited receipt was last the current one."""
        return len(self.history) - 1 - self.last[cited]


class _Citation:
    __slots__ = ("receipt", "refuted")

    def __init__(self, cited: str) -> None:
        self.receipt = cited
        self.refuted = False


class _Claim:
    __slots__ = ("citations", "order", "premises", "status", "text")

    def __init__(
        self, order: int, text: str, citations: dict[str, _Citation], premises: list[str]
    ) -> None:
        self.order = order
        self.text = text
        self.citations = citations
        self.premises = premises
        self.status = TRUSTED


class GroundedMemory:
    def __init__(self) -> None:
        self._sources: dict[str, _Source] = {}
        self._claims: dict[str, _Claim] = {}
        self._citing: dict[str, list[str]] = {}
        self._resting: dict[str, list[str]] = {}

    # Level 1
    def add_source(self, source_id: str, text: str) -> str:
        if source_id in self._sources:
            return ""
        self._sources[source_id] = _Source(text)
        self._citing[source_id] = []
        return self._sources[source_id].current()

    def add_claim(self, claim_id: str, text: str, citations: list[list[str]]) -> bool:
        if claim_id in self._claims or not citations:
            return False
        cited: dict[str, _Citation] = {}
        for source_id, given in citations:
            source = self._sources.get(source_id)
            if source is None or source_id in cited or given not in source.last:
                return False
            cited[source_id] = _Citation(given)
        claim = _Claim(len(self._claims), text, cited, [])
        self._claims[claim_id] = claim
        self._resting[claim_id] = []
        for source_id in cited:
            self._citing[source_id].append(claim_id)
        claim.status = self._status_of(claim)
        return True

    def status(self, claim_id: str) -> str:
        claim = self._claims.get(claim_id)
        return "" if claim is None else claim.status

    def evidence(self, claim_id: str) -> list[list[str]]:
        claim = self._claims.get(claim_id)
        if claim is None:
            return []
        return [
            [source_id, claim.citations[source_id].receipt] for source_id in sorted(claim.citations)
        ]

    def citing(self, source_id: str) -> list[str]:
        return sorted(self._citing.get(source_id, []))

    # Level 2
    def update_source(self, source_id: str, text: str) -> list[list[str]]:
        source = self._sources.get(source_id)
        if source is None:
            return []
        if receipt(text) == source.current():
            return []
        source.append(text)
        return self._refresh(self._citing[source_id])

    def history(self, source_id: str) -> list[str]:
        source = self._sources.get(source_id)
        return [] if source is None else list(source.history)

    def drift(self, claim_id: str) -> list[list[str]]:
        claim = self._claims.get(claim_id)
        if claim is None:
            return []
        rows = []
        for source_id in sorted(claim.citations):
            cited, source = claim.citations[source_id].receipt, self._sources[source_id]
            if cited != source.current():
                rows.append([source_id, cited, source.current(), str(source.behind(cited))])
        return rows

    def stale_claims(self) -> list[str]:
        return sorted(claim_id for claim_id, claim in self._claims.items() if claim.status == STALE)

    # Level 3
    def add_derived(self, claim_id: str, text: str, premises: list[str]) -> bool:
        if claim_id in self._claims or not premises:
            return False
        if len(set(premises)) != len(premises) or any(p not in self._claims for p in premises):
            return False
        claim = _Claim(len(self._claims), text, {}, list(premises))
        self._claims[claim_id] = claim
        self._resting[claim_id] = []
        for premise in premises:
            self._resting[premise].append(claim_id)
        claim.status = self._status_of(claim)
        return True

    def verify(self, claim_id: str, source_id: str, phrase: str) -> list[list[str]]:
        claim = self._claims.get(claim_id)
        if claim is None or source_id not in claim.citations:
            return []
        citation, source = claim.citations[source_id], self._sources[source_id]
        if phrase in source.text:
            citation.receipt = source.current()
            citation.refuted = False
        else:
            citation.refuted = True
        return self._refresh([claim_id])

    def dependents(self, claim_id: str) -> list[str]:
        if claim_id not in self._claims:
            return []
        return sorted(self._downstream([claim_id]) - {claim_id})

    # Level 4
    def recall(self, query: str, policy: str, k: int) -> list[list[str]]:
        wanted, usable = words(query), USABLE.get(policy, set())
        found = [
            (RANK[claim.status], claim_id)
            for claim_id, claim in self._claims.items()
            if claim.status in usable and wanted <= words(claim.text)
        ]
        found.sort()
        return [self._row(claim_id) for _, claim_id in found[:k]]

    def report(self) -> list[str]:
        counts = dict.fromkeys(STATUSES, 0)
        for claim in self._claims.values():
            counts[claim.status] += 1
        total = len(self._claims)
        drifted: set[str] = set()
        most_behind = 0
        for claim in self._claims.values():
            for source_id, citation in claim.citations.items():
                source = self._sources[source_id]
                if citation.receipt != source.current():
                    drifted.add(source_id)
                    most_behind = max(most_behind, source.behind(citation.receipt))
        share = "n/a" if total == 0 else f"{counts[TRUSTED] * 100 // total}%"
        return [
            f"claims: {total}",
            *(f"{status}: {counts[status]}" for status in STATUSES),
            f"supported: {share}",
            f"sources: {len(self._sources)}",
            f"drifted sources: {len(drifted)}",
            f"max behind: {most_behind}",
        ]

    # Status upkeep
    def _status_of(self, claim: _Claim) -> str:
        if claim.citations:
            if any(citation.refuted for citation in claim.citations.values()):
                return CONTRADICTED
            for source_id, citation in claim.citations.items():
                if citation.receipt != self._sources[source_id].current():
                    return STALE
            return TRUSTED
        worst = TRUSTED
        for premise in claim.premises:
            inherited = self._claims[premise].status
            if inherited == CONTRADICTED:
                inherited = UNSUPPORTED
            if RANK[inherited] > RANK[worst]:
                worst = inherited
        return worst

    def _downstream(self, seeds: list[str]) -> set[str]:
        reached, stack = set(seeds), list(seeds)
        while stack:
            for dependent in self._resting[stack.pop()]:
                if dependent not in reached:
                    reached.add(dependent)
                    stack.append(dependent)
        return reached

    def _refresh(self, seeds: list[str]) -> list[list[str]]:
        """Recompute the seeds and everything resting on them, premises first: a claim only
        rests on claims added before it, so the order of addition is a topological order."""
        affected = sorted(
            self._downstream(seeds), key=lambda claim_id: self._claims[claim_id].order
        )
        changes = []
        for claim_id in affected:
            claim = self._claims[claim_id]
            before, claim.status = claim.status, self._status_of(claim)
            if claim.status != before:
                changes.append([claim_id, before, claim.status])
        changes.sort()
        return changes

    def _row(self, claim_id: str) -> list[str]:
        claim = self._claims[claim_id]
        row = [claim_id, claim.status, claim.text]
        for source_id in sorted(claim.citations):
            cited = claim.citations[source_id].receipt
            outdated = cited != self._sources[source_id].current()
            row.append(f"{source_id}@{cited}" + (" (outdated)" if outdated else ""))
        for premise in sorted(claim.premises):
            row.append(premise + (" (stale)" if self._claims[premise].status == STALE else ""))
        return row
