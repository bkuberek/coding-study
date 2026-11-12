"""raft-sim promises that its hidden cases catch the classic mistakes of implementing Raft: votes
given for stale terms, twice in a term or to a candidate whose log is behind, terms not adopted
from replies, a majority miscounted, a candidate that ignores the leader of its term, logs cut
short by a late message or left with conflicting entries, an entry of an earlier term committed
by counting copies, a probe moved twice by one failure, and a partition that lets messages
through. These tests replay every case against a model of the cluster written from the statement,
which must give every expected output, and against that model with one mistake planted at a time,
which some hidden case must fail. While the correct model replays a case, they check after every
step the safety properties of the Raft paper: election safety, leader append-only, log matching,
leader completeness and state machine safety."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0372-raft-sim"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

Entry = tuple[int, str]
Node = dict[str, Any]
Message = dict[str, Any]


class Model:
    """The cluster as the statement words it: nodes are dictionaries, messages are dictionaries
    waiting in a table by id, and one method per rule, so that each mistake below overrides one
    rule."""

    def __init__(self, nodes: list[str]) -> None:
        self.order = list(nodes)
        self.nodes: dict[str, Node] = {name: self.fresh() for name in nodes}
        self.flight: dict[int, Message] = {}
        self.ids = 0
        self.side = dict.fromkeys(nodes, 0)
        self.sent: list[int] = []

    @staticmethod
    def fresh() -> Node:
        return {
            "term": 0,
            "vote": "",
            "log": [],
            "commit": 0,
            "applied": [],
            "role": "follower",
            "votes": set(),
            "next": {},
            "match": {},
        }

    # --- helpers
    def others(self, name: str) -> list[str]:
        return [other for other in self.order if other != name]

    def majority(self, count: int) -> bool:
        return count > len(self.order) // 2

    def last(self, node: Node) -> tuple[int, int]:
        """(last term, last index) of a node's log."""
        return (node["log"][-1][0] if node["log"] else 0, len(node["log"]))

    def term_at(self, node: Node, index: int) -> int:
        return node["log"][index - 1][0] if 0 < index <= len(node["log"]) else 0

    def cut(self, a: str, b: str) -> bool:
        return self.side[a] != self.side[b]

    def send(self, message: Message) -> None:
        if self.cut(message["from"], message["to"]):
            return
        self.ids += 1
        self.flight[self.ids] = message
        self.sent.append(self.ids)

    def adopt(self, node: Node, term: int) -> None:
        if term > node["term"]:
            node.update(term=term, vote="", role="follower", votes=set())

    def apply(self, node: Node, upto: int) -> None:
        if upto > node["commit"]:
            node["applied"] += [command for _, command in node["log"][node["commit"] : upto]]
            node["commit"] = upto

    # --- level 1
    def load(self, node: str, term: int, vote: str, entries: list[str]) -> None:
        log = [(int(text.partition(":")[0]), text.partition(":")[2]) for text in entries]
        self.nodes[node] = {**self.fresh(), "term": term, "vote": vote, "log": log}

    def log_ok(self, node: Node, last_index: int, last_term: int) -> bool:
        mine_term, mine_index = self.last(node)
        if last_term != mine_term:
            return last_term > mine_term
        return last_index >= mine_index

    def decide(self, name: str, candidate: str, term: int, last_index: int, last_term: int) -> str:
        node = self.nodes[name]
        self.adopt(node, term)
        if term < node["term"]:
            return "stale-term"
        if node["vote"] and node["vote"] != candidate:
            return "already-voted"
        if not self.log_ok(node, last_index, last_term):
            return "stale-log"
        node["vote"] = candidate
        return "granted"

    def request_vote(
        self, node: str, candidate: str, term: int, last_log_index: int, last_log_term: int
    ) -> str:
        return self.decide(node, candidate, term, last_log_index, last_log_term)

    def voted_for(self, node: str) -> str:
        return self.nodes[node]["vote"]

    def status(self) -> list[str]:
        return [f"{n} {self.nodes[n]['role']} {self.nodes[n]['term']}" for n in self.order]

    # --- level 2
    def count_self(self, name: str) -> set[str]:
        return {name}

    def timeout(self, node: str) -> list[int]:
        self.sent = []
        state = self.nodes[node]
        if state["role"] == "leader":
            return self.sent
        state.update(term=state["term"] + 1, role="candidate", vote=node)
        state["votes"] = self.count_self(node)
        if self.majority(len(state["votes"])):
            self.win(node)
        else:
            last_term, last_index = self.last(state)
            for other in self.others(node):
                self.send(
                    {
                        "kind": "vote",
                        "from": node,
                        "to": other,
                        "term": state["term"],
                        "last_index": last_index,
                        "last_term": last_term,
                    }
                )
        return self.sent

    def win(self, name: str) -> None:
        node = self.nodes[name]
        node.update(role="leader", votes=set())
        node["next"] = {other: len(node["log"]) + 1 for other in self.others(name)}
        node["match"] = dict.fromkeys(self.others(name), 0)
        for other in self.others(name):
            self.append_to(name, other)

    def append_to(self, name: str, other: str) -> None:
        node = self.nodes[name]
        start = node["next"][other]
        self.send(
            {
                "kind": "append",
                "from": name,
                "to": other,
                "term": node["term"],
                "prev": start - 1,
                "prev_term": self.term_at(node, start - 1),
                "entries": list(node["log"][start - 1 :]),
                "commit": node["commit"],
            }
        )

    def heartbeat(self, node: str) -> list[int]:
        self.sent = []
        if self.nodes[node]["role"] == "leader":
            for other in self.others(node):
                self.append_to(node, other)
        return self.sent

    def deliver(self, message: int) -> list[int]:
        self.sent = []
        found = self.take(message)
        if found is not None:
            getattr(self, "on_" + found["kind"].replace("-", "_"))(found)
        return self.sent

    def take(self, message: int) -> Message | None:
        return self.flight.pop(message, None)

    def lose(self, message: int) -> None:
        self.flight.pop(message, None)

    def on_vote(self, message: Message) -> None:
        name = message["to"]
        answer = self.decide(
            name, message["from"], message["term"], message["last_index"], message["last_term"]
        )
        self.send(
            {
                "kind": "vote-reply",
                "from": name,
                "to": message["from"],
                "term": self.nodes[name]["term"],
                "granted": answer == "granted",
            }
        )

    def counts(self, node: Node, message: Message) -> bool:
        return node["role"] == "candidate" and message["term"] == node["term"]

    def on_vote_reply(self, message: Message) -> None:
        node = self.nodes[message["to"]]
        self.step_down_on_reply(node, message["term"])
        if self.counts(node, message) and message["granted"]:
            node["votes"].add(message["from"])
            if self.majority(len(node["votes"])):
                self.win(message["to"])

    def step_down_on_reply(self, node: Node, term: int) -> None:
        self.adopt(node, term)

    # --- level 3
    def yields(self, node: Node, message: Message) -> None:
        if node["role"] == "candidate":
            node.update(role="follower", votes=set())

    def consistent(self, node: Node, prev: int, prev_term: int) -> bool:
        return prev <= len(node["log"]) and self.term_at(node, prev) == prev_term

    def store(self, node: Node, prev: int, entries: list[Entry]) -> None:
        for offset, entry in enumerate(entries):
            index = prev + 1 + offset
            if index <= len(node["log"]):
                if node["log"][index - 1][0] == entry[0]:
                    continue
                del node["log"][index - 1 :]
            node["log"].append(entry)

    def on_append(self, message: Message) -> None:
        name, leader = message["to"], message["from"]
        node = self.nodes[name]
        self.adopt(node, message["term"])
        reply = {
            "kind": "append-reply",
            "from": name,
            "to": leader,
            "term": node["term"],
            "success": False,
            "index": message["prev"],
        }
        if message["term"] == node["term"]:
            self.yields(node, message)
            if self.consistent(node, message["prev"], message["prev_term"]):
                self.store(node, message["prev"], message["entries"])
                last_new = message["prev"] + len(message["entries"])
                self.apply(node, min(message["commit"], last_new))
                reply.update(success=True, index=last_new)
        self.send(reply)

    def on_append_reply(self, message: Message) -> None:
        name, peer = message["to"], message["from"]
        node = self.nodes[name]
        self.step_down_on_reply(node, message["term"])
        if node["role"] != "leader" or message["term"] != node["term"]:
            return
        if message["success"]:
            node["match"][peer] = max(node["match"][peer], message["index"])
            node["next"][peer] = max(node["next"][peer], message["index"] + 1)
            self.advance(name)
        else:
            self.retry(name, peer, message["index"])

    def retry(self, name: str, peer: str, index: int) -> None:
        node = self.nodes[name]
        if index == node["next"][peer] - 1 and node["next"][peer] > 1:
            node["next"][peer] -= 1
            self.append_to(name, peer)

    def copies(self, name: str, index: int) -> int:
        node = self.nodes[name]
        return 1 + sum(1 for match in node["match"].values() if match >= index)

    def committable(self, node: Node, index: int) -> bool:
        return self.term_at(node, index) == node["term"]

    def advance(self, name: str) -> None:
        node = self.nodes[name]
        for index in range(len(node["log"]), node["commit"], -1):
            if self.committable(node, index) and self.majority(self.copies(name, index)):
                self.apply(node, index)
                return

    def propose(self, node: str, command: str) -> int:
        state = self.nodes[node]
        if state["role"] != "leader":
            return -1
        state["log"].append((state["term"], command))
        self.advance(node)
        return len(state["log"])

    def log(self, node: str) -> list[str]:
        return [f"{term}:{command}" for term, command in self.nodes[node]["log"]]

    def commit_index(self, node: str) -> int:
        return self.nodes[node]["commit"]

    # --- level 4
    def partition(self, groups: list[list[str]]) -> None:
        self.side = {name: number for number, group in enumerate(groups) for name in group}
        self.flight = {key: m for key, m in self.flight.items() if not self.cut(m["from"], m["to"])}

    def heal(self) -> None:
        self.side = dict.fromkeys(self.order, 0)

    def applied(self, node: str) -> list[str]:
        return list(self.nodes[node]["applied"])


# ------------------------------------------------------------------ level 1 mistakes
class GrantsStaleTerms(Model):
    """Never refuses a request for being from an older term."""

    def decide(self, name: str, candidate: str, term: int, last_index: int, last_term: int) -> str:
        node = self.nodes[name]
        self.adopt(node, term)
        if node["vote"] and node["vote"] != candidate:
            return "already-voted"
        if not self.log_ok(node, last_index, last_term):
            return "stale-log"
        node["vote"] = candidate
        return "granted"


class AdoptsTermOnlyWhenGranting(Model):
    """Moves to the candidate's term only when it grants the vote."""

    def decide(self, name: str, candidate: str, term: int, last_index: int, last_term: int) -> str:
        node = self.nodes[name]
        if term < node["term"]:
            return "stale-term"
        fresh = term > node["term"]
        if not fresh and node["vote"] and node["vote"] != candidate:
            return "already-voted"
        if not self.log_ok(node, last_index, last_term):
            return "stale-log"
        self.adopt(node, term)
        node["vote"] = candidate
        return "granted"


class KeepsTheVoteOfAnOldTerm(Model):
    """Keeps the recorded vote when a new term starts."""

    def adopt(self, node: Node, term: int) -> None:
        if term > node["term"]:
            node.update(term=term, role="follower", votes=set())


class ComparesLengthFirst(Model):
    """Compares log lengths before last terms."""

    def log_ok(self, node: Node, last_index: int, last_term: int) -> bool:
        mine_term, mine_index = self.last(node)
        if last_index != mine_index:
            return last_index > mine_index
        return last_term >= mine_term


class NeedsALongerLog(Model):
    """Requires the candidate's log to be strictly longer when the last terms are equal."""

    def log_ok(self, node: Node, last_index: int, last_term: int) -> bool:
        mine_term, mine_index = self.last(node)
        if last_term != mine_term:
            return last_term > mine_term
        return last_index > mine_index or (last_index == 0 and mine_index == 0)


class ComparesTheCandidatesTerm(Model):
    """Compares the candidate's current term instead of its last log term."""

    def request_vote(
        self, node: str, candidate: str, term: int, last_log_index: int, last_log_term: int
    ) -> str:
        return self.decide(node, candidate, term, last_log_index, term)


class RefusesTheSameCandidateTwice(Model):
    """Refuses a second request of the candidate it already voted for."""

    def decide(self, name: str, candidate: str, term: int, last_index: int, last_term: int) -> str:
        node = self.nodes[name]
        if term == node["term"] and node["vote"] == candidate:
            return "already-voted"
        return super().decide(name, candidate, term, last_index, last_term)


class ChecksTheLogBeforeTheVote(Model):
    """Reports a stale log before a vote already given."""

    def decide(self, name: str, candidate: str, term: int, last_index: int, last_term: int) -> str:
        node = self.nodes[name]
        self.adopt(node, term)
        if term < node["term"]:
            return "stale-term"
        if not self.log_ok(node, last_index, last_term):
            return "stale-log"
        if node["vote"] and node["vote"] != candidate:
            return "already-voted"
        node["vote"] = candidate
        return "granted"


# ------------------------------------------------------------------ level 2 mistakes
class HalfIsAMajority(Model):
    """Counts half of the cluster as a majority."""

    def majority(self, count: int) -> bool:
        return 2 * count >= len(self.order)


class CountsVotesOfAnyTerm(Model):
    """Counts every granted vote, whatever term it was for."""

    def counts(self, node: Node, message: Message) -> bool:
        return node["role"] == "candidate"


class IgnoresTermsInReplies(Model):
    """Adopts higher terms from requests only, never from replies."""

    def step_down_on_reply(self, node: Node, term: int) -> None:
        return None


class CandidateIgnoresTheLeaderOfItsTerm(Model):
    """Stays a candidate when the leader of its own term contacts it."""

    def yields(self, node: Node, message: Message) -> None:
        return None


class LeaderTimesOut(Model):
    """Starts an election when the leader's election timer fires."""

    def timeout(self, node: str) -> list[int]:
        state = self.nodes[node]
        if state["role"] == "leader":
            state["role"] = "follower"
        return super().timeout(node)


class NoHeartbeatOnWinning(Model):
    """Becomes leader without telling the others."""

    def win(self, name: str) -> None:
        node = self.nodes[name]
        node.update(role="leader", votes=set())
        node["next"] = {other: len(node["log"]) + 1 for other in self.others(name)}
        node["match"] = dict.fromkeys(self.others(name), 0)


class ForgetsItsOwnVote(Model):
    """Counts only the votes of other nodes."""

    def count_self(self, name: str) -> set[str]:
        return set()


class LostMessagesStillArrive(Model):
    """Keeps a lost message deliverable."""

    def lose(self, message: int) -> None:
        return None


# ------------------------------------------------------------------ level 3 mistakes
class CommitsEarlierTermsByCounting(Model):
    """Commits any entry stored on a majority, whatever its term."""

    def committable(self, node: Node, index: int) -> bool:
        return True


class CutsTheLogAfterEveryRequest(Model):
    """Deletes everything after prevLogIndex before appending."""

    def store(self, node: Node, prev: int, entries: list[Entry]) -> None:
        del node["log"][prev:]
        node["log"].extend(entries)


class OverwritesWithoutCutting(Model):
    """Replaces a conflicting entry but keeps the entries after it."""

    def store(self, node: Node, prev: int, entries: list[Entry]) -> None:
        for offset, entry in enumerate(entries):
            index = prev + 1 + offset
            if index <= len(node["log"]):
                node["log"][index - 1] = entry
            else:
                node["log"].append(entry)


class ChecksOnlyTheLength(Model):
    """Accepts any log long enough, without comparing the term at prevLogIndex."""

    def consistent(self, node: Node, prev: int, prev_term: int) -> bool:
        return prev <= len(node["log"])


class LeaderDoesNotCountItself(Model):
    """Counts the copies on the followers only."""

    def copies(self, name: str, index: int) -> int:
        return super().copies(name, index) - 1


class MovesNextIndexOnEveryFailure(Model):
    """Lowers nextIndex and retries on every failure reply, stale or not."""

    def retry(self, name: str, peer: str, index: int) -> None:
        node = self.nodes[name]
        if node["next"][peer] > 1:
            node["next"][peer] -= 1
            self.append_to(name, peer)


class NoRetryAfterAFailure(Model):
    """Lowers nextIndex but waits for the next heartbeat to try again."""

    def retry(self, name: str, peer: str, index: int) -> None:
        node = self.nodes[name]
        if index == node["next"][peer] - 1 and node["next"][peer] > 1:
            node["next"][peer] -= 1


class AnyNodeAcceptsCommands(Model):
    """Lets every node append a proposed command."""

    def propose(self, node: str, command: str) -> int:
        state = self.nodes[node]
        if state["role"] == "leader":
            return super().propose(node, command)
        state["log"].append((state["term"], command))
        return len(state["log"])


# ------------------------------------------------------------------ level 4 mistakes
class PartitionSparesMessagesInFlight(Model):
    """Cuts the links for new messages only."""

    def partition(self, groups: list[list[str]]) -> None:
        self.side = {name: number for number, group in enumerate(groups) for name in group}


class LostSendsStillTakeAnId(Model):
    """Numbers a message even when the partition loses it."""

    def send(self, message: Message) -> None:
        self.ids += 1
        if not self.cut(message["from"], message["to"]):
            self.flight[self.ids] = message
            self.sent.append(self.ids)


class HealDoesNothing(Model):
    """Leaves the partition in place."""

    def heal(self) -> None:
        return None


class AppliesWhenAppending(Model):
    """Applies entries as soon as they are stored."""

    def store(self, node: Node, prev: int, entries: list[Entry]) -> None:
        super().store(node, prev, entries)
        node["applied"] = [command for _, command in node["log"]]

    def propose(self, node: str, command: str) -> int:
        index = super().propose(node, command)
        state = self.nodes[node]
        state["applied"] = [c for _, c in state["log"]]
        return index


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


class Safety:
    """The properties of Figure 3 of the Raft paper, checked on the model after every step."""

    def __init__(self) -> None:
        self.leaders: dict[int, str] = {}
        self.leader_logs: dict[tuple[str, int], list[Entry]] = {}
        self.committed: dict[int, tuple[Entry, int]] = {}
        self.first_applied: dict[int, str] = {}

    def check(self, model: Model) -> None:
        nodes = model.nodes
        for name, node in nodes.items():
            if node["role"] == "leader":
                assert self.leaders.setdefault(node["term"], name) == name, "election safety"
                key = (name, node["term"])
                before = self.leader_logs.get(key, [])
                assert node["log"][: len(before)] == before, "leader append-only"
                self.leader_logs[key] = list(node["log"])
        for a in nodes.values():
            for b in nodes.values():
                for i in range(min(len(a["log"]), len(b["log"])), 0, -1):
                    if a["log"][i - 1][0] == b["log"][i - 1][0]:
                        assert a["log"][:i] == b["log"][:i], "log matching"
                        break
        for node in nodes.values():
            for index in range(1, node["commit"] + 1):
                entry = node["log"][index - 1]
                seen, term = self.committed.setdefault(index, (entry, node["term"]))
                assert seen == entry, "a committed entry changed"
                self.committed[index] = (entry, min(term, node["term"]))
        for node in nodes.values():
            if node["role"] != "leader":
                continue
            for index, (entry, term) in self.committed.items():
                if node["term"] > term:
                    assert node["log"][index - 1 : index] == [entry], "leader completeness"
        for node in nodes.values():
            for index, command in enumerate(node["applied"], start=1):
                first = self.first_applied.setdefault(index, command)
                assert first == command, "state machine safety"


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def run(
    model_type: type[Model], case: Mapping[str, Any], safety: Safety | None = None
) -> list[Any]:
    model = model_type(*case["args"][0])
    outputs: list[Any] = [None]
    for op, arguments in zip(case["ops"][1:], case["args"][1:], strict=True):
        outputs.append(getattr(model, snake_case(op))(*arguments))
        if safety is not None:
            safety.check(model)
    return outputs


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return run(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, AttributeError):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert run(Model, case) == case["expected"]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_every_step_of_every_case_keeps_the_safety_properties(case):
    run(Model, case, Safety())


@pytest.mark.parametrize(
    ("mistake", "case_id", "broken"),
    [
        (HalfIsAMajority, "ex4", "election safety"),
        (ChecksOnlyTheLength, "h20", "log matching"),
        (CommitsEarlierTermsByCounting, "h29", "leader completeness"),
    ],
)
def test_the_safety_checks_catch_an_unsafe_cluster(mistake, case_id, broken):
    """The checks are not vacuous: the schedules break them as soon as one rule is wrong."""
    case = next(case for case in CASES if case["id"] == case_id)
    with pytest.raises(AssertionError, match=broken):
        run(mistake, case, Safety())


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_give_every_vote_answer_and_both_roles_of_a_leader_change():
    answers = {
        got
        for case in HIDDEN_CASES
        for op, got in zip(case["ops"], case["expected"], strict=True)
        if op == "requestVote"
    }
    assert answers == {"granted", "stale-term", "already-voted", "stale-log"}
    statuses = [
        line
        for case in HIDDEN_CASES
        if case["level"] == 4
        for op, got in zip(case["ops"], case["expected"], strict=True)
        if op == "status"
        for line in got
    ]
    assert any(line.endswith(" leader 1") for line in statuses)
    assert any(" follower " in line for line in statuses)


def test_a_committed_entry_survives_a_partition_and_a_new_leader():
    """In the Figure 8 case the entry stored on a majority but never committed is replaced, and
    every node ends having applied the same commands."""
    case = next(case for case in CASES if case["id"] == "h29")
    model = Model(*case["args"][0])
    safety = Safety()
    for op, arguments in zip(case["ops"][1:], case["args"][1:], strict=True):
        getattr(model, snake_case(op))(*arguments)
        safety.check(model)
    applied = {name: node["applied"] for name, node in model.nodes.items()}
    assert applied["s1"] == applied["s5"] == ["c", "e"]
    assert all(commands == ["c", "e"][: len(commands)] for commands in applied.values())
