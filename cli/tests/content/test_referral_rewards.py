"""referral-rewards promises that its hidden cases catch the classic mistakes of a referral
program: a bonus paid twice for the same person, the last referrer winning instead of the first,
totals that count only direct referrals or the person themself, ties broken the wrong way, loops
and self-referrals accepted, the rules of a row applied in the wrong order, a board that includes
people without referrals or is never refreshed, and a recursion that runs out of stack. These
tests replay every case against a model of the program written from the statement, which must
give every expected output, and against that model with one mistake planted at a time, which some
hidden case must fail. A mistake that crashes fails its case, as a thrown exception does in the
grader."""

import json
import re
from collections import deque
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0314-referral-rewards"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]
COUNTED, REPEAT, RIVAL, LOOP = 0, 1, 2, 3


class Model:
    """The program as the statement words it, one rule per method, so that each mistake below
    overrides a single method. It keeps the counted referrals in order and answers by looking at
    them, with no cache."""

    def __init__(self, bonus: int) -> None:
        self.bonus = bonus
        self.referrer_of: dict[str, str] = {}
        self.counted: list[tuple[str, str]] = []
        self.listed: dict[str, list[str]] = {}

    # --- the rules for a row, in the order of the statement
    def reaches(self, start: str, target: str) -> bool:
        """Whether following the referrals backwards from `start` meets `target`."""
        current = start
        while current in self.referrer_of:
            current = self.referrer_of[current]
            if current == target:
                return True
        return False

    def classify(self, referrer: str, referred: str) -> int:
        if referrer == referred:
            return LOOP
        if referred in self.referrer_of:
            return REPEAT if self.referrer_of[referred] == referrer else RIVAL
        if self.reaches(referrer, referred):
            return LOOP
        return COUNTED

    def list_referral(self, referrer: str, referred: str) -> None:
        self.counted.append((referrer, referred))
        self.listed.setdefault(referrer, []).append(referred)

    def unlist_referral(self, referrer: str, referred: str) -> None:
        self.counted.remove((referrer, referred))
        self.listed[referrer].remove(referred)

    def record(self, referrer: str, referred: str) -> None:
        self.referrer_of[referred] = referrer
        self.list_referral(referrer, referred)

    def apply(self, referrer: str, referred: str) -> int:
        outcome = self.classify(referrer, referred)
        if outcome == COUNTED:
            self.record(referrer, referred)
        return outcome

    def payout(self, outcome: int) -> int:
        return self.bonus if outcome == COUNTED else 0

    # --- level 1
    def refer(self, referrer: str, referred: str) -> int:
        return self.payout(self.apply(referrer, referred))

    def referrals_of(self, person: str) -> list[str]:
        return list(self.listed.get(person, []))

    def points(self, person: str) -> int:
        return len(self.referrals_of(person)) * self.bonus

    # --- level 2
    def below(self, person: str) -> list[str]:
        """Everyone brought in by the person, directly or not."""
        found: list[str] = []
        seen = {person}
        queue = deque(self.referrals_of(person))
        while queue:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            found.append(current)
            queue.extend(self.referrals_of(current))
        return found

    def total_referrals(self, person: str) -> int:
        return len(self.below(person))

    def rank_key(self, person: str) -> Any:
        return (-self.total_referrals(person), -len(self.referrals_of(person)), person)

    def ranked_pool(self) -> list[str]:
        people = {referrer for referrer, _ in self.counted}
        return [person for person in people if self.total_referrals(person) >= 1]

    def ranking(self) -> list[str]:
        return sorted(self.ranked_pool(), key=self.rank_key)

    def top_referrer(self) -> str:
        board = self.ranking()
        return board[0] if board else ""

    # --- level 3
    def refer_all(self, rows: list[list[str]]) -> list[int]:
        tally = [0, 0, 0, 0]
        for referrer, referred in rows:
            tally[self.tally_slot(self.apply(referrer, referred))] += 1
        return tally

    def tally_slot(self, outcome: int) -> int:
        return outcome

    # --- level 4
    def leaderboard(self, k: int) -> list[str]:
        return self.ranking()[:k]


# ------------------------------------------------------------------ level 1 mistakes
class RepeatsPaidAgain(Model):
    """Pays again for a referral that was already counted."""

    def apply(self, referrer: str, referred: str) -> int:
        outcome = super().apply(referrer, referred)
        if outcome == REPEAT:
            self.list_referral(referrer, referred)
        return outcome

    def payout(self, outcome: int) -> int:
        return self.bonus if outcome in (COUNTED, REPEAT) else 0


class RivalsPaid(Model):
    """Pays a second referrer for a person who was already referred."""

    def apply(self, referrer: str, referred: str) -> int:
        outcome = super().apply(referrer, referred)
        if outcome == RIVAL:
            self.list_referral(referrer, referred)
        return outcome

    def payout(self, outcome: int) -> int:
        return self.bonus if outcome in (COUNTED, RIVAL) else 0


class LastReferrerWins(Model):
    """Moves a person to their newest referrer instead of keeping the first."""

    def apply(self, referrer: str, referred: str) -> int:
        outcome = super().apply(referrer, referred)
        if outcome == RIVAL:
            old = self.referrer_of[referred]
            self.unlist_referral(old, referred)
            self.record(referrer, referred)
            return COUNTED
        return outcome


class BonusOncePerReferrer(Model):
    """Pays a referrer a single bonus however many people they bring in."""

    def points(self, person: str) -> int:
        return self.bonus if self.referrals_of(person) else 0


class ReferralsSorted(Model):
    """Lists the referrals by name instead of in the order they were counted."""

    def referrals_of(self, person: str) -> list[str]:
        return sorted(super().referrals_of(person))


class ReferralsListed(Model):
    """Lists a referral again each time it is repeated."""

    def apply(self, referrer: str, referred: str) -> int:
        outcome = super().apply(referrer, referred)
        if outcome == REPEAT:
            self.list_referral(referrer, referred)
        return outcome

    def points(self, person: str) -> int:
        return len(set(self.referrals_of(person))) * self.bonus


class ReferReturnsTheBonusWhenNothingCounts(Model):
    """Answers with the bonus whatever happened."""

    def payout(self, outcome: int) -> int:
        return self.bonus


# ------------------------------------------------------------------ level 2 mistakes
class TotalIsDirectOnly(Model):
    """Counts only the people a person referred themself."""

    def total_referrals(self, person: str) -> int:
        return len(self.referrals_of(person))


class TotalCountsThePerson(Model):
    """Counts the person among the people they brought in."""

    def total_referrals(self, person: str) -> int:
        return super().total_referrals(person) + 1


class TotalStopsAtTwoLevels(Model):
    """Counts the people referred and the people they referred, and no one further down."""

    def below(self, person: str) -> list[str]:
        direct = self.referrals_of(person)
        return direct + [second for first in direct for second in self.referrals_of(first)]


class TopByDirectReferrals(Model):
    """Ranks by direct referrals, not by total."""

    def rank_key(self, person: str) -> Any:
        return (-len(self.referrals_of(person)), person)


class TopTieIgnoresDirectReferrals(Model):
    """Breaks a tie on the total by the name alone."""

    def rank_key(self, person: str) -> Any:
        return (-self.total_referrals(person), person)


class TopTieByLargerName(Model):
    """Breaks the last tie by the larger name."""

    def rank_key(self, person: str) -> Any:
        flipped = [-ord(char) for char in person]
        return (-self.total_referrals(person), -len(self.referrals_of(person)), flipped)


class TopTieByFirstSeen(Model):
    """Keeps the person who was first referring when everything else ties."""

    def rank_key(self, person: str) -> Any:
        first_seen = next(i for i, (referrer, _) in enumerate(self.counted) if referrer == person)
        return (-self.total_referrals(person), -len(self.referrals_of(person)), first_seen)


class TopTieByNameWithoutCase(Model):
    """Compares names without their case."""

    def rank_key(self, person: str) -> Any:
        return (-self.total_referrals(person), -len(self.referrals_of(person)), person.lower())


class TotalsKeptFromTheFirstQuestion(Model):
    """Counts each total once and never again."""

    def __init__(self, bonus: int) -> None:
        super().__init__(bonus)
        self.kept: dict[str, int] = {}

    def total_referrals(self, person: str) -> int:
        if person not in self.kept:
            self.kept[person] = super().total_referrals(person)
        return self.kept[person]


# ------------------------------------------------------------------ level 3 mistakes
class SelfReferralsCount(Model):
    """Lets a person refer themself, once."""

    def classify(self, referrer: str, referred: str) -> int:
        if referrer == referred and referred not in self.referrer_of:
            return COUNTED
        return super().classify(referrer, referred)


class LoopsAreAccepted(Model):
    """Never asks whether a referral closes a loop."""

    def reaches(self, start: str, target: str) -> bool:
        return False


class OnlyTwoPersonLoops(Model):
    """Finds a loop only when the referred person referred the referrer directly."""

    def reaches(self, start: str, target: str) -> bool:
        return self.referrer_of.get(start) == target


class LoopCheckedBeforeRival(Model):
    """Asks whether a referral closes a loop before asking whether the person was referred."""

    def classify(self, referrer: str, referred: str) -> int:
        if referrer == referred:
            return LOOP
        if self.reaches(referrer, referred):
            return LOOP
        if referred in self.referrer_of:
            return REPEAT if self.referrer_of[referred] == referrer else RIVAL
        return COUNTED


class RepeatsCountedAsRivals(Model):
    """Does not tell a repeat from a rival."""

    def tally_slot(self, outcome: int) -> int:
        return RIVAL if outcome == REPEAT else outcome


class RivalsCountedAsRepeats(Model):
    """Reports a second referrer as a repeat."""

    def tally_slot(self, outcome: int) -> int:
        return REPEAT if outcome == RIVAL else outcome


class LoopsCountedAsRivals(Model):
    """Reports a rejected loop as a rival."""

    def tally_slot(self, outcome: int) -> int:
        return RIVAL if outcome == LOOP else outcome


class SummaryInTheWrongOrder(Model):
    """Gives the rivals before the repeats."""

    def refer_all(self, rows: list[list[str]]) -> list[int]:
        counted, repeats, rivals, loops = super().refer_all(rows)
        return [counted, rivals, repeats, loops]


class ReferAllStopsAtTheFirstRejection(Model):
    """Stops reading rows at the first one that does not count."""

    def refer_all(self, rows: list[list[str]]) -> list[int]:
        tally = [0, 0, 0, 0]
        for referrer, referred in rows:
            outcome = self.apply(referrer, referred)
            tally[outcome] += 1
            if outcome != COUNTED:
                break
        return tally


class ReferAllOnlyCountsWhatCounted(Model):
    """Reports the rows that counted and one number for the rest."""

    def refer_all(self, rows: list[list[str]]) -> list[int]:
        counted, repeats, rivals, loops = super().refer_all(rows)
        return [counted, repeats + rivals + loops, 0, 0]


# ------------------------------------------------------------------ level 4 mistakes
class BoardIncludesPeopleWithoutReferrals(Model):
    """Ranks everyone who appears in a counted referral."""

    def ranked_pool(self) -> list[str]:
        return list({person for pair in self.counted for person in pair})


class BoardInReverse(Model):
    """Puts the best person last."""

    def leaderboard(self, k: int) -> list[str]:
        return list(reversed(self.ranking()))[:k]


class BoardOneTooLong(Model):
    """Returns k + 1 names."""

    def leaderboard(self, k: int) -> list[str]:
        return self.ranking()[: k + 1]


class BoardOfZeroIsTheWholeBoard(Model):
    """Treats k = 0 as no limit."""

    def leaderboard(self, k: int) -> list[str]:
        return self.ranking()[:k] if k else self.ranking()


class BoardTieIgnoresDirectReferrals(Model):
    """Breaks a tie on the total by the name alone."""

    def rank_key(self, person: str) -> Any:
        return (-self.total_referrals(person), person)


class BoardKeptFromTheFirstQuestion(Model):
    """Ranks once and answers every later question from that board."""

    def __init__(self, bonus: int) -> None:
        super().__init__(bonus)
        self.kept: list[str] | None = None

    def ranking(self) -> list[str]:
        if self.kept is None:
            self.kept = super().ranking()
        return self.kept


class TotalsByRecursion(Model):
    """Counts the people below by calling itself once per level, so a long chain overflows."""

    def below(self, person: str) -> list[str]:
        found: list[str] = []
        for referred in self.referrals_of(person):
            found.append(referred)
            found.extend(self.below(referred))
        return found


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type(*case["args"][0])
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, StopIteration, RecursionError):
        return False


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_a_hidden_case_holds_a_chain_deeper_than_the_default_recursion_limit():
    longest = max(
        len(arguments[0])
        for case in HIDDEN_CASES
        for op, arguments in zip(case["ops"], case["args"], strict=True)
        if op == "referAll"
    )
    assert longest > 1000


def test_the_generated_case_holds_a_million_referrals():
    generated = [case for case in CASES if "generate" in case]
    assert [case["generate"]["n"] for case in generated] == [1000000]


def test_every_level_has_visible_and_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert any(case.get("visible") for case in at_level)
        assert sum(not case.get("visible") for case in at_level) >= 2
