"""taxonomy promises that its hidden cases catch the classic mistakes of a concept hierarchy with
several parents: walks that follow one path instead of the shortest, duplicates through a diamond,
a cycle check that is too shallow, one lowest common ancestor where a DAG has several, labels
compared without the normalization the statement fixes, and ids that stop working after a rename,
a replacement or a mapping. These tests replay every case against a model of the taxonomy written
from the statement, which must give every expected output, and against that model with one mistake
planted at a time, which some hidden case must fail. A mistake that crashes fails its case, as a
thrown exception does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0317-taxonomy"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]


class Model:
    """The taxonomy as the statement words it, one rule per method, so that each mistake below
    overrides a single method. It keeps the links as a list and answers by looking at them."""

    def __init__(self) -> None:
        self.label: dict[str, str] = {}
        self.order: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.alts: dict[str, list[str]] = {}
        self.gone: dict[str, str] = {}
        self.matches: set[frozenset[str]] = set()

    # --- what a concept is
    def scheme(self, concept: str) -> str:
        return concept.split(":")[0] if ":" in concept else ""

    def norm(self, text: str) -> str:
        return re.sub(r" +", " ", text.strip(" ")).lower()

    def known(self, concept: str) -> bool:
        return concept in self.label

    def follow(self, concept: str) -> str:
        while concept in self.gone:
            concept = self.gone[concept]
        return concept

    def parents_of(self, concept: str) -> list[str]:
        return [parent for child, parent in self.links if child == concept]

    def children_of(self, concept: str) -> list[str]:
        return [child for child, parent in self.links if parent == concept]

    def distances(self, start: str, up: bool) -> dict[str, int]:
        """The fewest links from the start to each concept above (or below) it."""
        dist = {start: 0}
        changed = True
        while changed:
            changed = False
            for child, parent in self.links:
                source, target = (child, parent) if up else (parent, child)
                if source in dist and dist[source] + 1 < dist.get(target, 10**9):
                    dist[target] = dist[source] + 1
                    changed = True
        return dist

    def nearest_first(self, concept: str, up: bool) -> list[str]:
        if not self.known(concept):
            return []
        dist = self.distances(concept, up)
        del dist[concept]
        return [c for c, _ in sorted(dist.items(), key=lambda item: (item[1], item[0]))]

    def ancestor_set(self, concept: str) -> set[str]:
        return {concept, *self.nearest_first(concept, True)}

    # --- level 1
    def add_concept(self, concept: str, label: str, parents: list[str]) -> str:
        if self.known(concept):
            return "duplicate"
        if concept in parents:
            return "cycle"
        if any(not self.known(parent) for parent in parents):
            return "unknown-broader"
        resolved = [self.follow(parent) for parent in parents]
        if any(self.scheme(parent) != self.scheme(concept) for parent in resolved):
            return "cross-scheme"
        self.label[concept] = label
        self.order.append(concept)
        self.alts[concept] = []
        for parent in resolved:
            if (concept, parent) not in self.links:
                self.links.append((concept, parent))
        return "ok"

    def add_broader(self, narrower: str, broader: str) -> str:
        child, parent = self.follow(narrower), self.follow(broader)
        if not self.known(child) or not self.known(parent):
            return "unknown-concept"
        if self.scheme(child) != self.scheme(parent):
            return "cross-scheme"
        if child in self.ancestor_set(parent):
            return "cycle"
        if (child, parent) not in self.links:
            self.links.append((child, parent))
        return "ok"

    def pref_label(self, concept: str) -> str:
        return self.label.get(self.follow(concept), "")

    def broader(self, concept: str) -> list[str]:
        return sorted(self.parents_of(self.follow(concept)))

    def narrower(self, concept: str) -> list[str]:
        return sorted(self.children_of(self.follow(concept)))

    def ancestors(self, concept: str) -> list[str]:
        return self.nearest_first(self.follow(concept), True)

    def descendants(self, concept: str) -> list[str]:
        return self.nearest_first(self.follow(concept), False)

    def live(self) -> list[str]:
        return [concept for concept in self.order if concept not in self.gone]

    def roots(self) -> list[str]:
        return sorted(c for c in self.live() if not self.parents_of(c))

    # --- level 2
    def lowest_common_ancestors(self, first: str, second: str) -> list[str]:
        first, second = self.follow(first), self.follow(second)
        if not self.known(first) or not self.known(second):
            return []
        common = self.ancestor_set(first) & self.ancestor_set(second)
        return sorted(
            c for c in common if not any(d != c and c in self.ancestor_set(d) for d in common)
        )

    # --- level 3
    def labels_of(self, concept: str) -> list[str]:
        return [self.label[concept], *self.alts[concept]]

    def add_alt_label(self, concept: str, label: str) -> str:
        concept = self.follow(concept)
        if not self.known(concept):
            return "unknown-concept"
        key = self.norm(label)
        if key == "":
            return "empty-label"
        if key in [self.norm(text) for text in self.labels_of(concept)]:
            return "duplicate"
        self.alts[concept].append(label)
        return "ok"

    def alt_labels(self, concept: str) -> list[str]:
        concept = self.follow(concept)
        return list(self.alts[concept]) if self.known(concept) else []

    def matching(self, label: str) -> set[str]:
        key = self.norm(label)
        if key == "":
            return set()
        return {
            self.follow(c)
            for c in self.order
            if key in [self.norm(text) for text in self.labels_of(c)]
        }

    def find_by_label(self, label: str) -> list[str]:
        return sorted(self.matching(label))

    def expand(self, labels: list[str]) -> list[str]:
        found: set[str] = set()
        for label in labels:
            for concept in self.matching(label):
                found |= {concept, *self.descendants(concept)}
        return sorted(found)

    # --- level 4
    def rename(self, concept: str, label: str) -> str:
        concept = self.follow(concept)
        if not self.known(concept):
            return "unknown-concept"
        old, key = self.label[concept], self.norm(label)
        kept = [text for text in self.alts[concept] if self.norm(text) != key]
        if self.norm(old) not in ("", key):
            kept.append(old)
        self.alts[concept] = kept
        self.label[concept] = label
        return "ok"

    def remove_broader(self, narrower: str, broader: str) -> str:
        child, parent = self.follow(narrower), self.follow(broader)
        if not self.known(child) or not self.known(parent):
            return "unknown-concept"
        if (child, parent) not in self.links:
            return "no-link"
        self.links.remove((child, parent))
        return "ok"

    def deprecate(self, concept: str, replacement: str) -> str:
        if not self.known(concept) or not self.known(replacement):
            return "unknown-concept"
        if concept in self.gone:
            return "deprecated"
        target = self.follow(replacement)
        if target == concept:
            return "same-concept"
        if self.scheme(target) != self.scheme(concept):
            return "cross-scheme"
        if self.children_of(concept):
            return "has-narrower"
        self.links = [(c, p) for c, p in self.links if c != concept]
        self.matches = {
            frozenset(target if m == concept else m for m in pair) for pair in self.matches
        }
        self.gone[concept] = target
        return "ok"

    def resolve(self, concept: str) -> str:
        concept = self.follow(concept)
        return concept if self.known(concept) else ""

    def add_exact_match(self, first: str, second: str) -> str:
        first, second = self.follow(first), self.follow(second)
        if not self.known(first) or not self.known(second):
            return "unknown-concept"
        if self.scheme(first) == self.scheme(second):
            return "same-scheme"
        self.matches.add(frozenset((first, second)))
        return "ok"

    def partners(self, concept: str, scheme: str) -> set[str]:
        found = set()
        for pair in self.matches:
            if concept in pair:
                found |= {other for other in pair if self.scheme(other) == scheme}
        return found

    def known_inputs(self, concepts: list[str]) -> list[str]:
        resolved = {self.follow(concept) for concept in concepts}
        return sorted(c for c in resolved if self.known(c))

    def targets(self, concept: str, scheme: str) -> set[str]:
        if self.scheme(concept) == scheme:
            return {concept}
        return self.partners(concept, scheme)

    def translate(self, concepts: list[str], scheme: str) -> list[str]:
        found: set[str] = set()
        for concept in self.known_inputs(concepts):
            found |= self.targets(concept, scheme)
        return sorted(found)

    def unmapped(self, concepts: list[str], scheme: str) -> list[str]:
        return [c for c in self.known_inputs(concepts) if not self.targets(c, scheme)]


# ------------------------------------------------------------------ level 1 mistakes
class AncestorsDepthFirst(Model):
    """Lists the ancestors in depth-first order instead of nearest first."""

    def ancestors(self, concept: str) -> list[str]:
        order: list[str] = []

        def visit(current: str) -> None:
            for parent in sorted(self.parents_of(current)):
                if parent not in order:
                    order.append(parent)
                    visit(parent)

        concept = self.follow(concept)
        visit(concept) if self.known(concept) else None
        return order


class AncestorsSortedById(Model):
    """Sorts the ancestors by id and ignores the distance."""

    def ancestors(self, concept: str) -> list[str]:
        return sorted(super().ancestors(concept))


class AncestorsByLongestPath(Model):
    """Measures the distance along the longest path instead of the shortest."""

    def ancestors(self, concept: str) -> list[str]:
        concept = self.follow(concept)
        if not self.known(concept):
            return []
        longest = {concept: 0}
        for _ in range(len(self.order)):
            for child, parent in self.links:
                if child in longest:
                    longest[parent] = max(longest.get(parent, 0), longest[child] + 1)
        del longest[concept]
        return [c for c, _ in sorted(longest.items(), key=lambda item: (item[1], item[0]))]


class AncestorsIncludeTheConcept(Model):
    """Puts the concept itself first."""

    def ancestors(self, concept: str) -> list[str]:
        found = super().ancestors(concept)
        return [self.follow(concept), *found] if found or self.known(self.follow(concept)) else []


class DescendantsRepeatedThroughADiamond(Model):
    """Lists a concept once for every path that leads to it."""

    def descendants(self, concept: str) -> list[str]:
        concept = self.follow(concept)
        if not self.known(concept):
            return []
        found: list[str] = []
        level = [concept]
        while level:
            level = sorted(kid for current in level for kid in self.children_of(current))
            found.extend(level)
        return found


class DescendantsOnlyTheChildren(Model):
    """Stops at the direct children."""

    def descendants(self, concept: str) -> list[str]:
        return self.narrower(concept)


class AncestorsOnlyTheParents(Model):
    """Stops at the direct parents."""

    def ancestors(self, concept: str) -> list[str]:
        return self.broader(concept)


class BroaderInInsertionOrder(Model):
    """Lists the parents in the order the links were made."""

    def broader(self, concept: str) -> list[str]:
        return self.parents_of(self.follow(concept))


class RootsInInsertionOrder(Model):
    """Lists the roots in the order the concepts were added."""

    def roots(self) -> list[str]:
        return [c for c in self.live() if not self.parents_of(c)]


class NarrowerInInsertionOrder(Model):
    """Lists the children in the order the links were made."""

    def narrower(self, concept: str) -> list[str]:
        return self.children_of(self.follow(concept))


class AddConceptKeepsWhatWasValid(Model):
    """Adds the concept and the known parents when another parent is unknown."""

    def add_concept(self, concept: str, label: str, parents: list[str]) -> str:
        outcome = super().add_concept(concept, label, parents)
        if outcome == "unknown-broader":
            super().add_concept(concept, label, [p for p in parents if self.known(p)])
        return outcome


class AddConceptDuplicateReplacesTheLabel(Model):
    """Overwrites the label of an existing concept."""

    def add_concept(self, concept: str, label: str, parents: list[str]) -> str:
        outcome = super().add_concept(concept, label, parents)
        if outcome == "duplicate":
            self.label[concept] = label
        return outcome


class UnknownParentBeforeDuplicate(Model):
    """Checks the parents before the id."""

    def add_concept(self, concept: str, label: str, parents: list[str]) -> str:
        if any(not self.known(parent) for parent in parents):
            return "unknown-broader"
        return super().add_concept(concept, label, parents)


class AddBroaderToAnUnknownConceptIsOk(Model):
    """Accepts a link whose end has no concept."""

    def add_broader(self, narrower: str, broader: str) -> str:
        outcome = super().add_broader(narrower, broader)
        return "ok" if outcome == "unknown-concept" else outcome


class AddBroaderTwiceIsAnError(Model):
    """Answers 'duplicate' for a link that is already there."""

    def add_broader(self, narrower: str, broader: str) -> str:
        if (self.follow(narrower), self.follow(broader)) in self.links:
            return "duplicate"
        return super().add_broader(narrower, broader)


class PrefLabelOfAnUnknownConceptIsTheId(Model):
    """Gives the id back when there is no concept."""

    def pref_label(self, concept: str) -> str:
        return super().pref_label(concept) or concept


class PrefLabelIsTrimmed(Model):
    """Stores the label without its outer spaces."""

    def add_concept(self, concept: str, label: str, parents: list[str]) -> str:
        return super().add_concept(concept, label.strip(), parents)


class RootsIncludeOnlyConceptsWithChildren(Model):
    """Leaves a lone concept out of the roots."""

    def roots(self) -> list[str]:
        return [c for c in super().roots() if self.children_of(c)]


# ------------------------------------------------------------------ level 2 mistakes
class CyclesAllowed(Model):
    """Never rejects a link."""

    def add_broader(self, narrower: str, broader: str) -> str:
        child, parent = self.follow(narrower), self.follow(broader)
        if not self.known(child) or not self.known(parent):
            return "unknown-concept"
        self.links.append((child, parent))
        return "ok"


class SelfLinkAllowed(Model):
    """Rejects longer cycles but lets a concept be its own parent."""

    def add_broader(self, narrower: str, broader: str) -> str:
        if self.follow(narrower) == self.follow(broader) and self.known(self.follow(narrower)):
            self.links.append((self.follow(narrower), self.follow(narrower)))
            return "ok"
        return super().add_broader(narrower, broader)


class OnlyTwoConceptLoopsRejected(Model):
    """Looks at the direct parents of the new parent only."""

    def add_broader(self, narrower: str, broader: str) -> str:
        child, parent = self.follow(narrower), self.follow(broader)
        if (
            self.known(child)
            and self.known(parent)
            and child != parent
            and child not in self.parents_of(parent)
        ):
            if (child, parent) not in self.links:
                self.links.append((child, parent))
            return "ok"
        return super().add_broader(narrower, broader)


class RejectedLinkIsStillAdded(Model):
    """Answers 'cycle' and adds the link anyway."""

    def add_broader(self, narrower: str, broader: str) -> str:
        outcome = super().add_broader(narrower, broader)
        if outcome == "cycle":
            self.links.append((self.follow(narrower), self.follow(broader)))
        return outcome


class SelfParentOnInsertIsUnknown(Model):
    """Reports a concept that names itself as parent as an unknown parent."""

    def add_concept(self, concept: str, label: str, parents: list[str]) -> str:
        outcome = super().add_concept(concept, label, parents)
        return "unknown-broader" if outcome == "cycle" else outcome


class SelfParentOnInsertAccepted(Model):
    """Lets a new concept name itself as parent."""

    def add_concept(self, concept: str, label: str, parents: list[str]) -> str:
        if concept in parents and not self.known(concept):
            return super().add_concept(concept, label, [p for p in parents if p != concept])
        return super().add_concept(concept, label, parents)


class OneLowestCommonAncestor(Model):
    """Answers with a single concept, the first of the lowest ones."""

    def lowest_common_ancestors(self, first: str, second: str) -> list[str]:
        return super().lowest_common_ancestors(first, second)[:1]


class EveryCommonAncestor(Model):
    """Answers with all the common ancestors, not just the lowest."""

    def lowest_common_ancestors(self, first: str, second: str) -> list[str]:
        first, second = self.follow(first), self.follow(second)
        if not self.known(first) or not self.known(second):
            return []
        return sorted(self.ancestor_set(first) & self.ancestor_set(second))


class LowestIsTheDeepestOne(Model):
    """Keeps the common ancestors of the greatest depth, as in a tree."""

    def depth(self, concept: str) -> int:
        dist = self.distances(concept, True)
        return max(dist.values())

    def lowest_common_ancestors(self, first: str, second: str) -> list[str]:
        first, second = self.follow(first), self.follow(second)
        if not self.known(first) or not self.known(second):
            return []
        common = self.ancestor_set(first) & self.ancestor_set(second)
        if not common:
            return []
        deepest = max(self.depth_below_roots(c) for c in common)
        return sorted(c for c in common if self.depth_below_roots(c) == deepest)

    def depth_below_roots(self, concept: str) -> int:
        """The length of the longest path from a root down to the concept."""
        return max(
            (len(path) for path in [self.longest_up(concept)]),
            default=0,
        )

    def longest_up(self, concept: str) -> list[str]:
        best: list[str] = []
        for parent in self.parents_of(concept):
            candidate = self.longest_up(parent)
            if len(candidate) > len(best):
                best = candidate
        return [*best, concept]


class LowestCommonExcludesTheConceptItself(Model):
    """Starts from the parents, so that a concept above the other is not its own answer."""

    def lowest_common_ancestors(self, first: str, second: str) -> list[str]:
        first, second = self.follow(first), self.follow(second)
        if not self.known(first) or not self.known(second):
            return []
        common = set(self.nearest_first(first, True)) & set(self.nearest_first(second, True))
        return sorted(
            c for c in common if not any(d != c and c in self.ancestor_set(d) for d in common)
        )


class LowestCommonOfAnUnknownIsTheOther(Model):
    """Answers with the known concept when the other one has no entry."""

    def lowest_common_ancestors(self, first: str, second: str) -> list[str]:
        if not self.known(self.follow(second)) and self.known(self.follow(first)):
            return [self.follow(first)]
        return super().lowest_common_ancestors(first, second)


class LowestCommonAncestorsInTheOrderFound(Model):
    """Lists the answers by distance from the first concept instead of by id."""

    def lowest_common_ancestors(self, first: str, second: str) -> list[str]:
        found = super().lowest_common_ancestors(first, second)
        dist = self.distances(self.follow(first), True)
        return sorted(found, key=lambda c: (-dist.get(c, 0), c))


# ------------------------------------------------------------------ level 3 mistakes
class LabelsKeepTheirCase(Model):
    """Compares labels without folding the case."""

    def norm(self, text: str) -> str:
        return re.sub(r" +", " ", text.strip(" "))


class LabelsKeepOuterSpaces(Model):
    """Compares labels without trimming them."""

    def norm(self, text: str) -> str:
        return re.sub(r" +", " ", text).lower()


class LabelsKeepInnerRuns(Model):
    """Trims and folds but leaves runs of spaces as they are."""

    def norm(self, text: str) -> str:
        return text.strip(" ").lower()


class LabelsLoseAllSpaces(Model):
    """Removes every space, so that 'a b' and 'ab' are the same label."""

    def norm(self, text: str) -> str:
        return text.replace(" ", "").lower()


class FindIgnoresAltLabels(Model):
    """Looks only at the preferred labels."""

    def labels_of(self, concept: str) -> list[str]:
        return [self.label[concept]]

    def add_alt_label(self, concept: str, label: str) -> str:
        return Model.add_alt_label(self, concept, label)


class FindReturnsTheFirstConcept(Model):
    """Answers with one concept even when several share the label."""

    def find_by_label(self, label: str) -> list[str]:
        return super().find_by_label(label)[:1]


class ExpandWithoutTheConcept(Model):
    """Adds the descendants but not the concept that the label names."""

    def expand(self, labels: list[str]) -> list[str]:
        named = {c for label in labels for c in self.matching(label)}
        return sorted(set(super().expand(labels)) - named)


class ExpandOnlyTheChildren(Model):
    """Adds the direct children but not the whole subtree."""

    def expand(self, labels: list[str]) -> list[str]:
        found: set[str] = set()
        for label in labels:
            for concept in self.matching(label):
                found |= {concept, *self.narrower(concept)}
        return sorted(found)


class ExpandRepeatsConcepts(Model):
    """Lists a concept once for every label and path that reaches it."""

    def expand(self, labels: list[str]) -> list[str]:
        found: list[str] = []
        for label in labels:
            for concept in sorted(self.matching(label)):
                found.extend([concept, *self.descendants(concept)])
        return sorted(found)


class ExpandUsesTheFirstLabelOnly(Model):
    """Reads only the first label of the list."""

    def expand(self, labels: list[str]) -> list[str]:
        return super().expand(labels[:1])


class ExpandUsesTheFirstConceptOnly(Model):
    """Expands one concept when several share the label."""

    def expand(self, labels: list[str]) -> list[str]:
        found: set[str] = set()
        for label in labels:
            for concept in sorted(self.matching(label))[:1]:
                found |= {concept, *self.descendants(concept)}
        return sorted(found)


class AltLabelEqualToThePrefLabelAccepted(Model):
    """Lets an alternative label repeat the preferred label."""

    def add_alt_label(self, concept: str, label: str) -> str:
        concept = self.follow(concept)
        if self.known(concept) and self.norm(label) == self.norm(self.label[concept]):
            self.alts[concept].append(label)
            return "ok"
        return super().add_alt_label(concept, label)


class AltLabelDuplicateComparedAsGiven(Model):
    """Compares a new alternative label with the old ones before normalizing."""

    def add_alt_label(self, concept: str, label: str) -> str:
        concept = self.follow(concept)
        if self.known(concept) and label in self.alts[concept] and self.norm(label):
            return "duplicate"
        if self.known(concept) and self.norm(label) in [self.norm(t) for t in self.alts[concept]]:
            self.alts[concept].append(label)
            return "ok"
        return super().add_alt_label(concept, label)


class AltLabelStoredNormalized(Model):
    """Keeps the normalized text of an alternative label."""

    def add_alt_label(self, concept: str, label: str) -> str:
        outcome = super().add_alt_label(concept, label)
        if outcome == "ok":
            self.alts[self.follow(concept)][-1] = self.norm(label)
        return outcome


class AltLabelsSorted(Model):
    """Lists the alternative labels in alphabetical order."""

    def alt_labels(self, concept: str) -> list[str]:
        return sorted(super().alt_labels(concept))


class EmptyAltLabelAccepted(Model):
    """Stores a label that is empty after normalization."""

    def add_alt_label(self, concept: str, label: str) -> str:
        concept = self.follow(concept)
        if self.known(concept) and self.norm(label) == "":
            self.alts[concept].append(label)
            return "ok"
        return super().add_alt_label(concept, label)


class EmptyLabelMatchesEmptyLabels(Model):
    """Lets a query with an empty label match the concepts whose label is empty."""

    def matching(self, label: str) -> set[str]:
        key = self.norm(label)
        return {
            self.follow(c)
            for c in self.order
            if key in [self.norm(text) for text in self.labels_of(c)]
        }


class SharedLabelBelongsToTheLastConcept(Model):
    """Keeps one concept for a label that several concepts share."""

    def matching(self, label: str) -> set[str]:
        found = sorted(super().matching(label), key=lambda c: self.order.index(c))
        return set(found[-1:])


# ------------------------------------------------------------------ level 4 mistakes
class RenameForgetsTheOldLabel(Model):
    """Replaces the preferred label and drops the old one."""

    def rename(self, concept: str, label: str) -> str:
        concept = self.follow(concept)
        if not self.known(concept):
            return "unknown-concept"
        self.label[concept] = label
        return "ok"


class RenameKeepsTheAltLabelThatIsNowPreferred(Model):
    """Leaves the promoted alternative label in the list."""

    def rename(self, concept: str, label: str) -> str:
        concept = self.follow(concept)
        if not self.known(concept):
            return "unknown-concept"
        old = self.label[concept]
        if self.norm(old) not in ("", self.norm(label)):
            self.alts[concept].append(old)
        self.label[concept] = label
        return "ok"


class RenameOfCaseAddsAnAltLabel(Model):
    """Keeps the old spelling as an alternative label even when it normalizes the same."""

    def rename(self, concept: str, label: str) -> str:
        concept = self.follow(concept)
        if not self.known(concept):
            return "unknown-concept"
        old, key = self.label[concept], self.norm(label)
        self.alts[concept] = [t for t in self.alts[concept] if self.norm(t) != key]
        if self.norm(old) != "":
            self.alts[concept].append(old)
        self.label[concept] = label
        return "ok"


class RenameOfAnUnknownIsOk(Model):
    """Accepts a rename of a concept that does not exist."""

    def rename(self, concept: str, label: str) -> str:
        return super().rename(concept, label).replace("unknown-concept", "ok")


class ResolveIsTheIdItself(Model):
    """Gives the id back even when it was replaced."""

    def resolve(self, concept: str) -> str:
        return concept if self.known(concept) else ""


class ResolveFollowsOneStep(Model):
    """Follows a single replacement."""

    def follow(self, concept: str) -> str:
        return self.gone.get(concept, concept)


class QueriesDoNotResolve(Model):
    """Answers for the old id as if it had no links."""

    def follow(self, concept: str) -> str:
        return concept

    def resolve(self, concept: str) -> str:
        found = Model.follow(self, concept)
        return found if self.known(found) else ""


class DeprecateAllowsTheConceptItself(Model):
    """Replaces a concept with itself."""

    def deprecate(self, concept: str, replacement: str) -> str:
        outcome = super().deprecate(concept, replacement)
        return "ok" if outcome == "same-concept" else outcome


class DeprecateAllowsNarrowerConcepts(Model):
    """Retires a concept that still has children, which keep a parent that is gone."""

    def deprecate(self, concept: str, replacement: str) -> str:
        if self.known(concept) and self.known(replacement) and concept not in self.gone:
            target = self.follow(replacement)
            if target != concept and self.scheme(target) == self.scheme(concept):
                self.gone[concept] = target
                return "ok"
        return super().deprecate(concept, replacement)


class DeprecatedConceptStaysInTheHierarchy(Model):
    """Leaves the links of a retired concept in place."""

    def deprecate(self, concept: str, replacement: str) -> str:
        links = list(self.links)
        outcome = super().deprecate(concept, replacement)
        if outcome == "ok":
            self.links = links
        return outcome

    def live(self) -> list[str]:
        return list(self.order)


class DeprecateAcrossSchemes(Model):
    """Lets the replacement live in another scheme."""

    def deprecate(self, concept: str, replacement: str) -> str:
        outcome = super().deprecate(concept, replacement)
        if outcome == "cross-scheme" and not self.children_of(concept):
            self.gone[concept] = self.follow(replacement)
            return "ok"
        return outcome


class DeprecateTwiceIsOk(Model):
    """Accepts a second replacement for a concept that is already retired."""

    def deprecate(self, concept: str, replacement: str) -> str:
        outcome = super().deprecate(concept, replacement)
        return "ok" if outcome == "deprecated" else outcome


class RetiredLabelsAreForgotten(Model):
    """Stops matching the labels of a retired concept."""

    def matching(self, label: str) -> set[str]:
        key = self.norm(label)
        if key == "":
            return set()
        return {
            c
            for c in self.order
            if c not in self.gone and key in [self.norm(t) for t in self.labels_of(c)]
        }


class RetiredLabelsStopAtTheRetiredId(Model):
    """Answers a label search with the retired id, not its replacement."""

    def matching(self, label: str) -> set[str]:
        key = self.norm(label)
        if key == "":
            return set()
        return {c for c in self.order if key in [self.norm(t) for t in self.labels_of(c)]}


class MatchesStayOnTheRetiredConcept(Model):
    """Does not move the exact matches of a retired concept to its replacement."""

    def deprecate(self, concept: str, replacement: str) -> str:
        pairs = set(self.matches)
        outcome = super().deprecate(concept, replacement)
        if outcome == "ok":
            self.matches = pairs
        return outcome


class RemoveMissingLinkIsOk(Model):
    """Accepts the removal of a link that is not there."""

    def remove_broader(self, narrower: str, broader: str) -> str:
        outcome = super().remove_broader(narrower, broader)
        return "ok" if outcome == "no-link" else outcome


class RemoveBroaderRemovesEveryParent(Model):
    """Cuts all the parents of the concept."""

    def remove_broader(self, narrower: str, broader: str) -> str:
        outcome = super().remove_broader(narrower, broader)
        if outcome == "ok":
            self.links = [(c, p) for c, p in self.links if c != self.follow(narrower)]
        return outcome


class ExactMatchInsideOneScheme(Model):
    """Links two concepts of the same scheme."""

    def add_exact_match(self, first: str, second: str) -> str:
        first, second = self.follow(first), self.follow(second)
        if self.known(first) and self.known(second) and first != second:
            self.matches.add(frozenset((first, second)))
            return "ok"
        return super().add_exact_match(first, second)


class ExactMatchOneWay(Model):
    """Records a match in one direction only."""

    def partners(self, concept: str, scheme: str) -> set[str]:
        return {
            other
            for pair in self.matches
            for other in pair
            if self.ordered(pair)[0] == concept and self.scheme(other) == scheme
        }

    def ordered(self, pair: frozenset[str]) -> list[str]:
        return sorted(pair, key=lambda c: self.scheme(c))


class ExactMatchFollowsChains(Model):
    """Applies the transitive closure of the matches before translating."""

    def partners(self, concept: str, scheme: str) -> set[str]:
        group = {concept}
        changed = True
        while changed:
            changed = False
            for pair in self.matches:
                if pair & group and not pair <= group:
                    group |= pair
                    changed = True
        return {c for c in group if self.scheme(c) == scheme}


class TranslateDropsConceptsAlreadyThere(Model):
    """Leaves out the concepts that already belong to the target scheme."""

    def targets(self, concept: str, scheme: str) -> set[str]:
        return self.partners(concept, scheme)

    def unmapped(self, concepts: list[str], scheme: str) -> list[str]:
        return [
            c
            for c in self.known_inputs(concepts)
            if self.scheme(c) != scheme and not self.partners(c, scheme)
        ]


class TranslateTakesOnePartner(Model):
    """Keeps the first partner when a concept has several."""

    def translate(self, concepts: list[str], scheme: str) -> list[str]:
        found: set[str] = set()
        for concept in self.known_inputs(concepts):
            found |= set(sorted(self.targets(concept, scheme))[:1])
        return sorted(found)


class TranslateRepeatsManyToOne(Model):
    """Lists a target once for every concept that maps to it."""

    def translate(self, concepts: list[str], scheme: str) -> list[str]:
        found: list[str] = []
        for concept in self.known_inputs(concepts):
            found.extend(self.targets(concept, scheme))
        return sorted(found)


class TranslateKeepsUnmappedConcepts(Model):
    """Passes a concept without a partner through unchanged."""

    def translate(self, concepts: list[str], scheme: str) -> list[str]:
        found = set(super().translate(concepts, scheme))
        return sorted(found | set(self.unmapped(concepts, scheme)))


class TranslateIgnoresReplacements(Model):
    """Looks up a retired id as given, not through its replacement."""

    def known_inputs(self, concepts: list[str]) -> list[str]:
        return sorted({c for c in concepts if self.known(c) and c not in self.gone})


class UnmappedListsUnknownIds(Model):
    """Reports ids that have no concept as unmapped."""

    def unmapped(self, concepts: list[str], scheme: str) -> list[str]:
        mine = super().unmapped(concepts, scheme)
        return sorted({*mine, *(c for c in concepts if not self.known(self.follow(c)))})


class UnmappedIncludesConceptsInTheScheme(Model):
    """Counts a concept of the target scheme as unmapped."""

    def unmapped(self, concepts: list[str], scheme: str) -> list[str]:
        return [c for c in self.known_inputs(concepts) if not self.partners(c, scheme)]


class UnmappedNotSorted(Model):
    """Lists the unmapped concepts in the order of the input."""

    def unmapped(self, concepts: list[str], scheme: str) -> list[str]:
        wanted = set(super().unmapped(concepts, scheme))
        ordered: list[str] = []
        for concept in concepts:
            resolved = self.follow(concept)
            if resolved in wanted and resolved not in ordered:
                ordered.append(resolved)
        return ordered


class SchemeIsTheLastPrefix(Model):
    """Reads the scheme up to the last colon."""

    def scheme(self, concept: str) -> str:
        return concept.rsplit(":", 1)[0] if ":" in concept else ""


class LinksAcrossSchemesAllowed(Model):
    """Lets a concept have a parent from another scheme."""

    def scheme(self, concept: str) -> str:
        return ""

    def add_exact_match(self, first: str, second: str) -> str:
        first, second = self.follow(first), self.follow(second)
        if not self.known(first) or not self.known(second):
            return "unknown-concept"
        if Model.scheme(self, first) == Model.scheme(self, second):
            return "same-scheme"
        self.matches.add(frozenset((first, second)))
        return "ok"

    def partners(self, concept: str, scheme: str) -> set[str]:
        found = set()
        for pair in self.matches:
            if concept in pair:
                found |= {o for o in pair if Model.scheme(self, o) == scheme}
        return found

    def targets(self, concept: str, scheme: str) -> set[str]:
        if Model.scheme(self, concept) == scheme:
            return {concept}
        return self.partners(concept, scheme)


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


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_a_hidden_case_holds_a_chain_deeper_than_the_default_recursion_limit():
    chain = max(sum(1 for op in case["ops"] if op == "addConcept") for case in HIDDEN_CASES)
    assert chain > 1000


def test_the_generated_case_builds_a_scheme_of_the_largest_size():
    generated = [case for case in CASES if "generate" in case]
    assert [case["generate"]["n"] for case in generated] == [100000]


def test_every_level_has_visible_and_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert any(case.get("visible") for case in at_level)
        assert sum(not case.get("visible") for case in at_level) >= 2
