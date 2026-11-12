from dataclasses import dataclass, field

FOLLOWER, CANDIDATE, LEADER = "follower", "candidate", "leader"


@dataclass
class Message:
    """One RPC request or reply in flight. Only the fields of its kind are used."""

    kind: str
    sender: str
    receiver: str
    term: int
    last_index: int = 0
    last_term: int = 0
    granted: bool = False
    prev_index: int = 0
    prev_term: int = 0
    entries: list[tuple[int, str]] = field(default_factory=list)
    leader_commit: int = 0
    success: bool = False
    index: int = 0


class Node:
    """The state of one server: persistent (term, vote, log), volatile (commit index, role) and
    the leader's bookkeeping, plus the commands applied to its state machine."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.term = 0
        self.voted_for = ""
        self.log: list[tuple[int, str]] = []
        self.commit = 0
        self.applied: list[str] = []
        self.role = FOLLOWER
        self.votes: set[str] = set()
        self.next_index: dict[str, int] = {}
        self.match_index: dict[str, int] = {}

    def last_index(self) -> int:
        return len(self.log)

    def term_at(self, index: int) -> int:
        return self.log[index - 1][0] if index > 0 else 0

    def observe(self, term: int) -> None:
        """A term greater than the node's own makes it a follower of that term with no vote."""
        if term > self.term:
            self.term, self.voted_for, self.role, self.votes = term, "", FOLLOWER, set()

    def decide_vote(self, candidate: str, term: int, last_index: int, last_term: int) -> str:
        self.observe(term)
        if term < self.term:
            return "stale-term"
        if self.voted_for not in ("", candidate):
            return "already-voted"
        if (last_term, last_index) < (self.term_at(self.last_index()), self.last_index()):
            return "stale-log"
        self.voted_for = candidate
        return "granted"

    def commit_to(self, index: int) -> None:
        """Raises the commit index and applies the newly committed commands in log order."""
        if index > self.commit:
            self.applied.extend(command for _, command in self.log[self.commit : index])
            self.commit = index


class RaftCluster:
    """A cluster of Raft nodes on a scripted network. Messages wait in flight until the script
    delivers or loses them; every node reacts to one message at a time by the rules of the Raft
    summary, and every message it sends gets the next id."""

    def __init__(self, nodes: list[str]) -> None:
        self._order = list(nodes)
        self._nodes = {name: Node(name) for name in nodes}
        self._flight: dict[int, Message] = {}
        self._last_id = 0
        self._group = dict.fromkeys(nodes, 0)
        self._sent: list[int] = []

    def _peers(self, name: str) -> list[str]:
        return [peer for peer in self._order if peer != name]

    def _majority(self, count: int) -> bool:
        return 2 * count > len(self._order)

    def _send(self, message: Message) -> None:
        if self._group[message.sender] != self._group[message.receiver]:
            return
        self._last_id += 1
        self._flight[self._last_id] = message
        self._sent.append(self._last_id)

    def _append_to(self, leader: Node, peer: str) -> None:
        start = leader.next_index[peer]
        self._send(
            Message(
                "append",
                leader.name,
                peer,
                leader.term,
                prev_index=start - 1,
                prev_term=leader.term_at(start - 1),
                entries=leader.log[start - 1 :],
                leader_commit=leader.commit,
            )
        )

    def _become_leader(self, node: Node) -> None:
        node.role, node.votes = LEADER, set()
        node.next_index = dict.fromkeys(self._peers(node.name), node.last_index() + 1)
        node.match_index = dict.fromkeys(self._peers(node.name), 0)
        for peer in self._peers(node.name):
            self._append_to(node, peer)

    def _advance_commit(self, leader: Node) -> None:
        """Commits the highest entry of the leader's own term that a majority stores."""
        for index in range(leader.last_index(), leader.commit, -1):
            if leader.term_at(index) != leader.term:
                return
            stored = 1 + sum(match >= index for match in leader.match_index.values())
            if self._majority(stored):
                leader.commit_to(index)
                return

    # Level 1
    def load(self, node: str, term: int, vote: str, entries: list[str]) -> None:
        state = self._nodes[node]
        state.term, state.voted_for, state.role, state.votes = term, vote, FOLLOWER, set()
        state.log = [(int(text.split(":", 1)[0]), text.split(":", 1)[1]) for text in entries]
        state.commit, state.applied = 0, []

    def request_vote(
        self, node: str, candidate: str, term: int, last_log_index: int, last_log_term: int
    ) -> str:
        return self._nodes[node].decide_vote(candidate, term, last_log_index, last_log_term)

    def voted_for(self, node: str) -> str:
        return self._nodes[node].voted_for

    def status(self) -> list[str]:
        return [f"{name} {self._nodes[name].role} {self._nodes[name].term}" for name in self._order]

    # Level 2
    def timeout(self, node: str) -> list[int]:
        self._sent = []
        state = self._nodes[node]
        if state.role == LEADER:
            return []
        state.term += 1
        state.role, state.voted_for, state.votes = CANDIDATE, node, {node}
        if self._majority(len(state.votes)):
            self._become_leader(state)
            return self._sent
        for peer in self._peers(node):
            vote = Message("vote", node, peer, state.term)
            vote.last_index, vote.last_term = state.last_index(), state.term_at(state.last_index())
            self._send(vote)
        return self._sent

    def heartbeat(self, node: str) -> list[int]:
        self._sent = []
        state = self._nodes[node]
        if state.role == LEADER:
            for peer in self._peers(node):
                self._append_to(state, peer)
        return self._sent

    def deliver(self, message: int) -> list[int]:
        self._sent = []
        found = self._flight.pop(message, None)
        if found is not None:
            receiver = self._nodes[found.receiver]
            handlers = {
                "vote": self._on_vote,
                "vote-reply": self._on_vote_reply,
                "append": self._on_append,
                "append-reply": self._on_append_reply,
            }
            handlers[found.kind](receiver, found)
        return self._sent

    def lose(self, message: int) -> None:
        self._flight.pop(message, None)

    def _on_vote(self, node: Node, message: Message) -> None:
        result = node.decide_vote(
            message.sender, message.term, message.last_index, message.last_term
        )
        reply = Message("vote-reply", node.name, message.sender, node.term)
        reply.granted = result == "granted"
        self._send(reply)

    def _on_vote_reply(self, node: Node, message: Message) -> None:
        node.observe(message.term)
        if node.role != CANDIDATE or message.term != node.term or not message.granted:
            return
        node.votes.add(message.sender)
        if self._majority(len(node.votes)):
            self._become_leader(node)

    def _on_append(self, node: Node, message: Message) -> None:
        node.observe(message.term)
        reply = Message("append-reply", node.name, message.sender, node.term)
        reply.index = message.prev_index
        if message.term < node.term:
            self._send(reply)
            return
        if node.role == CANDIDATE:
            node.role, node.votes = FOLLOWER, set()
        prev = message.prev_index
        if prev > node.last_index() or node.term_at(prev) != message.prev_term:
            self._send(reply)
            return
        for offset, entry in enumerate(message.entries):
            index = prev + 1 + offset
            if index <= node.last_index() and node.term_at(index) != entry[0]:
                del node.log[index - 1 :]
            if index > node.last_index():
                node.log.append(entry)
        last_new = prev + len(message.entries)
        if message.leader_commit > node.commit:
            node.commit_to(min(message.leader_commit, last_new))
        reply.success, reply.index = True, last_new
        self._send(reply)

    def _on_append_reply(self, node: Node, message: Message) -> None:
        node.observe(message.term)
        if node.role != LEADER or message.term != node.term:
            return
        peer = message.sender
        if message.success:
            node.match_index[peer] = max(node.match_index[peer], message.index)
            node.next_index[peer] = max(node.next_index[peer], message.index + 1)
            self._advance_commit(node)
        elif message.index == node.next_index[peer] - 1 and node.next_index[peer] > 1:
            node.next_index[peer] -= 1
            self._append_to(node, peer)

    # Level 3
    def propose(self, node: str, command: str) -> int:
        state = self._nodes[node]
        if state.role != LEADER:
            return -1
        state.log.append((state.term, command))
        self._advance_commit(state)
        return state.last_index()

    def log(self, node: str) -> list[str]:
        return [f"{term}:{command}" for term, command in self._nodes[node].log]

    def commit_index(self, node: str) -> int:
        return self._nodes[node].commit

    # Level 4
    def partition(self, groups: list[list[str]]) -> None:
        for number, group in enumerate(groups):
            for name in group:
                self._group[name] = number
        for key, message in list(self._flight.items()):
            if self._group[message.sender] != self._group[message.receiver]:
                del self._flight[key]

    def heal(self) -> None:
        self._group = dict.fromkeys(self._order, 0)

    def applied(self, node: str) -> list[str]:
        return list(self._nodes[node].applied)
