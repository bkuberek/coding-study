"""context-compaction promises that its hidden cases catch the classic mistakes of keeping a long
conversation in a window: a token rule that rounds, forgets punctuation or white space, or leaves
out the framing; a window that skips a turn that does not fit or cuts a tool run in two; a
compaction that fires on equality, replaces too much or too little, or touches the turns it
should keep; a summary that is appended when it should replace or the other way round; a prefix
comparison that looks at the wrong thing; and a pinned block that is chosen at the wrong moment,
placed in the wrong spot or kept out of the size. These tests replay every case against a model
of the window written from the statement, which must give every expected output, and against that
model with one mistake planted at a time, which some hidden case must fail. A mistake that crashes
fails its case, as a thrown exception does in the grader."""

import copy
import json
import re
from collections.abc import Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0325-context-compaction"
CASES: Sequence[dict[str, Any]] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))[
    "cases"
]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
FRAMING = 4
Item = tuple[str, str, str]  # kind, ref, content


class Model:
    """The window as the statement words it: a history of turns, a set of turns that compaction
    took out, and a live context that is always built from them. Each mistake below overrides one
    hook."""

    def __init__(self) -> None:
        self.turns: list[tuple[str, str, str]] = []
        self.gone: list[int] = []
        self.summary_items: list[tuple[int, str]] = []
        self.queue: list[str] = []
        self.pointer = 0
        self.threshold = -1
        self.keep = 1
        self.low = -1
        self.compaction_count = 0
        self.facts: dict[str, str] = {}
        self.pin_budget = -1
        self.block: list[str] = []
        self.previous: list[Item] = []
        self.reuse: list[int] = []

    # --- level 1: tokens and the window
    def word_char(self, ch: str) -> bool:
        return ch in LETTERS

    def free_char(self, ch: str) -> bool:
        return ch in " \t\n"

    def word_cost(self, length: int) -> int:
        return (length + 3) // 4

    def count_tokens(self, text: str) -> int:
        total, run = 0, 0
        for ch in text:
            if self.word_char(ch):
                run += 1
                continue
            total += self.word_cost(run)
            run = 0
            if not self.free_char(ch):
                total += 1
        return total + self.word_cost(run)

    def cost_of(self, content: str) -> int:
        return self.count_tokens(content) + FRAMING

    def add_turn(self, role: str, content: str) -> int:
        return self.append(role, content, "")

    def system_numbers(self) -> list[int]:
        return [n for n, turn in enumerate(self.turns) if turn[0] == "system"]

    def all_units(self) -> list[list[int]]:
        units: list[list[int]] = []
        for n, (role, _, _) in enumerate(self.turns):
            if role == "system":
                continue
            tool = role in ("call", "result")
            joined = n > 0 and self.turns[n - 1][0] in ("call", "result")
            if tool and joined and units:
                units[-1].append(n)
            else:
                units.append([n])
        return units

    def window_units(self) -> list[list[int]]:
        return self.all_units()

    def unit_fits(self, unit: list[int], taken: int, max_turns: int, cost: int, left: int) -> bool:
        return taken + len(unit) <= max_turns and cost <= left

    def window(self, budget: int, max_turns: int) -> list[int]:
        system = self.system_numbers()
        left = budget - sum(self.cost_of(self.turns[n][1]) for n in system)
        kept: list[int] = []
        for unit in reversed(self.window_units()):
            cost = sum(self.cost_of(self.turns[n][1]) for n in unit)
            if self.unit_fits(unit, len(kept), max_turns, cost, left):
                kept = unit + kept
                left -= cost
            elif self.stop_at_misfit():
                break
        return self.arrange(system, kept)

    def stop_at_misfit(self) -> bool:
        return True

    def arrange(self, system: list[int], kept: list[int]) -> list[int]:
        return system + kept

    # --- level 2: tool calls, summaries, compaction
    def add_call(self, call_id: str, content: str) -> int:
        if any(turn[0] == "call" and turn[2] == call_id for turn in self.turns):
            return -1
        return self.append("call", content, call_id)

    def add_result(self, call_id: str, content: str) -> int:
        has_call = any(turn[0] == "call" and turn[2] == call_id for turn in self.turns)
        answered = any(turn[0] == "result" and turn[2] == call_id for turn in self.turns)
        if not has_call or answered:
            return -1
        return self.append("result", content, call_id)

    def set_summaries(self, texts: list[str]) -> None:
        self.queue = list(texts)
        self.pointer = 0

    def set_compaction(self, threshold: int, keep_recent: int) -> None:
        self.threshold, self.keep = threshold, keep_recent

    def turn_item(self, n: int) -> Item:
        role, content, _ = self.turns[n]
        return (role, str(n), content)

    def live_units(self) -> list[list[int]]:
        return [unit for unit in self.all_units() if unit[0] not in self.gone]

    def summary_item(self, position: int, text: str) -> Item:
        return ("summary", str(position), text)

    def assemble(self, units: list[list[int]], summaries: list[tuple[int, str]], block: list[str]):
        items = [self.turn_item(n) for n in self.system_numbers()]
        items += [self.summary_item(p, t) for p, t in summaries]
        if block:
            items.append(self.block_item(block))
        for unit in units:
            items += [self.turn_item(n) for n in unit]
        return self.place_block(items)

    def block_item(self, block: list[str]) -> Item:
        return ("pinned", ",".join(block), "\n".join(self.facts[f] for f in block))

    def place_block(self, items: list[Item]) -> list[Item]:
        return items

    def live(self) -> list[Item]:
        return self.assemble(self.live_units(), self.summary_items, self.block)

    def size(self, items: list[Item]) -> int:
        return sum(self.cost_of(content) for _, _, content in items)

    def context(self) -> list[list[str]]:
        return [[kind, ref, str(self.cost_of(content))] for kind, ref, content in self.live()]

    def compactions(self) -> int:
        return self.compaction_count

    def over(self, size: int) -> bool:
        return size > self.threshold

    def candidates(self) -> list[list[int]]:
        units = self.live_units()
        return units[: max(len(units) - self.keep, 0)]

    def target(self) -> int:
        return self.low if self.low >= 0 else self.threshold

    def appends(self) -> bool:
        return self.low >= 0

    def trial(self, k: int) -> tuple[list[list[int]], list[tuple[int, str]], list[str]]:
        units = self.live_units()[k:]
        new = (self.pointer, self.queue[self.pointer])
        summaries = [*self.summary_items, new] if self.appends() else [new]
        block = self.choose_block(self.assemble(units, summaries, []))
        return units, summaries, block

    def pick_k(self, count: int) -> int:
        for k in range(1, count + 1):
            units, summaries, block = self.trial(k)
            if self.size(self.assemble(units, summaries, block)) <= self.target():
                return k
        return count

    def compact(self) -> None:
        cands = self.candidates()
        if not cands or self.pointer >= len(self.queue):
            return
        k = self.pick_k(len(cands))
        _units, summaries, block = self.trial(k)
        self.gone += [n for unit in self.live_units()[:k] for n in unit]
        self.summary_items, self.block = summaries, block
        self.pointer += 1
        self.compaction_count += 1

    def append(self, role: str, content: str, call_id: str) -> int:
        self.turns.append((role, content, call_id))
        if self.threshold >= 0 and self.over(self.size(self.live())):
            self.compact()
        prompt = self.live()
        self.reuse.append(self.shared(self.previous, prompt))
        self.previous = prompt
        return len(self.turns) - 1

    # --- level 3: prefix
    def set_stable_prefix(self, low_water: int) -> None:
        self.low = low_water

    def same_item(self, old: Item, new: Item) -> bool:
        return old[0] == new[0] and old[2] == new[2]

    def shared(self, old: list[Item], new: list[Item]) -> int:
        total = 0
        for a, b in zip(old, new, strict=False):
            if not self.same_item(a, b):
                break
            total += self.cost_of(b[2])
        return total

    def prefix_reuse(self) -> list[int]:
        return self.reuse

    # --- level 4: facts
    def pin_fact(self, fact_id: str, text: str) -> bool:
        if fact_id in self.facts:
            return False
        self.facts[fact_id] = text
        self.block = self.choose_block(self.assemble(self.live_units(), self.summary_items, []))
        return True

    def set_pin_budget(self, tokens: int) -> None:
        self.pin_budget = tokens

    def present(self, text: str, content: str) -> bool:
        return text in content

    def block_fits(self, spent: int, cost: int) -> bool:
        return self.pin_budget < 0 or spent + cost <= self.pin_budget

    def block_start(self) -> int:
        return FRAMING

    def fact_order(self) -> list[str]:
        return list(self.facts)

    def choose_block(self, others: list[Item]) -> list[str]:
        chosen, spent = [], self.block_start()
        for fact_id in self.fact_order():
            text = self.facts[fact_id]
            if any(self.present(text, content) for _, _, content in others):
                continue
            cost = self.count_tokens(text)
            if not self.block_fits(spent, cost):
                if self.stop_block_at_misfit():
                    break
                continue
            chosen.append(fact_id)
            spent += cost
        return chosen

    def stop_block_at_misfit(self) -> bool:
        return False

    def recall_items(self) -> list[Item]:
        return self.live()

    def recall(self, fact_id: str) -> bool:
        text = self.facts.get(fact_id)
        return text is not None and any(text in content for _, _, content in self.recall_items())

    def dropped(self) -> list[list[str]]:
        rows = [["turn", str(n)] for n in sorted(self.gone)]
        rows += [["fact", f] for f in self.lost_facts()]
        return rows

    def lost_facts(self) -> list[str]:
        return [f for f in self.facts if not self.recall(f)]


# ---------------------------------------------------------------- level 1
class WordsRoundedDown(Model):
    """Counts one token for each 4 characters, rounding down."""

    def word_cost(self, length: int) -> int:
        return length // 4


class WordIsOneToken(Model):
    """Counts any word as one token."""

    def word_cost(self, length: int) -> int:
        return 1 if length else 0


class PieceOfFiveCharacters(Model):
    """Counts one token for each 5 characters."""

    def word_cost(self, length: int) -> int:
        return (length + 4) // 5


class PunctuationIsFree(Model):
    """Does not charge for characters that are not letters, digits or white space."""

    def free_char(self, ch: str) -> bool:
        return ch in " \t\n" or ch not in LETTERS


class UnderscoreBelongsToWords(Model):
    """Reads `_` as part of a word."""

    def word_char(self, ch: str) -> bool:
        return ch in LETTERS or ch == "_"


class WhiteSpaceIsCharged(Model):
    """Charges a token for a tab or a newline."""

    def free_char(self, ch: str) -> bool:
        return ch == " "


class NoFraming(Model):
    """Costs a turn as its content only."""

    def cost_of(self, content: str) -> int:
        return self.count_tokens(content)


class EmptyTurnsAreFree(Model):
    """Adds the framing only to turns that have content."""

    def cost_of(self, content: str) -> int:
        return self.count_tokens(content) + (FRAMING if content else 0)


class SystemTurnsDroppedWhenOver(Model):
    """Drops the system turns when they alone are over the budget."""

    def window(self, budget, max_turns):
        system = self.system_numbers()
        if sum(self.cost_of(self.turns[n][1]) for n in system) > budget:
            return []
        return super().window(budget, max_turns)


class SystemTurnsStayInPlace(Model):
    """Lists the system turns where they were added."""

    def arrange(self, system, kept):
        return sorted(system + kept)


class SystemTurnsCountAgainstMaxTurns(Model):
    """Counts the system turns in the number of turns."""

    def unit_fits(self, unit, taken, max_turns, cost, left):
        return taken + len(self.system_numbers()) + len(unit) <= max_turns and cost <= left


class WalkSkipsTheMisfit(Model):
    """Goes on to older turns after one that does not fit."""

    def stop_at_misfit(self):
        return False


class ExactFitIsRefused(Model):
    """Needs one token to spare."""

    def unit_fits(self, unit, taken, max_turns, cost, left):
        return taken + len(unit) <= max_turns and cost < left


class MaxTurnsIsOneTooMany(Model):
    """Lets one more turn in than the limit."""

    def unit_fits(self, unit, taken, max_turns, cost, left):
        return taken + len(unit) <= max_turns + 1 and cost <= left


# ---------------------------------------------------------------- level 2
class WindowCutsInsideToolRuns(Model):
    """Treats each turn as a unit in the window."""

    def window_units(self):
        return [[n] for n, turn in enumerate(self.turns) if turn[0] != "system"]


class WindowRunsNeedOnlyTheCost(Model):
    """Takes a tool run that fits the tokens even if it does not fit the turns."""

    def unit_fits(self, unit, taken, max_turns, cost, left):
        return (taken + len(unit) <= max_turns or len(unit) > 1) and cost <= left


class RunsAreOnlyAdjacentPairs(Model):
    """Pairs a call with the next result only, so parallel calls are split."""

    def all_units(self):
        units: list[list[int]] = []
        for n, (role, _, _) in enumerate(self.turns):
            if role == "system":
                continue
            if role == "result" and units and self.turns[units[-1][-1]][0] == "call":
                units[-1].append(n)
            else:
                units.append([n])
        return units


class CompactionCutsInsideToolRuns(Model):
    """Compacts one turn at a time."""

    def all_units(self):
        return [[n] for n, turn in enumerate(self.turns) if turn[0] != "system"]


class EqualToTheThresholdCompacts(Model):
    """Compacts at the threshold and not only above it."""

    def over(self, size):
        return size >= self.threshold


class AlwaysReplacesEveryCandidate(Model):
    """Replaces all the candidates and not the smallest number."""

    def pick_k(self, count):
        return count


class ReplacesOnlyOneUnit(Model):
    """Replaces one unit and stops."""

    def pick_k(self, count):
        return 1


class KeepsRecentTurnsNotUnits(Model):
    """Counts the recent turns that are kept and not the units."""

    def candidates(self):
        units = self.live_units()
        kept, turns = 0, 0
        while kept < len(units) and turns < self.keep:
            turns += len(units[-1 - kept])
            kept += 1
        return units[: len(units) - kept]


class KeepsNoRecentUnit(Model):
    """Lets the newest units be replaced."""

    def candidates(self):
        return self.live_units()


class SummariesAreAlwaysAppended(Model):
    """Appends summaries without the stable policy."""

    def appends(self):
        return True


class SummaryReusedWhenUsedUp(Model):
    """Uses the last summary again when the list is used up."""

    def compact(self):
        if self.queue and self.pointer >= len(self.queue):
            self.pointer = len(self.queue) - 1
        super().compact()
        if self.queue and self.pointer >= len(self.queue):
            self.pointer = len(self.queue)


class NewSummariesKeepThePointer(Model):
    """Goes on from where the old list was when a new list is set."""

    def set_summaries(self, texts):
        self.queue = list(texts)


class RefIsTheCompactionCount(Model):
    """Names a summary by the number of compactions."""

    def summary_item(self, position, text):
        return ("summary", str(self.compaction_count), text)


class FailedAddsTakeANumber(Model):
    """Stores a duplicate call and returns its number."""

    def add_call(self, call_id, content):
        return self.append("call", content, call_id)


class ResultNeedsNoCall(Model):
    """Accepts a result whose call is unknown."""

    def add_result(self, call_id, content):
        answered = any(turn[0] == "result" and turn[2] == call_id for turn in self.turns)
        return -1 if answered else self.append("result", content, call_id)


class ResultMayBeRepeated(Model):
    """Accepts a second result for a call."""

    def add_result(self, call_id, content):
        has_call = any(turn[0] == "call" and turn[2] == call_id for turn in self.turns)
        return self.append("result", content, call_id) if has_call else -1


class WindowForgetsReplacedTurns(Model):
    """Lets the window skip the turns that compaction replaced."""

    def window_units(self):
        return [unit for unit in self.all_units() if unit[0] not in self.gone]


class SystemTurnsCanBeReplaced(Model):
    """Includes the system turns in the units."""

    def all_units(self):
        units = super().all_units()
        return [[n] for n in self.system_numbers()] + units


class ReplacesTheNewestCandidates(Model):
    """Takes the candidates from the newest end."""

    def trial(self, k):
        units = self.live_units()
        cands = self.candidates()
        removed = cands[len(cands) - k :]
        remaining = [u for u in units if u not in removed]
        new = (self.pointer, self.queue[self.pointer])
        summaries = [*self.summary_items, new] if self.appends() else [new]
        return remaining, summaries, self.choose_block(self.assemble(remaining, summaries, []))

    def compact(self):
        cands = self.candidates()
        if not cands or self.pointer >= len(self.queue):
            return
        k = self.pick_k(len(cands))
        _units, summaries, block = self.trial(k)
        self.gone += [n for unit in cands[len(cands) - k :] for n in unit]
        self.summary_items, self.block = summaries, block
        self.pointer += 1
        self.compaction_count += 1


class CompactsEvenWhenNoSummaryIsLeft(Model):
    """Drops the oldest candidate with an empty summary when the list is used up."""

    def compact(self):
        if self.queue and self.pointer >= len(self.queue):
            self.queue.append("")
        super().compact()


# ---------------------------------------------------------------- level 3
class LowWaterMarkIgnored(Model):
    """Appends but still compacts down to the threshold."""

    def target(self):
        return self.threshold


class StablePolicyStillReplaces(Model):
    """Goes down to the mark but replaces the single summary."""

    def appends(self):
        return False


class MarkAppliesToTheTrigger(Model):
    """Triggers at the mark and not at the threshold."""

    def over(self, size):
        return size > (self.low if self.low >= 0 else self.threshold)


class ReuseIgnoresTheKind(Model):
    """Compares the text only."""

    def same_item(self, old, new):
        return old[2] == new[2]


class ReuseComparesTheRef(Model):
    """Compares the turn numbers as well."""

    def same_item(self, old, new):
        return old == new


class ReuseCountsContentWithoutFraming(Model):
    """Counts the tokens of the shared items without the framing."""

    def shared(self, old, new):
        total = 0
        for a, b in zip(old, new, strict=False):
            if not self.same_item(a, b):
                break
            total += self.count_tokens(b[2])
        return total


class ReuseGoesOnAfterAMismatch(Model):
    """Counts the equal items after the first different one."""

    def shared(self, old, new):
        return sum(
            self.cost_of(b[2]) for a, b in zip(old, new, strict=False) if self.same_item(a, b)
        )


class FirstAddReusesItself(Model):
    """Counts the first prompt as shared."""

    def shared(self, old, new):
        return super().shared(old or new, new)


class FailedAddsMakeAPrompt(Model):
    """Records a prompt for a failed add."""

    def add_result(self, call_id, content):
        number = super().add_result(call_id, content)
        if number == -1:
            prompt = self.live()
            self.reuse.append(self.shared(self.previous, prompt))
            self.previous = prompt
        return number


class ReuseMeasuresOnlyTheSystemTurns(Model):
    """Reports the cost of the system turns whatever the prompt shares."""

    def shared(self, old, new):
        if not old:
            return 0
        return sum(self.cost_of(c) for k, _, c in new if k == "system")


class ReuseIsComparedWithTheFirstPrompt(Model):
    """Compares each prompt with the first one."""

    def append(self, role, content, call_id):
        number = super().append(role, content, call_id)
        if len(self.reuse) == 1:
            self.first = list(self.previous)
        else:
            self.previous = self.first
            self.reuse[-1] = self.shared(self.first, self.live())
        return number


# ---------------------------------------------------------------- level 4
class BlockComesBeforeTheSummaries(Model):
    """Places the pinned block right after the system turns."""

    def place_block(self, items):
        pinned = [i for i in items if i[0] == "pinned"]
        rest = [i for i in items if i[0] != "pinned"]
        systems = [i for i in rest if i[0] == "system"]
        return [*systems, *pinned, *rest[len(systems) :]]


class BlockComesLast(Model):
    """Places the pinned block after the turns."""

    def place_block(self, items):
        return [i for i in items if i[0] != "pinned"] + [i for i in items if i[0] == "pinned"]


class BlockIsChosenAtEveryAdd(Model):
    """Chooses the block again at each add."""

    def append(self, role, content, call_id):
        self.turns.append((role, content, call_id))
        self.turns.pop()
        self.block = self.choose_block(self.assemble(self.live_units(), self.summary_items, []))
        return super().append(role, content, call_id)


class BlockIsNotChosenAtPinTime(Model):
    """Chooses the block only when a compaction happens."""

    def pin_fact(self, fact_id, text):
        if fact_id in self.facts:
            return False
        self.facts[fact_id] = text
        return True


class BlockCarriesFactsThatAreThere(Model):
    """Puts every fact in the block."""

    def present(self, text, content):
        return False


class PresenceIgnoresLetterCase(Model):
    """Finds a fact in another item whatever the case."""

    def present(self, text, content):
        return text.lower() in content.lower()


class PresenceIgnoresSummaries(Model):
    """Looks for a fact in the turns only."""

    def choose_block(self, others):
        return super().choose_block([i for i in others if i[0] != "summary"])


class PresenceIgnoresSystemTurns(Model):
    """Looks for a fact in the conversation only."""

    def choose_block(self, others):
        return super().choose_block([i for i in others if i[0] != "system"])


class BudgetStopsAtTheFirstMisfit(Model):
    """Stops choosing facts at the first that does not fit."""

    def stop_block_at_misfit(self):
        return True


class BudgetLeavesOutTheFraming(Model):
    """Does not count the framing of the block."""

    def block_start(self):
        return 0


class BudgetIsOnlyAdvice(Model):
    """Does not limit the block."""

    def block_fits(self, spent, cost):
        return True


class BudgetMustBeBeaten(Model):
    """Needs a token to spare in the budget."""

    def block_fits(self, spent, cost):
        return self.pin_budget < 0 or spent + cost < self.pin_budget


class BlockIsNotInTheSize(Model):
    """Leaves the block out when adding up the context."""

    def size(self, items):
        return super().size([i for i in items if i[0] != "pinned"])


class SearchForKIgnoresTheBlock(Model):
    """Chooses k without the block that the replacement leaves."""

    def pick_k(self, count):
        for k in range(1, count + 1):
            units, summaries, _ = self.trial(k)
            if self.size(self.assemble(units, summaries, [])) <= self.target():
                return k
        return count


class BlockIsChosenBeforeTheReplacement(Model):
    """Keeps the old block through a compaction."""

    def compact(self):
        old = list(self.block)
        super().compact()
        self.block = old


class FactsAreLostInPinOrderLast(Model):
    """Lists the lost facts in alphabetical order of id."""

    def lost_facts(self):
        return sorted(super().lost_facts())


class DroppedListsFactsFirst(Model):
    """Lists the lost facts before the turns."""

    def dropped(self):
        rows = super().dropped()
        return [r for r in rows if r[0] == "fact"] + [r for r in rows if r[0] == "turn"]


class DroppedLosesFactsHeldBySummaries(Model):
    """Counts a fact that only a summary holds as lost."""

    def recall_items(self):
        return [i for i in self.live() if i[0] != "summary"]


class RecallOnlyLooksInTurns(Model):
    """Does not look in the pinned block."""

    def recall_items(self):
        return [i for i in self.live() if i[0] not in ("pinned",)]


class RecallIgnoresLetterCase(Model):
    """Finds the text whatever the case."""

    def recall(self, fact_id):
        text = self.facts.get(fact_id)
        return text is not None and any(text.lower() in c.lower() for _, _, c in self.live())


class UnknownFactsAreRecalled(Model):
    """Says true for a fact that was never pinned."""

    def recall(self, fact_id):
        return fact_id not in self.facts or super().recall(fact_id)


class PinTwiceReplaces(Model):
    """Replaces the text of a fact that is pinned again."""

    def pin_fact(self, fact_id, text):
        was = fact_id in self.facts
        self.facts[fact_id] = text
        self.block = self.choose_block(self.assemble(self.live_units(), self.summary_items, []))
        return not was


class BlockOrderIsAlphabetical(Model):
    """Orders the facts of the block by id."""

    def fact_order(self):
        return sorted(self.facts)


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
    except (IndexError, KeyError, ValueError, TypeError, AttributeError):
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


def test_the_hidden_cases_reach_every_kind_of_item_and_report_row():
    kinds: set[str] = set()
    rows: set[str] = set()
    for case in HIDDEN_CASES:
        for op, got in zip(case["ops"], case["expected"], strict=True):
            if op == "context":
                kinds.update(row[0] for row in got)
            elif op == "dropped":
                rows.update(row[0] for row in got)
    assert kinds == {"system", "user", "assistant", "call", "result", "summary", "pinned"}
    assert rows == {"turn", "fact"}
