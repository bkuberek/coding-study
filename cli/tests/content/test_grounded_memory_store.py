"""grounded-memory-store promises that its hidden cases catch the classic mistakes of a memory
that grounds its claims in evidence: receipts hashed from the wrong bytes or cut to the wrong
length, refused claims that leave a trace, staleness kept as a flag that a revert cannot clear or
counted in versions instead of receipts, distances measured from the first version instead of the
last, checks that read the wrong text or refresh the wrong citations, refutations that a source
update erases, contradictions that stop one level down or pass on unchanged, answers cut to k
before they are filtered, and shares rounded the wrong way. These tests replay every case against
a model of the memory written from the statement, which must give every expected output, and
against that model with one mistake planted at a time, which some hidden case must fail. A
mistake that crashes fails its case, as a thrown exception does in the grader."""

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0385-grounded-memory-store"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]

TRUSTED, STALE, UNSUPPORTED, CONTRADICTED = "trusted", "stale", "unsupported", "contradicted"
ORDER = [TRUSTED, STALE, UNSUPPORTED, CONTRADICTED]


@dataclass
class Source:
    texts: list[str]


@dataclass
class Citation:
    source: str
    receipt: str
    refuted: bool = False


@dataclass
class Claim:
    id: str
    text: str
    citations: list[Citation] = field(default_factory=list)
    premises: list[str] = field(default_factory=list)


class Model:
    """The memory as the statement words it. Every text a source has held is kept, and every
    status is worked out again from scratch on each call, top-down through the premises; the
    rows of a change compare a snapshot of every status before it with every status after it."""

    def __init__(self) -> None:
        self.sources: dict[str, Source] = {}
        self.claims: dict[str, Claim] = {}

    # --- receipts
    def receipt(self, text: str) -> str:
        return self.digest(self.text_bytes(text))[: self.receipt_length()]

    def text_bytes(self, text: str) -> bytes:
        return text.encode("utf-8")

    def digest(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def receipt_length(self) -> int:
        return 12

    def receipt_of(self, source_id: str, text: str) -> str:
        return self.receipt(text)

    def receipts(self, source_id: str) -> list[str]:
        return [self.receipt_of(source_id, text) for text in self.sources[source_id].texts]

    def current(self, source_id: str) -> str:
        return self.receipts(source_id)[-1]

    # --- level 1
    def add_source(self, source_id: str, text: str) -> str:
        if source_id in self.sources:
            return self.add_known_source(source_id, text)
        self.sources[source_id] = Source([text])
        return self.current(source_id)

    def add_known_source(self, source_id: str, text: str) -> str:
        return ""

    def claim_id_free(self, claim_id: str) -> bool:
        return claim_id not in self.claims

    def enough(self, pairs: list[Any]) -> bool:
        return len(pairs) > 0

    def held(self, source_id: str) -> list[str]:
        return self.receipts(source_id)

    def receipt_ok(self, source_id: str, given: str) -> bool:
        return given in self.held(source_id)

    def citation_ok(self, source_id: str, given: str, seen: list[str]) -> bool:
        return (
            source_id in self.sources
            and source_id not in seen
            and self.receipt_ok(source_id, given)
        )

    def add_claim(self, claim_id: str, text: str, citations: list[list[str]]) -> bool:
        if not self.claim_id_free(claim_id) or not self.enough(citations):
            return False
        seen: list[str] = []
        for source_id, given in citations:
            if not self.citation_ok(source_id, given, seen):
                return False
            seen.append(source_id)
        self.store(Claim(claim_id, text, [Citation(s, given) for s, given in citations]))
        return True

    def store(self, claim: Claim) -> None:
        self.claims[claim.id] = claim

    def status(self, claim_id: str) -> str:
        return self.status_of(claim_id) if claim_id in self.claims else ""

    def evidence_order(self, citations: list[Citation]) -> list[Citation]:
        return sorted(citations, key=lambda citation: citation.source)

    def evidence(self, claim_id: str) -> list[list[str]]:
        if claim_id not in self.claims:
            return []
        citations = self.evidence_order(self.claims[claim_id].citations)
        return [[citation.source, citation.receipt] for citation in citations]

    def citing_order(self, ids: list[str]) -> list[str]:
        return sorted(ids)

    def citing(self, source_id: str) -> list[str]:
        ids = [
            claim.id
            for claim in self.claims.values()
            if any(citation.source == source_id for citation in claim.citations)
        ]
        return self.citing_order(ids)

    # --- statuses
    def outdated(self, citation: Citation) -> bool:
        return citation.receipt != self.current(citation.source)

    def base_status(self, claim: Claim) -> str:
        if any(citation.refuted for citation in claim.citations):
            return CONTRADICTED
        if any(self.outdated(citation) for citation in claim.citations):
            return STALE
        return TRUSTED

    def inherited(self, status: str) -> str:
        return UNSUPPORTED if status == CONTRADICTED else status

    def derived_status(self, claim: Claim) -> str:
        passed = [self.inherited(self.status_of(premise)) for premise in claim.premises]
        return max(passed, key=ORDER.index)

    def status_of(self, claim_id: str) -> str:
        claim = self.claims[claim_id]
        return self.base_status(claim) if claim.citations else self.derived_status(claim)

    def statuses(self) -> dict[str, str]:
        return {claim_id: self.status_of(claim_id) for claim_id in self.claims}

    def changes(self, before: dict[str, str]) -> list[list[str]]:
        after = self.statuses()
        return [
            [claim_id, before[claim_id], after[claim_id]]
            for claim_id in sorted(before)
            if claim_id in after and before[claim_id] != after[claim_id]
        ]

    # --- level 2
    def new_version(self, source_id: str, text: str) -> bool:
        return self.receipt_of(source_id, text) != self.current(source_id)

    def update_source(self, source_id: str, text: str) -> list[list[str]]:
        if source_id not in self.sources or not self.new_version(source_id, text):
            return []
        before = self.statuses()
        self.sources[source_id].texts.append(text)
        return self.changes(before)

    def history(self, source_id: str) -> list[str]:
        return self.receipts(source_id) if source_id in self.sources else []

    def behind(self, citation: Citation) -> int:
        receipts = self.receipts(citation.source)
        last_seen = max(i for i, found in enumerate(receipts) if found == citation.receipt)
        return len(receipts) - 1 - last_seen

    def drifting(self, citation: Citation) -> bool:
        return self.outdated(citation)

    def drift(self, claim_id: str) -> list[list[str]]:
        if claim_id not in self.claims:
            return []
        return [
            [c.source, c.receipt, self.current(c.source), str(self.behind(c))]
            for c in self.evidence_order(self.claims[claim_id].citations)
            if self.drifting(c)
        ]

    def stale_claims(self) -> list[str]:
        return sorted(claim_id for claim_id, status in self.statuses().items() if status == STALE)

    # --- level 3
    def premises_ok(self, premises: list[str]) -> bool:
        return (
            len(premises) > 0
            and len(set(premises)) == len(premises)
            and all(premise in self.claims for premise in premises)
        )

    def add_derived(self, claim_id: str, text: str, premises: list[str]) -> bool:
        if not self.claim_id_free(claim_id) or not self.premises_ok(premises):
            return False
        self.store(Claim(claim_id, text, [], list(premises)))
        return True

    def citation_of(self, claim_id: str, source_id: str) -> Citation | None:
        claim = self.claims.get(claim_id)
        found = [c for c in claim.citations if c.source == source_id] if claim else []
        return found[0] if found else None

    def checked_text(self, citation: Citation) -> str:
        return self.sources[citation.source].texts[-1]

    def holds(self, citation: Citation, phrase: str) -> bool:
        return phrase in self.checked_text(citation)

    def confirm(self, claim_id: str, citation: Citation) -> None:
        citation.receipt = self.current(citation.source)
        citation.refuted = False

    def refute(self, claim_id: str, citation: Citation) -> None:
        citation.refuted = True

    def verify(self, claim_id: str, source_id: str, phrase: str) -> list[list[str]]:
        citation = self.citation_of(claim_id, source_id)
        if citation is None:
            return []
        before = self.statuses()
        if self.holds(citation, phrase):
            self.confirm(claim_id, citation)
        else:
            self.refute(claim_id, citation)
        return self.verify_changes(claim_id, before)

    def verify_changes(self, claim_id: str, before: dict[str, str]) -> list[list[str]]:
        return self.changes(before)

    def rests_on(self, claim_id: str, target: str) -> bool:
        premises = self.claims[claim_id].premises
        return target in premises or any(self.rests_on(premise, target) for premise in premises)

    def dependents(self, claim_id: str) -> list[str]:
        if claim_id not in self.claims:
            return []
        return sorted(other for other in self.claims if self.rests_on(other, claim_id))

    # --- level 4
    def words(self, text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", text.lower()))

    def query_words(self, query: str) -> set[str]:
        return self.words(query)

    def matches(self, claim: Claim, query: str) -> bool:
        return self.query_words(query) <= self.words(claim.text)

    def usable(self, status: str, policy: str) -> bool:
        return status == TRUSTED or (policy == "lenient" and status == STALE)

    def recall_key(self, claim: Claim) -> Any:
        return (ORDER.index(self.status_of(claim.id)), claim.id)

    def recall(self, query: str, policy: str, k: int) -> list[list[str]]:
        found = [
            claim
            for claim in self.claims.values()
            if self.matches(claim, query) and self.usable(self.status_of(claim.id), policy)
        ]
        return [self.row(claim) for claim in sorted(found, key=self.recall_key)[:k]]

    def citation_entry(self, citation: Citation) -> str:
        warning = " (outdated)" if self.outdated(citation) else ""
        return f"{citation.source}@{citation.receipt}{warning}"

    def premise_entry(self, premise: str) -> str:
        return premise + (" (stale)" if self.status_of(premise) == STALE else "")

    def premise_order(self, premises: list[str]) -> list[str]:
        return sorted(premises)

    def row(self, claim: Claim) -> list[str]:
        entries = [self.citation_entry(c) for c in self.evidence_order(claim.citations)]
        entries += [self.premise_entry(p) for p in self.premise_order(claim.premises)]
        return [claim.id, self.status_of(claim.id), claim.text, *entries]

    def outdated_citations(self) -> list[Citation]:
        return [c for claim in self.claims.values() for c in claim.citations if self.outdated(c)]

    def share(self, counts: dict[str, int]) -> str:
        total = sum(counts.values())
        return "n/a" if total == 0 else f"{counts[TRUSTED] * 100 // total}%"

    def drifted_sources(self) -> int:
        return len({citation.source for citation in self.outdated_citations()})

    def max_behind(self) -> int:
        return max((self.behind(c) for c in self.outdated_citations()), default=0)

    def source_count(self) -> int:
        return len(self.sources)

    def report(self) -> list[str]:
        statuses = self.statuses()
        counts = {status: list(statuses.values()).count(status) for status in ORDER}
        return [
            f"claims: {len(self.claims)}",
            *(f"{status}: {counts[status]}" for status in ORDER),
            f"supported: {self.share(counts)}",
            f"sources: {self.source_count()}",
            f"drifted sources: {self.drifted_sources()}",
            f"max behind: {self.max_behind()}",
        ]


# ------------------------------------------------------------------ level 1 mistakes
class Mistake(Model):
    pass


class HashesTheIdWithTheText(Mistake):
    """Hashes the source id together with the text."""

    def receipt_of(self, source_id: str, text: str) -> str:
        return self.receipt(source_id + text)


class KeepsTheWholeDigest(Mistake):
    """Keeps all 64 characters of the digest."""

    def receipt_length(self) -> int:
        return 64


class UppercaseReceipts(Mistake):
    """Writes the digest in uppercase hexadecimal."""

    def digest(self, data: bytes) -> str:
        return super().digest(data).upper()


class TrimsTheTextBeforeHashing(Mistake):
    """Removes the spaces and line breaks around the text before hashing it."""

    def text_bytes(self, text: str) -> bytes:
        return super().text_bytes(text.strip())


class HashesTheLowByteOfEachCodeUnit(Mistake):
    """Hashes one byte per UTF-16 code unit, as a latin1 or binary encoding does."""

    def text_bytes(self, text: str) -> bytes:
        return text.encode("utf-16-le")[0::2]


class SecondAddSourceReplacesTheText(Mistake):
    """Lets addSource replace the text of a known source."""

    def add_known_source(self, source_id: str, text: str) -> str:
        self.sources[source_id] = Source([text])
        return self.current(source_id)


class RefusedClaimStillIndexed(Mistake):
    """Indexes each citation as it is checked, so a refused claim is still listed by citing."""

    def __init__(self) -> None:
        super().__init__()
        self.leaked: list[tuple[str, str]] = []

    def add_claim(self, claim_id: str, text: str, citations: list[list[str]]) -> bool:
        accepted = super().add_claim(claim_id, text, citations)
        if not accepted and self.claim_id_free(claim_id):
            seen: list[str] = []
            for source_id, given in citations:
                if not self.citation_ok(source_id, given, seen):
                    break
                seen.append(source_id)
                self.leaked.append((source_id, claim_id))
        return accepted

    def citing(self, source_id: str) -> list[str]:
        leaked = [claim_id for source, claim_id in self.leaked if source == source_id]
        return sorted(set(super().citing(source_id)) | set(leaked))


class ReceiptOfAnySourceAccepted(Mistake):
    """Accepts a receipt held by any source, not only by the cited one."""

    def held(self, source_id: str) -> list[str]:
        return [found for source in self.sources for found in self.receipts(source)]


class ReceiptNotChecked(Mistake):
    """Accepts any receipt for a known source."""

    def receipt_ok(self, source_id: str, given: str) -> bool:
        return True


class UnknownSourcesSkipped(Mistake):
    """Drops the citations of unknown sources and keeps the claim."""

    def add_claim(self, claim_id: str, text: str, citations: list[list[str]]) -> bool:
        known = [pair for pair in citations if pair[0] in self.sources]
        return super().add_claim(claim_id, text, known)


class RepeatedSourceAccepted(Mistake):
    """Accepts a claim that cites the same source twice."""

    def citation_ok(self, source_id: str, given: str, seen: list[str]) -> bool:
        return super().citation_ok(source_id, given, [])


class ClaimWithoutCitationsAccepted(Mistake):
    """Accepts a claim with no citations, trusted since none of them is outdated."""

    def enough(self, pairs: list[Any]) -> bool:
        return True

    def derived_status(self, claim: Claim) -> str:
        return super().derived_status(claim) if claim.premises else TRUSTED


class ReusedClaimIdReplaces(Mistake):
    """Lets addClaim replace a claim with the same id."""

    def claim_id_free(self, claim_id: str) -> bool:
        return True


class EvidenceInGivenOrder(Mistake):
    """Returns the citations in the order they were given."""

    def evidence_order(self, citations: list[Citation]) -> list[Citation]:
        return list(citations)


class CitingInOrderOfAddition(Mistake):
    """Lists the claims citing a source in the order they were added."""

    def citing_order(self, ids: list[str]) -> list[str]:
        return list(ids)


# ------------------------------------------------------------------ level 2 mistakes
class VersionCountersInsteadOfReceipts(Mistake):
    """Calls a citation outdated whenever the source got a version after it, even one that
    brought the cited text back."""

    def __init__(self) -> None:
        super().__init__()
        self.stamps: dict[int, int] = {}

    def stamp(self, citation: Citation) -> int:
        if id(citation) not in self.stamps:
            receipts = self.receipts(citation.source)
            self.stamps[id(citation)] = max(
                i for i, found in enumerate(receipts) if found == citation.receipt
            )
        return self.stamps[id(citation)]

    def store(self, claim: Claim) -> None:
        super().store(claim)
        for citation in claim.citations:
            self.stamp(citation)

    def outdated(self, citation: Citation) -> bool:
        return self.stamp(citation) != len(self.sources[citation.source].texts) - 1

    def confirm(self, claim_id: str, citation: Citation) -> None:
        super().confirm(claim_id, citation)
        self.stamps[id(citation)] = len(self.sources[citation.source].texts) - 1


class StaleNeverClears(Mistake):
    """Marks a citation outdated when its source changes and only a check clears the mark."""

    def __init__(self) -> None:
        super().__init__()
        self.marked: set[int] = set()

    def update_source(self, source_id: str, text: str) -> list[list[str]]:
        before = self.statuses()
        if source_id not in self.sources or not self.new_version(source_id, text):
            return []
        self.sources[source_id].texts.append(text)
        for claim in self.claims.values():
            for citation in claim.citations:
                if citation.source == source_id and super().outdated(citation):
                    self.marked.add(id(citation))
        return self.changes(before)

    def outdated(self, citation: Citation) -> bool:
        return id(citation) in self.marked or super().outdated(citation)

    def confirm(self, claim_id: str, citation: Citation) -> None:
        super().confirm(claim_id, citation)
        self.marked.discard(id(citation))


class RepeatedTextStartsAVersion(Mistake):
    """Starts a version even when the text has the current receipt."""

    def new_version(self, source_id: str, text: str) -> bool:
        return True


class BehindFromTheFirstTime(Mistake):
    """Counts the versions since the cited receipt was first current, not last."""

    def behind(self, citation: Citation) -> int:
        receipts = self.receipts(citation.source)
        return len(receipts) - 1 - receipts.index(citation.receipt)


class StaleClaimsForgotten(Mistake):
    """Deletes the claims that a source change makes stale."""

    def update_source(self, source_id: str, text: str) -> list[list[str]]:
        rows = super().update_source(source_id, text)
        for claim_id, status in self.statuses().items():
            if status == STALE:
                del self.claims[claim_id]
        return rows


class EarlierReceiptsRefused(Mistake):
    """Accepts only the receipt of the source's current text."""

    def held(self, source_id: str) -> list[str]:
        return [self.current(source_id)]


class StaleOnlyWhenEveryCitationIsOutdated(Mistake):
    """Calls a claim stale only when all of its citations are outdated."""

    def base_status(self, claim: Claim) -> str:
        if any(citation.refuted for citation in claim.citations):
            return CONTRADICTED
        if all(self.outdated(citation) for citation in claim.citations):
            return STALE
        return TRUSTED


class ChangesListEveryCitingClaim(Mistake):
    """Lists every claim citing the changed source, changed or not."""

    def update_source(self, source_id: str, text: str) -> list[list[str]]:
        if source_id not in self.sources or not self.new_version(source_id, text):
            return []
        before = self.statuses()
        self.sources[source_id].texts.append(text)
        after = self.statuses()
        return [[c, before[c], after[c]] for c in self.citing(source_id)]


class DriftListsCurrentCitations(Mistake):
    """Lists every citation in drift, current ones with 0 versions behind."""

    def drifting(self, citation: Citation) -> bool:
        return True


# ------------------------------------------------------------------ level 3 mistakes
class PhraseMatchIgnoresCase(Mistake):
    """Matches the phrase without regard to case."""

    def holds(self, citation: Citation, phrase: str) -> bool:
        return phrase.lower() in self.checked_text(citation).lower()


class PhraseCheckedAgainstTheCitedText(Mistake):
    """Checks the phrase against the text the citation was formed from."""

    def checked_text(self, citation: Citation) -> str:
        source = self.sources[citation.source]
        receipts = self.receipts(citation.source)
        last_seen = max(i for i, found in enumerate(receipts) if found == citation.receipt)
        return source.texts[last_seen]


class FailedCheckRefreshesTheReceipt(Mistake):
    """Moves a refuted citation to the current receipt."""

    def refute(self, claim_id: str, citation: Citation) -> None:
        super().refute(claim_id, citation)
        citation.receipt = self.current(citation.source)


class CheckRefreshesEveryCitation(Mistake):
    """Refreshes every citation of the claim when one check holds."""

    def confirm(self, claim_id: str, citation: Citation) -> None:
        for each in self.claims[claim_id].citations:
            super().confirm(claim_id, each)


class CheckDoesNotClearARefutation(Mistake):
    """Refreshes the receipt on a check that holds but leaves the citation refuted."""

    def confirm(self, claim_id: str, citation: Citation) -> None:
        citation.receipt = self.current(citation.source)


class SourceUpdateClearsRefutations(Mistake):
    """Clears the refutations of a source's citations when its text changes."""

    def update_source(self, source_id: str, text: str) -> list[list[str]]:
        if source_id not in self.sources or not self.new_version(source_id, text):
            return []
        before = self.statuses()
        self.sources[source_id].texts.append(text)
        for claim in self.claims.values():
            for citation in claim.citations:
                if citation.source == source_id:
                    citation.refuted = False
        return self.changes(before)


class StaleOutranksContradicted(Mistake):
    """Checks for outdated citations before refuted ones."""

    def base_status(self, claim: Claim) -> str:
        if any(self.outdated(citation) for citation in claim.citations):
            return STALE
        return super().base_status(claim)


class ContradictionPassesOnUnchanged(Mistake):
    """Makes a claim resting on a contradicted claim contradicted too."""

    def inherited(self, status: str) -> str:
        return status


class UnsupportedPremiseIgnored(Mistake):
    """Lets only a contradicted premise flag a claim, not an unsupported one."""

    def inherited(self, status: str) -> str:
        return TRUSTED if status == UNSUPPORTED else super().inherited(status)


class StalePremiseIgnored(Mistake):
    """Keeps a claim trusted when a premise is stale."""

    def inherited(self, status: str) -> str:
        return TRUSTED if status == STALE else super().inherited(status)


class OnlyDirectDependentsRecomputed(Mistake):
    """Keeps statuses and recomputes, after a change, only the claims it touches and the claims
    resting on those directly."""

    def __init__(self) -> None:
        super().__init__()
        self.kept: dict[str, str] = {}

    def store(self, claim: Claim) -> None:
        super().store(claim)
        self.kept[claim.id] = super().status_of(claim.id)

    def status_of(self, claim_id: str) -> str:
        return self.kept.get(claim_id, TRUSTED)

    def recompute(self, seeds: list[str]) -> None:
        direct = [c for c in self.claims if any(p in seeds for p in self.claims[c].premises)]
        for claim_id in [*seeds, *direct]:
            claim = self.claims[claim_id]
            self.kept[claim_id] = (
                self.base_status(claim) if claim.citations else self.derived_status(claim)
            )

    def update_source(self, source_id: str, text: str) -> list[list[str]]:
        if source_id not in self.sources or not self.new_version(source_id, text):
            return []
        before = self.statuses()
        self.sources[source_id].texts.append(text)
        self.recompute(self.citing(source_id))
        return self.changes(before)

    def verify_changes(self, claim_id: str, before: dict[str, str]) -> list[list[str]]:
        self.recompute([claim_id])
        return self.changes(before)


class VerifyListsOnlyTheClaim(Mistake):
    """Lists only the checked claim among the changes of verify."""

    def verify_changes(self, claim_id: str, before: dict[str, str]) -> list[list[str]]:
        return [row for row in super().verify_changes(claim_id, before) if row[0] == claim_id]


class DependentsListedOncePerPath(Mistake):
    """Lists a dependent once for every path that reaches it."""

    def dependents(self, claim_id: str) -> list[str]:
        found: list[str] = []
        stack = [claim_id]
        while stack:
            current = stack.pop()
            for other in self.claims.values():
                if current in other.premises:
                    found.append(other.id)
                    stack.append(other.id)
        return sorted(found) if claim_id in self.claims else []


class DependentsIncludeTheClaim(Mistake):
    """Lists the claim among its own dependents."""

    def dependents(self, claim_id: str) -> list[str]:
        found = super().dependents(claim_id)
        return sorted([claim_id, *found]) if claim_id in self.claims else found


class DependentsOnlyDirect(Mistake):
    """Lists only the claims that name the claim as a premise."""

    def rests_on(self, claim_id: str, target: str) -> bool:
        return target in self.claims[claim_id].premises


class UnknownPremiseAccepted(Mistake):
    """Accepts a derived claim with a premise that is not a claim."""

    def premises_ok(self, premises: list[str]) -> bool:
        return len(premises) > 0 and len(set(premises)) == len(premises)

    def status_of(self, claim_id: str) -> str:
        return super().status_of(claim_id) if claim_id in self.claims else TRUSTED

    def rests_on(self, claim_id: str, target: str) -> bool:
        if claim_id not in self.claims:
            return False
        return super().rests_on(claim_id, target)


class RepeatedPremiseAccepted(Mistake):
    """Accepts a derived claim that names a premise twice."""

    def premises_ok(self, premises: list[str]) -> bool:
        return len(premises) > 0 and all(premise in self.claims for premise in premises)


class DerivedWithoutPremisesAccepted(Mistake):
    """Accepts a derived claim with no premises, trusted by default."""

    def premises_ok(self, premises: list[str]) -> bool:
        return len(set(premises)) == len(premises) and all(p in self.claims for p in premises)

    def derived_status(self, claim: Claim) -> str:
        return super().derived_status(claim) if claim.premises else TRUSTED


# ------------------------------------------------------------------ level 4 mistakes
class KeepsKBeforeFiltering(Mistake):
    """Keeps the first k matches, then drops the ones the policy does not allow."""

    def recall(self, query: str, policy: str, k: int) -> list[list[str]]:
        found = sorted(
            (claim for claim in self.claims.values() if self.matches(claim, query)),
            key=lambda claim: claim.id,
        )[:k]
        usable = [claim for claim in found if self.usable(self.status_of(claim.id), policy)]
        return [self.row(claim) for claim in sorted(usable, key=self.recall_key)]


class AnswersSortedByIdOnly(Mistake):
    """Sorts the answers by id, mixing trusted and stale claims."""

    def recall_key(self, claim: Claim) -> Any:
        return claim.id


class StrictAlsoUsesStale(Mistake):
    """Lets the strict policy use stale claims."""

    def usable(self, status: str, policy: str) -> bool:
        return status in (TRUSTED, STALE)


class LenientAlsoUsesUnsupported(Mistake):
    """Lets the lenient policy use unsupported claims."""

    def usable(self, status: str, policy: str) -> bool:
        return super().usable(status, policy) or (policy == "lenient" and status == UNSUPPORTED)


class MatchesSubstrings(Mistake):
    """Matches each query word anywhere in the text, inside other words too."""

    def matches(self, claim: Claim, query: str) -> bool:
        return all(word in claim.text.lower() for word in self.query_words(query))


class QueryCaseKept(Mistake):
    """Splits the query into words without lowercasing it."""

    def query_words(self, query: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", query))


class PremisesInGivenOrder(Mistake):
    """Lists the premises in the order they were given."""

    def premise_order(self, premises: list[str]) -> list[str]:
        return list(premises)


class NoWarningOnOutdatedCitations(Mistake):
    """Writes outdated citations without their warning."""

    def citation_entry(self, citation: Citation) -> str:
        return f"{citation.source}@{citation.receipt}"


class NoWarningOnStalePremises(Mistake):
    """Writes stale premises without their warning."""

    def premise_entry(self, premise: str) -> str:
        return premise


class ShareRoundedToNearest(Mistake):
    """Rounds the share to the nearest percent."""

    def share(self, counts: dict[str, int]) -> str:
        total = sum(counts.values())
        return "n/a" if total == 0 else f"{round(counts[TRUSTED] * 100 / total)}%"


class ShareCountsStaleClaims(Mistake):
    """Counts stale claims as supported."""

    def share(self, counts: dict[str, int]) -> str:
        total = sum(counts.values())
        return "n/a" if total == 0 else f"{(counts[TRUSTED] + counts[STALE]) * 100 // total}%"


class EmptyShareIsZero(Mistake):
    """Reports 0% for an empty memory."""

    def share(self, counts: dict[str, int]) -> str:
        return "0%" if sum(counts.values()) == 0 else super().share(counts)


class DriftedSourcesCountCitations(Mistake):
    """Counts outdated citations instead of the sources they cite."""

    def drifted_sources(self) -> int:
        return len(self.outdated_citations())


class MaxBehindIsTheLongestHistory(Mistake):
    """Reports the versions of the longest history among drifted sources."""

    def max_behind(self) -> int:
        drifted = {citation.source for citation in self.outdated_citations()}
        return max((len(self.sources[s].texts) - 1 for s in drifted), default=0)


class SourcesCountsOnlyCitedOnes(Mistake):
    """Counts only the sources that some claim cites."""

    def source_count(self) -> int:
        return len({c.source for claim in self.claims.values() for c in claim.citations})


MISTAKES: Sequence[type[Model]] = Mistake.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, StopIteration):
        return False


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_receipt_the_statement_gives_for_the_empty_text_is_right():
    statement = (PROBLEM / "problem.md").read_text(encoding="utf-8")
    assert f"The receipt of the empty text is `{Model().receipt('')}`." in statement


def test_a_hidden_case_hashes_text_beyond_ascii_and_with_outer_spaces():
    texts = [
        args[1]
        for case in HIDDEN_CASES
        for op, args in zip(case["ops"], case["args"], strict=True)
        if op in ("addSource", "updateSource")
    ]
    assert any(not text.isascii() for text in texts)
    assert any(text != text.strip() for text in texts)
