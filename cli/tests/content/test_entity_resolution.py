"""entity-resolution promises that its hidden cases catch the classic mistakes of matching records:
a name cleaned in the wrong order, a Jaro-Winkler with a wrong window, rounding or boost, blocking
that is too wide or too narrow, a score that ignores the email or treats two empty emails as equal,
a grouping that follows chains of matches without the guard or with the wrong order, a canonical
record chosen by the wrong key, and measures with the wrong convention for empty pair sets. These
tests replay every case against a model of the resolver written from the statement, which must give
every expected output, and against that model with one mistake planted at a time, which some hidden
case must fail. A mistake that crashes fails its case, as a thrown exception does in the grader.
They also check the promise of the statement that no decision rests on a score within 1e-9 of a
threshold."""

import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from itertools import combinations
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0320-entity-resolution"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]
FLOAT_METHODS = {"jaroWinkler", "tokenJaccard", "similarity", "pairwiseScores", "bcubedScores"}
TOLERANCE = 1e-6


class Model:
    """The resolver as the statement words it. Each mistake below changes one constant or one
    method. Records are kept in the order they were added, and groups are plain sets."""

    TITLES = ("mr", "mrs", "ms", "miss", "dr", "prof")
    KEY_LENGTH = 3
    WEIGHT_JARO = 0.7
    MATCH = 0.75
    FLOOR = 0.65
    SCALE = 0.1
    PREFIX_CAP = 4
    BOOST_ABOVE: float | None = None
    REUSE_CHARACTERS = False

    def __init__(self) -> None:
        self.rows: dict[str, tuple[str, str]] = {}

    # --- level 1
    def clean_comma(self, text: str) -> str:
        parts = text.split(",")
        return parts[1] + " " + parts[0] if len(parts) == 2 else text

    def clean_marks(self, text: str) -> str:
        return re.sub(r"[^a-z0-9 ]", " ", text.replace("'", ""))

    def drop_title(self, tokens: list[str]) -> list[str]:
        if len(tokens) > 1 and tokens[0] in self.TITLES:
            return tokens[1:]
        return tokens

    def normalize_name(self, name: str) -> str:
        text = self.clean_marks(self.clean_comma(name.lower()))
        return " ".join(self.drop_title(text.split()))

    def normalize_email(self, email: str) -> str:
        return email.strip(" ").lower()

    def add_record(self, record_id: str, name: str, email: str) -> bool:
        if record_id in self.rows:
            return False
        self.rows[record_id] = (self.normalize_name(name), self.normalize_email(email))
        return True

    def normalized(self, record_id: str) -> list[str]:
        return list(self.rows[record_id]) if record_id in self.rows else []

    def group_key(self, row: tuple[str, str]) -> tuple[str, str]:
        return row

    def groupable(self, row: tuple[str, str]) -> bool:
        return row != ("", "")

    def smallest_group(self) -> int:
        return 2

    def exact_groups(self) -> list[list[str]]:
        buckets: dict[tuple[str, str], list[str]] = defaultdict(list)
        for record_id, row in self.rows.items():
            if self.groupable(row):
                buckets[self.group_key(row)].append(record_id)
        return sorted(sorted(ids) for ids in buckets.values() if len(ids) >= self.smallest_group())

    # --- level 2
    def keys_of(self, row: tuple[str, str]) -> set[str]:
        name, email = row
        keys = set()
        if name:
            keys.add("n:" + name.split()[-1][: self.KEY_LENGTH])
        if email:
            keys.add("e:" + email)
        return keys

    def blocking_keys(self, record_id: str) -> list[str]:
        return sorted(self.keys_of(self.rows[record_id])) if record_id in self.rows else []

    def comparable(self, first: str, second: str) -> bool:
        return bool(self.keys_of(self.rows[first]) & self.keys_of(self.rows[second]))

    def candidate_pairs(self) -> list[list[str]]:
        ids = sorted(self.rows)
        return [[a, b] for a, b in combinations(ids, 2) if self.comparable(a, b)]

    def window(self, first_length: int, second_length: int) -> int:
        return max(0, max(first_length, second_length) // 2 - 1)

    def transpositions(self, differing: int) -> float:
        return differing / 2

    def common_prefix(self, first: str, second: str) -> int:
        count = 0
        for a, b in zip(first[: self.PREFIX_CAP], second, strict=False):
            if a != b:
                break
            count += 1
        return count

    def both_empty(self) -> float:
        return 0.0

    def jaro_winkler(self, first: str, second: str) -> float:
        if not first or not second:
            return self.both_empty() if not first and not second else 0.0
        reach = self.window(len(first), len(second))
        free = list(range(len(second)))
        found: list[tuple[int, int]] = []
        for i, char in enumerate(first):
            for j in free:
                if abs(i - j) <= reach and second[j] == char:
                    found.append((i, j))
                    if not self.REUSE_CHARACTERS:
                        free.remove(j)
                    break
        count = len(found)
        if count == 0:
            return 0.0
        in_first = [first[i] for i, _ in found]
        in_second = [second[j] for j in sorted({j for _, j in found})]
        in_second = in_second if not self.REUSE_CHARACTERS else [second[j] for _, j in found]
        differing = sum(a != b for a, b in zip(in_first, in_second, strict=True))
        moved = self.transpositions(differing)
        jaro = (count / len(first) + count / len(second) + (count - moved) / count) / 3
        if self.BOOST_ABOVE is not None and jaro <= self.BOOST_ABOVE:
            return jaro
        return jaro + self.common_prefix(first, second) * self.SCALE * (1 - jaro)

    def tokens(self, text: str) -> Any:
        return set(text.split())

    def empty_overlap(self) -> float:
        return 0.0

    def token_jaccard(self, first: str, second: str) -> float:
        left, right = self.tokens(first), self.tokens(second)
        if not left and not right:
            return self.empty_overlap()
        both = sum(1 for token in left if token in right)
        either = len(left) + len(right) - both
        return both / either

    def same_email(self, first: tuple[str, str], second: tuple[str, str]) -> bool:
        return first[1] != "" and first[1] == second[1]

    def score(self, first: tuple[str, str], second: tuple[str, str]) -> float:
        if self.same_email(first, second):
            return 1.0
        if not first[0] or not second[0]:
            return 0.0
        return self.WEIGHT_JARO * self.jaro_winkler(first[0], second[0]) + (
            1 - self.WEIGHT_JARO
        ) * self.token_jaccard(first[0], second[0])

    def similarity(self, first: str, second: str) -> float:
        if first not in self.rows or second not in self.rows:
            return 0.0
        low, high = sorted((first, second))
        return self.score(self.rows[low], self.rows[high])

    def is_match(self, first: str, second: str) -> bool:
        return (
            first in self.rows
            and second in self.rows
            and self.similarity(first, second) >= self.MATCH
        )

    def matches(self) -> list[list[str]]:
        return [pair for pair in self.candidate_pairs() if self.is_match(*pair)]

    # --- level 3
    def finish(self, groups: Any) -> list[list[str]]:
        return sorted(sorted(group) for group in groups)

    def components(self) -> list[list[str]]:
        groups = [{record_id} for record_id in self.rows]
        for first, second in self.matches():
            one = next(g for g in groups if first in g)
            other = next(g for g in groups if second in g)
            if one is not other:
                groups.remove(other)
                one |= other
        return self.finish(groups)

    def edges(self) -> list[list[str]]:
        return sorted(self.matches(), key=lambda pair: (-self.similarity(*pair), *pair))

    def may_merge(self, one: set[str], other: set[str]) -> bool:
        return all(self.similarity(a, b) >= self.FLOOR for a in one for b in other)

    def cluster_sets(self) -> list[set[str]]:
        groups = [{record_id} for record_id in self.rows]
        for first, second in self.edges():
            one = next(g for g in groups if first in g)
            other = next(g for g in groups if second in g)
            if one is not other and self.may_merge(one, other):
                groups.remove(other)
                one |= other
        return groups

    def clusters(self) -> list[list[str]]:
        return self.finish(self.cluster_sets())

    def entity(self, record_id: str) -> set[str]:
        if record_id not in self.rows:
            return set()
        return next(group for group in self.cluster_sets() if record_id in group)

    def canonical_key(self, record_id: str) -> tuple[Any, ...]:
        name, email = self.rows[record_id]
        return (-(bool(name) + bool(email)), -len(name), record_id)

    def canonical(self, record_id: str) -> str:
        group = self.entity(record_id)
        return min(group, key=self.canonical_key) if group else ""

    def alias_pool(self, group: set[str]) -> set[str]:
        return {self.rows[member][0] for member in group}

    def aliases(self, record_id: str) -> list[str]:
        group = self.entity(record_id)
        if not group:
            return []
        keeper = self.rows[self.canonical(record_id)][0]
        return sorted(self.alias_pool(group) - {keeper, ""})

    # --- level 4
    def pair_set(self, groups: list[list[str]]) -> set[tuple[str, str]]:
        return {pair for group in groups for pair in combinations(sorted(group), 2)}

    def harmonic(self, precision: float, recall: float) -> float:
        return 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    def empty_precision(self) -> float:
        return 1.0

    def empty_recall(self) -> float:
        return 1.0

    def pairwise_scores(self, predicted: list[list[str]], gold: list[list[str]]) -> list[float]:
        guess, truth = self.pair_set(predicted), self.pair_set(gold)
        both = len(guess & truth)
        precision = both / len(guess) if guess else self.empty_precision()
        recall = both / len(truth) if truth else self.empty_recall()
        return [precision, recall, self.harmonic(precision, recall)]

    def record_overlaps(
        self, predicted: list[list[str]], gold: list[list[str]]
    ) -> list[tuple[float, float]]:
        guess = {i: set(group) for group in predicted for i in group}
        truth = {i: set(group) for group in gold for i in group}
        return [
            (len(guess[i] & truth[i]) / len(guess[i]), len(guess[i] & truth[i]) / len(truth[i]))
            for i in sorted(truth)
        ]

    def bcubed_scores(self, predicted: list[list[str]], gold: list[list[str]]) -> list[float]:
        overlaps = self.record_overlaps(predicted, gold)
        precision = sum(p for p, _ in overlaps) / len(overlaps)
        recall = sum(r for _, r in overlaps) / len(overlaps)
        return [precision, recall, self.harmonic(precision, recall)]

    def error_labels(self) -> tuple[str, str]:
        return "false-merge", "missed"

    def error_order(self, rows: list[list[str]]) -> list[list[str]]:
        return sorted(rows)

    def pair_errors(self, predicted: list[list[str]], gold: list[list[str]]) -> list[list[str]]:
        guess, truth = self.pair_set(predicted), self.pair_set(gold)
        extra, lost = self.error_labels()
        rows = [[extra, *pair] for pair in guess - truth] + [
            [lost, *pair] for pair in truth - guess
        ]
        return self.error_order(rows)


# ------------------------------------------------------------------ level 1 mistakes
class SwapsOnTheFirstComma(Model):
    """Swaps around the first comma even when there are more."""

    def clean_comma(self, text: str) -> str:
        if "," in text:
            before, after = text.split(",", 1)
            return after + " " + before
        return text


class TitleBeforeTheSwap(Model):
    """Looks for the title in the text as written, before the comma is swapped."""

    def normalize_name(self, name: str) -> str:
        tokens = self.clean_marks(name.lower()).replace(",", " ").split()
        first = self.drop_title(tokens)
        return " ".join(
            self.drop_title(self.clean_marks(self.clean_comma(" ".join(first))).split())
        )


class EveryLeadingTitleDropped(Model):
    """Drops titles for as long as the first token is one."""

    def drop_title(self, tokens: list[str]) -> list[str]:
        while len(tokens) > 1 and tokens[0] in self.TITLES:
            tokens = tokens[1:]
        return tokens


class LoneTitleDropped(Model):
    """Drops a title even when nothing else remains."""

    def drop_title(self, tokens: list[str]) -> list[str]:
        return tokens[1:] if tokens and tokens[0] in self.TITLES else tokens


class MoreTitlesRecognised(Model):
    """Also treats professor and mister as titles."""

    TITLES = (*Model.TITLES, "professor", "mister", "sir")


class ApostropheBecomesASpace(Model):
    """Splits o'brien into two words."""

    def clean_marks(self, text: str) -> str:
        return re.sub(r"[^a-z0-9 ]", " ", text)


class HyphenIsDeleted(Model):
    """Joins mary-jane into one word."""

    def clean_marks(self, text: str) -> str:
        return re.sub(r"[^a-z0-9 ]", " ", text.replace("'", "").replace("-", ""))


class DigitsAreDropped(Model):
    """Keeps letters only."""

    def clean_marks(self, text: str) -> str:
        return re.sub(r"[^a-z ]", " ", text.replace("'", ""))


class EmailNotTrimmed(Model):
    """Lower-cases the email and leaves spaces at its ends."""

    def normalize_email(self, email: str) -> str:
        return email.lower()


class EmailLosesAllSpaces(Model):
    """Removes the spaces inside an email too."""

    def normalize_email(self, email: str) -> str:
        return email.replace(" ", "").lower()


class EmailLosesItsTag(Model):
    """Cuts the +tag of the local part."""

    def normalize_email(self, email: str) -> str:
        return re.sub(r"\+[^@]*", "", email.strip(" ").lower())


class ReusedIdOverwrites(Model):
    """Replaces the stored record when the id is used again."""

    def add_record(self, record_id: str, name: str, email: str) -> bool:
        if record_id in self.rows:
            self.rows[record_id] = (self.normalize_name(name), self.normalize_email(email))
            return False
        return super().add_record(record_id, name, email)


class ExactGroupsByNameOnly(Model):
    """Groups records that have the same name, whatever the email."""

    def group_key(self, row: tuple[str, str]) -> tuple[str, str]:
        return (row[0], "")


class ExactGroupsKeepEmptyRecords(Model):
    """Groups the records that have nothing left after cleaning."""

    def groupable(self, row: tuple[str, str]) -> bool:
        return True


class ExactGroupsKeepSingletons(Model):
    """Lists records that are alone as groups of one."""

    def smallest_group(self) -> int:
        return 1


# ------------------------------------------------------------------ level 2 mistakes
class NameKeyFromTheFirstToken(Model):
    """Builds the name key from the first token."""

    def keys_of(self, row: tuple[str, str]) -> set[str]:
        keys = super().keys_of(row)
        keys = {key for key in keys if not key.startswith("n:")}
        if row[0]:
            keys.add("n:" + row[0].split()[0][: self.KEY_LENGTH])
        return keys


class NameKeyOfTwoCharacters(Model):
    """Uses only 2 characters."""

    KEY_LENGTH = 2


class NameKeyOfFourCharacters(Model):
    """Uses 4 characters."""

    KEY_LENGTH = 4


class NoEmailKey(Model):
    """Blocks on the name only."""

    def keys_of(self, row: tuple[str, str]) -> set[str]:
        return {key for key in super().keys_of(row) if key.startswith("n:")}


class NoNameKey(Model):
    """Blocks on the email only."""

    def keys_of(self, row: tuple[str, str]) -> set[str]:
        return {key for key in super().keys_of(row) if key.startswith("e:")}


class EveryPairIsACandidate(Model):
    """Compares everything with everything."""

    def comparable(self, first: str, second: str) -> bool:
        return True


class JaroWindowTooWide(Model):
    """Forgets to subtract 1 from the window."""

    def window(self, first_length: int, second_length: int) -> int:
        return max(first_length, second_length) // 2


class JaroWindowOfTheShorterText(Model):
    """Sizes the window from the shorter text."""

    def window(self, first_length: int, second_length: int) -> int:
        return max(0, min(first_length, second_length) // 2 - 1)


class TranspositionsRoundedDown(Model):
    """Counts whole transpositions only."""

    def transpositions(self, differing: int) -> float:
        return differing // 2


class TranspositionsNotHalved(Model):
    """Counts every differing position as a transposition."""

    def transpositions(self, differing: int) -> float:
        return differing


class BoostOnlyAboveSevenTenths(Model):
    """Applies the prefix bonus only to a Jaro value above 0.7."""

    BOOST_ABOVE = 0.7


class PrefixNotCapped(Model):
    """Counts the whole common prefix."""

    PREFIX_CAP = 100


class PrefixOfThree(Model):
    """Caps the prefix at 3."""

    PREFIX_CAP = 3


class ScaleOfOneTenthPlus(Model):
    """Uses a larger scale for the prefix."""

    SCALE = 0.15


class CharactersMatchTwice(Model):
    """Lets a character of the second text match more than once."""

    REUSE_CHARACTERS = True


class EmptyAgainstEmptyIsOne(Model):
    """Scores two empty texts as equal."""

    def both_empty(self) -> float:
        return 1.0


class JaccardCountsRepeats(Model):
    """Counts repeated tokens."""

    def token_jaccard(self, first: str, second: str) -> float:
        left, right = first.split(), second.split()
        if not left and not right:
            return 0.0
        both = sum(min(left.count(token), right.count(token)) for token in set(left))
        return both / (len(left) + len(right) - both)


class JaccardOfTwoEmptyTextsIsOne(Model):
    """Scores two texts without tokens as equal."""

    def empty_overlap(self) -> float:
        return 1.0


class JaccardIgnoresCase(Model):
    """Folds case before comparing tokens."""

    def tokens(self, text: str) -> Any:
        return set(text.lower().split())


class ScoreIgnoresTheEmail(Model):
    """Never lets an email decide."""

    def same_email(self, first: tuple[str, str], second: tuple[str, str]) -> bool:
        return False


class EmptyEmailsAreEqual(Model):
    """Counts two empty emails as the same email."""

    def same_email(self, first: tuple[str, str], second: tuple[str, str]) -> bool:
        return first[1] == second[1]


class EmailEqualityBeforeNormalisation(Model):
    """Compares the emails as stored in lower case but without the shared trimming of the name."""

    def same_email(self, first: tuple[str, str], second: tuple[str, str]) -> bool:
        return first[1] != "" and first == second


class WeightsSwapped(Model):
    """Gives 0.3 to Jaro-Winkler and 0.7 to the tokens."""

    WEIGHT_JARO = 0.3


class ThresholdOfSevenTenths(Model):
    """Matches from 0.7."""

    MATCH = 0.70


class ThresholdOfEightTenths(Model):
    """Matches from 0.8."""

    MATCH = 0.80


class MatchesIgnoreBlocking(Model):
    """Lists every pair that matches, compared or not."""

    def matches(self) -> list[list[str]]:
        ids = sorted(self.rows)
        return [[a, b] for a, b in combinations(ids, 2) if self.is_match(a, b)]


class UnknownIdMatches(Model):
    """Answers true for an id that is not stored when both are the same."""

    def is_match(self, first: str, second: str) -> bool:
        return first == second or super().is_match(first, second)


# ------------------------------------------------------------------ level 3 mistakes
class GuardMissing(Model):
    """Merges every matched pair, as components does."""

    def may_merge(self, one: set[str], other: set[str]) -> bool:
        return True


class GuardAtTheMatchThreshold(Model):
    """Requires cross pairs to match, not only to be close."""

    FLOOR = 0.75


class GuardFloorTooLow(Model):
    """Uses a floor of 0.5."""

    FLOOR = 0.5


class GuardChecksOnlyTheMatchedPair(Model):
    """Looks at the pair that caused the merge, not at the other cross pairs."""

    def cluster_sets(self) -> list[set[str]]:
        groups = [{record_id} for record_id in self.rows]
        for first, second in self.edges():
            one = next(g for g in groups if first in g)
            other = next(g for g in groups if second in g)
            if one is not other and self.similarity(first, second) >= self.FLOOR:
                groups.remove(other)
                one |= other
        return groups


class GuardChecksOnlyComparedPairs(Model):
    """Skips the cross pairs that blocking would not compare."""

    def may_merge(self, one: set[str], other: set[str]) -> bool:
        compared = {tuple(pair) for pair in self.candidate_pairs()}
        return all(
            self.similarity(a, b) >= self.FLOOR
            for a in one
            for b in other
            if tuple(sorted((a, b))) in compared
        )


class PairsTakenInIdOrder(Model):
    """Visits the matches in the order of the ids instead of the score."""

    def edges(self) -> list[list[str]]:
        return sorted(self.matches())


class PairsTakenFromTheLowestScore(Model):
    """Visits the weakest matches first."""

    def edges(self) -> list[list[str]]:
        return sorted(self.matches(), key=lambda pair: (self.similarity(*pair), *pair))


class SingletonsLeftOut(Model):
    """Lists only groups of two or more records."""

    def finish(self, groups: Any) -> list[list[str]]:
        return sorted(sorted(group) for group in groups if len(group) > 1)


class GroupsInTheOrderOfCreation(Model):
    """Leaves the ids of a group in the order the records were added."""

    def finish(self, groups: Any) -> list[list[str]]:
        order = list(self.rows)
        return sorted([sorted(group, key=order.index) for group in groups])


class CanonicalIsTheLongestName(Model):
    """Ignores the email when choosing the canonical record."""

    def canonical_key(self, record_id: str) -> tuple[Any, ...]:
        return (-len(self.rows[record_id][0]), record_id)


class CanonicalIsTheLargestId(Model):
    """Breaks ties by the larger id."""

    def canonical_key(self, record_id: str) -> tuple[Any, ...]:
        name, email = self.rows[record_id]
        return (-(bool(name) + bool(email)), -len(name), tuple(-ord(ch) for ch in record_id))


class CanonicalIsTheFirstAdded(Model):
    """Breaks ties by the order in which the records were added."""

    def canonical_key(self, record_id: str) -> tuple[Any, ...]:
        name, email = self.rows[record_id]
        return (-(bool(name) + bool(email)), -len(name), list(self.rows).index(record_id))


class CanonicalCountsOnlyNames(Model):
    """Counts the filled fields as the name alone."""

    def canonical_key(self, record_id: str) -> tuple[Any, ...]:
        name, _ = self.rows[record_id]
        return (-bool(name), -len(name), record_id)


class AliasesKeepTheCanonicalName(Model):
    """Lists every distinct name."""

    def aliases(self, record_id: str) -> list[str]:
        group = self.entity(record_id)
        return sorted(self.alias_pool(group) - {""}) if group else []


class AliasesKeepEmptyNames(Model):
    """Lists the empty name as an alias."""

    def aliases(self, record_id: str) -> list[str]:
        group = self.entity(record_id)
        if not group:
            return []
        keeper = self.rows[self.canonical(record_id)][0]
        return sorted(self.alias_pool(group) - {keeper})


class AliasesRepeatNames(Model):
    """Lists a name once for every record that has it."""

    def aliases(self, record_id: str) -> list[str]:
        group = self.entity(record_id)
        if not group:
            return []
        keeper = self.rows[self.canonical(record_id)][0]
        return sorted(self.rows[m][0] for m in group if self.rows[m][0] not in (keeper, ""))


class EntityIsTheComponent(Model):
    """Reads canonical record and aliases from the plain components."""

    def entity(self, record_id: str) -> set[str]:
        if record_id not in self.rows:
            return set()
        return next(set(g) for g in self.components() if record_id in g)


class UnknownIdHasItselfAsCanonical(Model):
    """Answers with the id when it is not stored."""

    def canonical(self, record_id: str) -> str:
        return super().canonical(record_id) or record_id


# ------------------------------------------------------------------ level 4 mistakes
class NoPredictedPairsMeansZeroPrecision(Model):
    """Gives precision 0 when no pair is predicted."""

    def empty_precision(self) -> float:
        return 0.0


class NoGoldPairsMeansZeroRecall(Model):
    """Gives recall 0 when the gold has no pair."""

    def empty_recall(self) -> float:
        return 0.0


class PairwiseF1IsTheMean(Model):
    """Averages precision and recall."""

    def harmonic(self, precision: float, recall: float) -> float:
        return (precision + recall) / 2


class PairwiseCountsOrderedPairs(Model):
    """Counts each pair in both directions, which changes nothing but also a record with itself."""

    def pair_set(self, groups: list[list[str]]) -> set[tuple[str, str]]:
        return {(a, b) for group in groups for a in group for b in group}


class BcubedOverClusters(Model):
    """Averages over the predicted clusters, not over the records."""

    def bcubed_scores(self, predicted: list[list[str]], gold: list[list[str]]) -> list[float]:
        truth = {i: set(group) for group in gold for i in group}
        precision = recall = 0.0
        for group in predicted:
            members = set(group)
            precision += sum(len(members & truth[i]) / len(members) for i in members) / len(members)
            recall += sum(len(members & truth[i]) / len(truth[i]) for i in members) / len(members)
        precision /= len(predicted)
        recall /= len(predicted)
        return [precision, recall, self.harmonic(precision, recall)]


class BcubedF1IsTheMeanOfRecordF1(Model):
    """Combines precision and recall for each record, then averages."""

    def bcubed_scores(self, predicted: list[list[str]], gold: list[list[str]]) -> list[float]:
        overlaps = self.record_overlaps(predicted, gold)
        precision = sum(p for p, _ in overlaps) / len(overlaps)
        recall = sum(r for _, r in overlaps) / len(overlaps)
        return [precision, recall, sum(self.harmonic(p, r) for p, r in overlaps) / len(overlaps)]


class BcubedSidesSwapped(Model):
    """Reports recall first."""

    def bcubed_scores(self, predicted: list[list[str]], gold: list[list[str]]) -> list[float]:
        precision, recall, f1 = super().bcubed_scores(predicted, gold)
        return [recall, precision, f1]


class ErrorLabelsSwapped(Model):
    """Calls a missed pair a false merge and the reverse."""

    def error_labels(self) -> tuple[str, str]:
        return "missed", "false-merge"


class MissedPairsListedFirst(Model):
    """Lists the missed pairs before the false merges."""

    def error_order(self, rows: list[list[str]]) -> list[list[str]]:
        return sorted(rows, key=lambda row: (row[0] != "missed", row[1], row[2]))


class ErrorsInTheOrderOfDiscovery(Model):
    """Leaves the pairs in the order a set gives them, then by label."""

    def error_order(self, rows: list[list[str]]) -> list[list[str]]:
        return sorted(rows, key=lambda row: (row[0], row[2], row[1]))


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def same(actual: Any, expected: Any, tolerance: float) -> bool:
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(same(a, e, tolerance) for a, e in zip(actual, expected, strict=True))
        )
    if isinstance(expected, float):
        return isinstance(actual, float) and abs(actual - expected) <= tolerance * max(
            1.0, abs(expected)
        )
    return actual == expected and type(actual) is type(expected)


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def agrees(actual: Sequence[Any], case: Mapping[str, Any]) -> bool:
    flags = [op in FLOAT_METHODS for op in case["ops"]]
    return len(actual) == len(case["expected"]) and all(
        same(got, want, TOLERANCE if is_float else 0.0)
        for got, want, is_float in zip(actual, case["expected"], flags, strict=True)
    )


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return agrees(outputs(model_type, case), case)
    except (IndexError, KeyError, ValueError, TypeError, ZeroDivisionError, StopIteration):
        return False


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert agrees(outputs(Model, case), case)


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def final_model(case: Mapping[str, Any]) -> Model:
    model = Model()
    for op, arguments in zip(case["ops"][1:], case["args"][1:], strict=True):
        if op == "addRecord":
            model.add_record(*arguments)
    return model


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_no_decision_rests_on_a_score_within_a_billionth_of_a_threshold(case):
    model = final_model(case)
    for first, second in combinations(sorted(model.rows), 2):
        score = model.similarity(first, second)
        assert abs(score - Model.MATCH) > 1e-9, (first, second)
        assert abs(score - Model.FLOOR) > 1e-9, (first, second)


class EqualScoresBelowOneTiedTheOtherWay(Model):
    """Visits pairs with equal scores below 1 from the larger ids down. Scores of exactly 1 keep
    the order of the statement, since a shared email and equal names both give exactly 1."""

    def edges(self) -> list[list[str]]:
        def key(pair: list[str]) -> tuple[Any, ...]:
            score = self.similarity(*pair)
            if score >= 1 - 1e-12:
                return (-1.0, 0, *pair)
            return (-round(score, 9), 1, *(tuple(-ord(ch) for ch in part) for part in pair))

        return sorted(self.matches(), key=key)


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_no_answer_depends_on_how_equal_scores_below_one_are_ordered(case):
    assert agrees(outputs(EqualScoresBelowOneTiedTheOtherWay, case), case)


def test_the_cases_use_the_values_that_the_statement_quotes():
    jaro = {
        (case["args"][i][0], case["args"][i][1]): case["expected"][i]
        for case in SCRIPTED_CASES
        for i, op in enumerate(case["ops"])
        if op == "jaroWinkler"
    }
    assert jaro[("MARTHA", "MARHTA")] == pytest.approx(0.9611111, abs=1e-6)
    assert jaro[("DWAYNE", "DUANE")] == pytest.approx(0.84, abs=1e-6)
    assert jaro[("DIXON", "DICKSONX")] == pytest.approx(0.8133333, abs=1e-6)


def test_a_hidden_case_has_an_odd_number_of_out_of_order_characters():
    assert any(
        case["ops"][i] == "jaroWinkler" and case["args"][i] == ["bac", "acbccc"]
        for case in HIDDEN_CASES
        for i in range(len(case["ops"]))
    )


def test_every_level_has_visible_and_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert any(case.get("visible") for case in at_level)
        assert sum(not case.get("visible") for case in at_level) >= 2
