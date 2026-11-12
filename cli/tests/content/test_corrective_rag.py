"""corrective-rag promises that its hidden cases catch the classic mistakes of a retriever that
grades what it found: a ranking by the wrong similarity or tie-break, a verdict trusted when it was
never given or kept for the wrong question, a decision table read the wrong way, refined passages
cut at the wrong place, a fallback trusted unchecked, rewrites retried past their bound or chosen
badly, and a grounded answer that packs, counts, cites or refuses wrongly. These tests replay every
case against a model of the retriever written from the statement, which must give every expected
output, and against that model with one mistake planted at a time, which some hidden case must
fail. A mistake that crashes fails its case, as a thrown exception does in the grader."""

import json
import math
import re
from collections.abc import Mapping, Sequence
from fractions import Fraction
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0330-corrective-rag"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]

Piece = tuple[str, str, str]
Attempt = tuple[str, str, int]


class Model:
    """The retriever as the statement words it. Scores are floats, the passages are a list in the
    order they were added, and each rule is a small method, so each mistake overrides one rule."""

    UNGRADED = "irrelevant"
    SKIP_A_MISFIT = False

    def __init__(self) -> None:
        self.passages: list[tuple[str, list[int], str]] = []
        self.queries: dict[str, list[int]] = {}
        self.verdicts: dict[Any, str] = {}
        self.fallbacks: dict[str, list[tuple[str, str]]] = {}
        self.rewrites: dict[str, list[str]] = {}

    # --- level 1
    def add_passage(self, passage_id: str, embedding: list[int], text: str) -> bool:
        if any(known == passage_id for known, _, _ in self.passages):
            return False
        self.passages.append((passage_id, embedding, text))
        return True

    def add_query(self, query: str, embedding: list[int]) -> bool:
        if query in self.queries:
            return False
        self.queries[query] = embedding
        return True

    def add_verdict(self, query: str, item_id: str, verdict: str) -> bool:
        key = self.verdict_key(query, item_id)
        if key in self.verdicts:
            return False
        self.verdicts[key] = verdict
        return True

    def verdict_key(self, query: str, item_id: str) -> Any:
        return (query, item_id)

    def verdict(self, query: str, item_id: str) -> str:
        return self.verdicts.get(self.verdict_key(query, item_id), self.UNGRADED)

    def score(self, query: list[int], passage: list[int]) -> Any:
        query_length = sum(x * x for x in query)
        passage_length = sum(x * x for x in passage)
        if not query_length or not passage_length:
            return None
        dot = sum(a * b for a, b in zip(query, passage, strict=True))
        return dot / (math.sqrt(query_length) * math.sqrt(passage_length))

    def rank_key(self, score: Any, passage_id: str, position: int) -> Any:
        return (-score, passage_id)

    def top(self, query: str, k: int) -> list[str]:
        embedding = self.queries.get(query)
        if embedding is None:
            return []
        ranked = []
        for position, (passage_id, vector, _) in enumerate(self.passages):
            score = self.score(embedding, vector)
            if score is not None:
                ranked.append((self.rank_key(score, passage_id, position), passage_id))
        ranked.sort()
        return [passage_id for _, passage_id in ranked][:k]

    def retrieve(self, query: str, k: int) -> list[list[str]]:
        return [[pid, self.verdict(query, pid)] for pid in self.top(query, k)]

    def keep_relevant(self, query: str, k: int) -> list[str]:
        return [pid for pid, verdict in self.retrieve(query, k) if verdict == "relevant"]

    def verdict_counts(self, query: str, k: int) -> list[int]:
        verdicts = [verdict for _, verdict in self.retrieve(query, k)]
        return [verdicts.count(name) for name in self.count_order()]

    def count_order(self) -> list[str]:
        return ["relevant", "ambiguous", "irrelevant"]

    # --- level 2
    def add_fallback(self, query: str, fallback_id: str, text: str) -> bool:
        items = self.fallbacks.setdefault(self.fallback_key(query), [])
        if any(known == fallback_id for known, _ in items):
            return False
        items.append((fallback_id, text))
        return True

    def fallback_key(self, query: str) -> str:
        return query

    def decision_pool(self, query: str, k: int) -> list[str]:
        return self.top(query, k)

    def decide(self, query: str, k: int) -> str:
        seen = {self.verdict(query, pid) for pid in self.decision_pool(query, k)}
        return self.table()[("relevant" in seen, "ambiguous" in seen)]

    def table(self) -> dict[tuple[bool, bool], str]:
        return {
            (True, False): "keep",
            (True, True): "refine",
            (False, True): "blend",
            (False, False): "fallback",
        }

    def sentences(self, text: str) -> list[str]:
        return [sentence.strip() for sentence in re.findall(r"[^.]*\.", text)]

    def sentence_id(self, passage_id: str, number: int) -> str:
        return f"{passage_id}#{number}"

    def first_sentence_number(self) -> int:
        return 1

    def sentence_kept(self, query: str, sentence_id: str) -> bool:
        return self.verdict(query, sentence_id) == "relevant"

    def refined(self, query: str, passage_id: str, text: str) -> list[Piece]:
        pieces = []
        for number, sentence in enumerate(self.sentences(text), self.first_sentence_number()):
            sentence_id = self.sentence_id(passage_id, number)
            if self.sentence_kept(query, sentence_id):
                pieces.append((sentence_id, passage_id, sentence))
        return pieces

    def pieces(self, query: str, passage_id: str, verdict: str, text: str) -> list[Piece]:
        if verdict == "relevant":
            return [(passage_id, passage_id, text)]
        if verdict == "ambiguous":
            return self.refined(query, passage_id, text)
        return []

    def uses_fallback(self, action: str) -> bool:
        return action in ("blend", "fallback")

    def fallback_pieces(self, query: str) -> list[Piece]:
        return [
            (fid, fid, text)
            for fid, text in self.fallbacks.get(self.fallback_key(query), [])
            if self.verdict(query, fid) == "relevant"
        ]

    def passage_pieces(self, query: str, k: int) -> list[Piece]:
        texts = {pid: text for pid, _, text in self.passages}
        return [
            piece
            for pid in self.top(query, k)
            for piece in self.pieces(query, pid, self.verdict(query, pid), texts[pid])
        ]

    def items(self, query: str, k: int) -> list[Piece]:
        found = self.passage_pieces(query, k)
        if self.uses_fallback(self.decide(query, k)):
            found += self.fallback_pieces(query)
        return found

    def evidence(self, query: str, k: int) -> list[list[str]]:
        return [[item_id, text] for item_id, _, text in self.items(query, k)]

    # --- level 3
    def add_rewrite(self, query: str, rewrite: str) -> bool:
        listed = self.rewrites.setdefault(query, [])
        if rewrite == query or rewrite in listed:
            return False
        listed.append(rewrite)
        return True

    def candidates(self, query: str, max_retries: int) -> list[str]:
        return [query, *self.rewrites.get(query, [])[:max_retries]]

    def evidence_count(self, query: str, k: int) -> int:
        return len(self.items(query, k))

    def enough(self, count: int, need: int) -> bool:
        return count >= need

    def stops_on_success(self) -> bool:
        return True

    def best_of(self, tried: list[Attempt]) -> int:
        best = 0
        for index, (_, _, count) in enumerate(tried):
            if count > tried[best][2]:
                best = index
        return best

    def run(self, query: str, k: int, need: int, max_retries: int) -> tuple[list[Attempt], int]:
        tried: list[Attempt] = []
        winner = None
        for asked in self.candidates(query, max_retries):
            tried.append((asked, self.decide(asked, k), self.evidence_count(asked, k)))
            if winner is None and self.enough(tried[-1][2], need):
                winner = len(tried) - 1
                if self.stops_on_success():
                    break
        return tried, self.best_of(tried) if winner is None else winner

    def attempts(self, query: str, k: int, need: int, max_retries: int) -> list[list[str]]:
        tried, chosen = self.run(query, k, need, max_retries)
        return [
            [asked, action, str(count), "chosen" if index == chosen else "tried"]
            for index, (asked, action, count) in enumerate(tried)
        ]

    # --- level 4
    def tokens(self, text: str) -> int:
        return len(re.findall(r"[a-z0-9]+", text)) + text.count(".")

    def fits(self, tokens: int, remaining: int) -> bool:
        return tokens <= remaining

    def cite(self, item_id: str, source: str) -> str:
        return source

    def searched(self, query: str, k: int, need: int, max_retries: int) -> str:
        tried, chosen = self.run(query, k, need, max_retries)
        return tried[chosen][0]

    def packed(self, query: str, k: int, need: int, max_retries: int, budget: int) -> list[Piece]:
        searched = self.searched(query, k, need, max_retries)
        kept: list[Piece] = []
        remaining = budget
        for item_id, source, text in self.items(searched, k):
            tokens = self.tokens(text)
            if not self.fits(tokens, remaining):
                if self.SKIP_A_MISFIT:
                    continue
                break
            remaining -= tokens
            kept.append((self.cite(item_id, source), str(tokens), text))
        return kept

    def numbers(self, cites: list[str]) -> list[int]:
        order: list[str] = []
        for cite in cites:
            if cite not in order:
                order.append(cite)
        return [order.index(cite) + 1 for cite in cites]

    def grounded_context(
        self, query: str, k: int, need: int, max_retries: int, budget: int
    ) -> list[list[str]]:
        kept = self.packed(query, k, need, max_retries, budget)
        numbers = self.numbers([cite for cite, _, _ in kept])
        return [
            [str(number), cite, tokens, text]
            for number, (cite, tokens, text) in zip(numbers, kept, strict=True)
        ]

    def support(self, rows: list[list[str]], query: str, k: int, need: int, retries: int) -> int:
        return len({cite for _, cite, _, _ in rows})

    def supported(self, support: int, minimum: int) -> bool:
        return support >= minimum

    def question_line(self, query: str, searched: str) -> str:
        return f"question: {query}"

    def answer(
        self, query: str, k: int, need: int, max_retries: int, budget: int, min_support: int
    ) -> str:
        rows = self.grounded_context(query, k, need, max_retries, budget)
        support = self.support(rows, query, k, need, max_retries)
        if not self.supported(support, min_support):
            return f"not enough evidence: {support} of {min_support} sources"
        searched = self.searched(query, k, need, max_retries)
        lines = [self.question_line(query, searched), f"searched: {searched}"]
        lines += [f"[{number}] {text}" for number, _, _, text in rows]
        sources: list[str] = []
        for number, cite, _, _ in rows:
            entry = f"[{number}] {cite}"
            if entry not in sources:
                sources.append(entry)
        lines.append("sources: " + ", ".join(sources))
        return "\n".join(lines)


# ------------------------------------------------------------------ correct variants
class CosineFromTheSquareRootOfTheProduct(Model):
    """Computes the cosine as dot / sqrt(|q|^2 * |p|^2), which rounds differently."""

    def score(self, query: list[int], passage: list[int]) -> Any:
        query_length = sum(x * x for x in query)
        passage_length = sum(x * x for x in passage)
        if not query_length or not passage_length:
            return None
        dot = sum(a * b for a, b in zip(query, passage, strict=True))
        return dot / math.sqrt(query_length * passage_length)


class CosineComparedExactly(Model):
    """Orders by the exact fraction dot * |dot| / |p|^2, with no rounding at all."""

    def score(self, query: list[int], passage: list[int]) -> Any:
        passage_length = sum(x * x for x in passage)
        if not any(query) or not passage_length:
            return None
        dot = sum(a * b for a, b in zip(query, passage, strict=True))
        return Fraction(dot * abs(dot), passage_length)


CORRECT_VARIANTS: Sequence[type[Model]] = [
    Model,
    CosineFromTheSquareRootOfTheProduct,
    CosineComparedExactly,
]


# ------------------------------------------------------------------ level 1 mistakes
class Mistake(Model):
    pass


class TiesGoToTheLargerId(Mistake):
    """Breaks equal scores by the larger id."""

    def rank_key(self, score: Any, passage_id: str, position: int) -> Any:
        return (-score, [-ord(c) for c in passage_id])


class TiesGoToTheFirstAdded(Mistake):
    """Breaks equal scores by the order the passages were added."""

    def rank_key(self, score: Any, passage_id: str, position: int) -> Any:
        return (-score, position)


class RankedByTheDotProduct(Mistake):
    """Ranks by the dot product, so a long vector beats a well-aimed one."""

    def score(self, query: list[int], passage: list[int]) -> Any:
        if not any(query) or not any(passage):
            return None
        return sum(a * b for a, b in zip(query, passage, strict=True))


class RankedByDistance(Mistake):
    """Ranks by the Euclidean distance between the vectors, nearest first."""

    def score(self, query: list[int], passage: list[int]) -> Any:
        if not any(query) or not any(passage):
            return None
        return -math.dist(query, passage)


class NegativeScoresDropped(Mistake):
    """Leaves out the passages that point away from the query."""

    def score(self, query: list[int], passage: list[int]) -> Any:
        score = super().score(query, passage)
        return None if score is None or score < 0 else score


class ZeroPassageScoresZero(Mistake):
    """Gives a passage with no direction a score of 0 instead of skipping it."""

    def score(self, query: list[int], passage: list[int]) -> Any:
        if any(query) and not any(passage):
            return 0.0
        return super().score(query, passage)


class ZeroQueryRanksEverything(Mistake):
    """Gives every passage a score of 0 for a query with no direction."""

    def score(self, query: list[int], passage: list[int]) -> Any:
        if not any(query) and any(passage):
            return 0.0
        return super().score(query, passage)


class OneMorePassageThanK(Mistake):
    """Returns k + 1 passages."""

    def top(self, query: str, k: int) -> list[str]:
        return super().top(query, k + 1)


class UngradedCountsAsAmbiguous(Mistake):
    """Treats a passage nobody graded as ambiguous."""

    UNGRADED = "ambiguous"


class LaterVerdictReplaces(Mistake):
    """Lets a second verdict replace the first."""

    def add_verdict(self, query: str, item_id: str, verdict: str) -> bool:
        fresh = (query, item_id) not in self.verdicts
        self.verdicts[(query, item_id)] = verdict
        return fresh


class VerdictIgnoresTheQuery(Mistake):
    """Keeps one verdict per passage, whatever the question."""

    def verdict_key(self, query: str, item_id: str) -> Any:
        return item_id


class RepeatedPassageReplaces(Mistake):
    """Replaces a passage that is added again."""

    def add_passage(self, passage_id: str, embedding: list[int], text: str) -> bool:
        fresh = all(known != passage_id for known, _, _ in self.passages)
        self.passages = [entry for entry in self.passages if entry[0] != passage_id]
        self.passages.append((passage_id, embedding, text))
        return fresh


class RepeatedQueryReplaces(Mistake):
    """Replaces the embedding of a query that is added again."""

    def add_query(self, query: str, embedding: list[int]) -> bool:
        fresh = query not in self.queries
        self.queries[query] = embedding
        return fresh


class CountsFromIrrelevantUp(Mistake):
    """Gives the counts in the order irrelevant, ambiguous, relevant."""

    def count_order(self) -> list[str]:
        return ["irrelevant", "ambiguous", "relevant"]


# ------------------------------------------------------------------ level 2 mistakes
class FallbackEvenWhenSomethingIsRelevant(Mistake):
    """Adds the fallback items whatever the decision."""

    def uses_fallback(self, action: str) -> bool:
        return True


class BlendSkipsTheFallback(Mistake):
    """Falls back only when no passage is relevant or ambiguous."""

    def uses_fallback(self, action: str) -> bool:
        return action == "fallback"


class BlendIsCalledRefine(Mistake):
    """Calls the ambiguous-only case refine."""

    def table(self) -> dict[tuple[bool, bool], str]:
        return {**super().table(), (False, True): "refine"}


class DecisionOverEveryPassage(Mistake):
    """Decides from the verdicts of every passage, not only the top k."""

    def decision_pool(self, query: str, k: int) -> list[str]:
        return self.top(query, len(self.passages))


class AmbiguousPassageKeptWhole(Mistake):
    """Keeps an ambiguous passage whole instead of refining it."""

    def pieces(self, query: str, passage_id: str, verdict: str, text: str) -> list[Piece]:
        if verdict == "ambiguous":
            return [(passage_id, passage_id, text)]
        return super().pieces(query, passage_id, verdict, text)


class SentencesNumberedFromZero(Mistake):
    """Numbers the sentences from 0."""

    def first_sentence_number(self) -> int:
        return 0


class SentenceLosesItsPeriod(Mistake):
    """Splits on the periods and drops them."""

    def sentences(self, text: str) -> list[str]:
        return [piece.strip() for piece in text.split(".") if piece.strip()]


class AmbiguousSentenceKept(Mistake):
    """Keeps every sentence that is not graded irrelevant."""

    def sentence_kept(self, query: str, sentence_id: str) -> bool:
        return self.verdicts.get((query, sentence_id), "irrelevant") != "irrelevant"


class IrrelevantPassagesRefinedToo(Mistake):
    """Looks for relevant sentences in irrelevant passages as well."""

    def pieces(self, query: str, passage_id: str, verdict: str, text: str) -> list[Piece]:
        if verdict == "irrelevant":
            return self.refined(query, passage_id, text)
        return super().pieces(query, passage_id, verdict, text)


class RelevantPassagesSplitToo(Mistake):
    """Keeps only the relevant sentences of a relevant passage."""

    def pieces(self, query: str, passage_id: str, verdict: str, text: str) -> list[Piece]:
        if verdict == "relevant":
            return self.refined(query, passage_id, text)
        return super().pieces(query, passage_id, verdict, text)


class SentencesAfterThePassages(Mistake):
    """Lists the whole passages first and the kept sentences after them."""

    def passage_pieces(self, query: str, k: int) -> list[Piece]:
        pieces = super().passage_pieces(query, k)
        return sorted(pieces, key=lambda piece: "#" in piece[0])


class FallbackTrustedUnchecked(Mistake):
    """Uses every fallback item, whatever its verdict."""

    def fallback_pieces(self, query: str) -> list[Piece]:
        return [(fid, fid, text) for fid, text in self.fallbacks.get(query, [])]


class FallbackSortedById(Mistake):
    """Lists the fallback items by id instead of in the order they were added."""

    def fallback_pieces(self, query: str) -> list[Piece]:
        return sorted(super().fallback_pieces(query))


class FallbacksSharedByEveryQuery(Mistake):
    """Keeps one list of fallback items for all questions."""

    def fallback_key(self, query: str) -> str:
        return ""


class RepeatedFallbackReplaces(Mistake):
    """Replaces the text of a fallback item that is added again."""

    def add_fallback(self, query: str, fallback_id: str, text: str) -> bool:
        items = self.fallbacks.setdefault(query, [])
        fresh = all(known != fallback_id for known, _ in items)
        self.fallbacks[query] = [item for item in items if item[0] != fallback_id]
        self.fallbacks[query].append((fallback_id, text))
        return fresh


# ------------------------------------------------------------------ level 3 mistakes
class LastAttemptIsChosen(Mistake):
    """Chooses the last attempt when none has enough evidence."""

    def best_of(self, tried: list[Attempt]) -> int:
        return len(tried) - 1


class TiesGoToTheLaterAttempt(Mistake):
    """Chooses the later of two attempts with the same evidence."""

    def best_of(self, tried: list[Attempt]) -> int:
        best = 0
        for index, (_, _, count) in enumerate(tried):
            if count >= tried[best][2]:
                best = index
        return best


class TriesEveryRewrite(Mistake):
    """Goes on through the rewrites after one has enough evidence."""

    def stops_on_success(self) -> bool:
        return False


class OneRetryTooMany(Mistake):
    """Tries one rewrite more than the bound."""

    def candidates(self, query: str, max_retries: int) -> list[str]:
        return super().candidates(query, max_retries + 1)


class OneRetryTooFew(Mistake):
    """Tries one rewrite fewer than the bound."""

    def candidates(self, query: str, max_retries: int) -> list[str]:
        return super().candidates(query, max(0, max_retries - 1))


class RewriteMayRepeatTheQuery(Mistake):
    """Accepts the query itself as one of its rewrites."""

    def add_rewrite(self, query: str, rewrite: str) -> bool:
        listed = self.rewrites.setdefault(query, [])
        if rewrite in listed:
            return False
        listed.append(rewrite)
        return True


class RepeatedRewriteAccepted(Mistake):
    """Accepts a rewrite that is already listed, which is then tried twice."""

    def add_rewrite(self, query: str, rewrite: str) -> bool:
        if rewrite == query:
            return False
        self.rewrites.setdefault(query, []).append(rewrite)
        return True


class EnoughMeansMoreThanNeed(Mistake):
    """Asks for more evidence than `need`."""

    def enough(self, count: int, need: int) -> bool:
        return count > need


class CountsOnlyWholePassages(Mistake):
    """Counts the relevant passages and ignores sentences and fallback items."""

    def evidence_count(self, query: str, k: int) -> int:
        return sum(
            "#" not in item and item in {p for p, _, _ in self.passages}
            for item, _, _ in self.items(query, k)
        )


class FollowsRewritesOfRewrites(Mistake):
    """Also tries the rewrites of each rewrite."""

    def candidates(self, query: str, max_retries: int) -> list[str]:
        order = [query]
        for asked in order:
            for rewrite in self.rewrites.get(asked, []):
                if rewrite not in order:
                    order.append(rewrite)
        return order[: max_retries + 1]


# ------------------------------------------------------------------ level 4 mistakes
class SkipsAMisfitAndGoesOn(Mistake):
    """Skips an item that does not fit and tries the next."""

    SKIP_A_MISFIT = True


class TokensAreWords(Mistake):
    """Counts the words only."""

    def tokens(self, text: str) -> int:
        return len(text.split())


class TokensAreCharactersOverFour(Mistake):
    """Counts the characters in groups of 4, rounded up."""

    def tokens(self, text: str) -> int:
        return -(-len(text) // 4)


class FitNeedsRoomToSpare(Mistake):
    """Takes an item only when it leaves some budget over."""

    def fits(self, tokens: int, remaining: int) -> bool:
        return tokens < remaining


class CitesTheSentence(Mistake):
    """Cites a sentence by its own id instead of its passage."""

    def cite(self, item_id: str, source: str) -> str:
        return item_id


class NumbersEveryItem(Mistake):
    """Gives every item a number of its own."""

    def numbers(self, cites: list[str]) -> list[int]:
        return list(range(1, len(cites) + 1))


class SupportCountsItems(Mistake):
    """Counts the items of the context as the support."""

    def support(self, rows: list[list[str]], query: str, k: int, need: int, retries: int) -> int:
        return len(rows)


class SupportCountsAllEvidence(Mistake):
    """Counts the sources of all the evidence, packed or not."""

    def support(self, rows: list[list[str]], query: str, k: int, need: int, retries: int) -> int:
        searched = self.searched(query, k, need, retries)
        return len({source for _, source, _ in self.items(searched, k)})


class SupportMustExceedTheMinimum(Mistake):
    """Refuses when the support only equals the minimum."""

    def supported(self, support: int, minimum: int) -> bool:
        return support > minimum


class QuestionLineShowsTheSearch(Mistake):
    """Prints the rewrite that was searched as the question."""

    def question_line(self, query: str, searched: str) -> str:
        return f"question: {searched}"


class ContextFromTheOriginalQuery(Mistake):
    """Packs the evidence of the original query, whichever attempt was chosen."""

    def searched(self, query: str, k: int, need: int, max_retries: int) -> str:
        return query


MISTAKES: Sequence[type[Model]] = Mistake.__subclasses__()


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
    except (IndexError, KeyError, ValueError, TypeError, ZeroDivisionError, StopIteration):
        return False


@pytest.mark.parametrize("variant", CORRECT_VARIANTS, ids=lambda variant: variant.__name__)
@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_every_correct_model_gives_every_expected_output(case, variant):
    assert outputs(variant, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_every_embedding_of_a_case_has_one_length_and_small_numbers():
    for case in SCRIPTED_CASES:
        vectors = [
            arguments[-1] if op == "addQuery" else arguments[1]
            for op, arguments in zip(case["ops"], case["args"], strict=True)
            if op in ("addPassage", "addQuery")
        ]
        assert len({len(vector) for vector in vectors}) == 1, case["id"]
        assert all(1 <= len(vector) <= 8 for vector in vectors)
        assert all(-100 <= value <= 100 for vector in vectors for value in vector)
