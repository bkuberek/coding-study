type Role = "follower" | "candidate" | "leader";
type Entry = [number, string];

// One RPC request or reply in flight. Only the fields of its kind are used.
interface Message {
  kind: "vote" | "vote-reply" | "append" | "append-reply";
  sender: string;
  receiver: string;
  term: number;
  lastIndex: number;
  lastTerm: number;
  granted: boolean;
  prevIndex: number;
  prevTerm: number;
  entries: Entry[];
  leaderCommit: number;
  success: boolean;
  index: number;
}

function message(kind: Message["kind"], sender: string, receiver: string, term: number): Message {
  return {
    kind, sender, receiver, term,
    lastIndex: 0, lastTerm: 0, granted: false,
    prevIndex: 0, prevTerm: 0, entries: [], leaderCommit: 0,
    success: false, index: 0,
  };
}

// The state of one server: persistent (term, vote, log), volatile (commit index, role) and the
// leader's bookkeeping, plus the commands applied to its state machine.
class RaftNode {
  readonly name: string;
  term = 0;
  votedFor = "";
  log: Entry[] = [];
  commit = 0;
  applied: string[] = [];
  role: Role = "follower";
  votes = new Set<string>();
  nextIndex = new Map<string, number>();
  matchIndex = new Map<string, number>();

  constructor(name: string) {
    this.name = name;
  }

  lastIndex(): number {
    return this.log.length;
  }

  termAt(index: number): number {
    return index > 0 ? this.log[index - 1][0] : 0;
  }

  // A term greater than the node's own makes it a follower of that term with no vote.
  observe(term: number): void {
    if (term > this.term) {
      this.term = term;
      this.votedFor = "";
      this.role = "follower";
      this.votes = new Set();
    }
  }

  decideVote(candidate: string, term: number, lastIndex: number, lastTerm: number): string {
    this.observe(term);
    if (term < this.term) return "stale-term";
    if (this.votedFor !== "" && this.votedFor !== candidate) return "already-voted";
    const myTerm = this.termAt(this.lastIndex());
    if (lastTerm < myTerm || (lastTerm === myTerm && lastIndex < this.lastIndex())) return "stale-log";
    this.votedFor = candidate;
    return "granted";
  }

  // Raises the commit index and applies the newly committed commands in log order.
  commitTo(index: number): void {
    if (index <= this.commit) return;
    for (const [, command] of this.log.slice(this.commit, index)) this.applied.push(command);
    this.commit = index;
  }
}

// A cluster of Raft nodes on a scripted network. Messages wait in flight until the script
// delivers or loses them; every node reacts to one message at a time by the rules of the Raft
// summary, and every message it sends gets the next id.
export class RaftCluster {
  private readonly order: string[];
  private readonly nodes = new Map<string, RaftNode>();
  private readonly flight = new Map<number, Message>();
  private lastId = 0;
  private group = new Map<string, number>();
  private sent: number[] = [];

  constructor(nodes: string[]) {
    this.order = [...nodes];
    for (const name of nodes) {
      this.nodes.set(name, new RaftNode(name));
      this.group.set(name, 0);
    }
  }

  private node(name: string): RaftNode {
    return this.nodes.get(name)!;
  }

  private peers(name: string): string[] {
    return this.order.filter((peer) => peer !== name);
  }

  private majority(count: number): boolean {
    return 2 * count > this.order.length;
  }

  private send(out: Message): void {
    if (this.group.get(out.sender) !== this.group.get(out.receiver)) return;
    this.lastId += 1;
    this.flight.set(this.lastId, out);
    this.sent.push(this.lastId);
  }

  private appendTo(leader: RaftNode, peer: string): void {
    const start = leader.nextIndex.get(peer)!;
    const out = message("append", leader.name, peer, leader.term);
    out.prevIndex = start - 1;
    out.prevTerm = leader.termAt(start - 1);
    out.entries = leader.log.slice(start - 1);
    out.leaderCommit = leader.commit;
    this.send(out);
  }

  private becomeLeader(node: RaftNode): void {
    node.role = "leader";
    node.votes = new Set();
    node.nextIndex = new Map();
    node.matchIndex = new Map();
    for (const peer of this.peers(node.name)) {
      node.nextIndex.set(peer, node.lastIndex() + 1);
      node.matchIndex.set(peer, 0);
    }
    for (const peer of this.peers(node.name)) this.appendTo(node, peer);
  }

  // Commits the highest entry of the leader's own term that a majority stores.
  private advanceCommit(leader: RaftNode): void {
    for (let index = leader.lastIndex(); index > leader.commit; index--) {
      if (leader.termAt(index) !== leader.term) return;
      let stored = 1;
      for (const match of leader.matchIndex.values()) if (match >= index) stored += 1;
      if (this.majority(stored)) {
        leader.commitTo(index);
        return;
      }
    }
  }

  // Level 1
  load(node: string, term: number, vote: string, entries: string[]): void {
    const state = this.node(node);
    state.term = term;
    state.votedFor = vote;
    state.role = "follower";
    state.votes = new Set();
    state.log = entries.map((text): Entry => {
      const colon = text.indexOf(":");
      return [Number(text.slice(0, colon)), text.slice(colon + 1)];
    });
    state.commit = 0;
    state.applied = [];
  }

  requestVote(node: string, candidate: string, term: number, lastLogIndex: number, lastLogTerm: number): string {
    return this.node(node).decideVote(candidate, term, lastLogIndex, lastLogTerm);
  }

  votedFor(node: string): string {
    return this.node(node).votedFor;
  }

  status(): string[] {
    return this.order.map((name) => `${name} ${this.node(name).role} ${this.node(name).term}`);
  }

  // Level 2
  timeout(node: string): number[] {
    this.sent = [];
    const state = this.node(node);
    if (state.role === "leader") return [];
    state.term += 1;
    state.role = "candidate";
    state.votedFor = node;
    state.votes = new Set([node]);
    if (this.majority(state.votes.size)) {
      this.becomeLeader(state);
      return this.sent;
    }
    for (const peer of this.peers(node)) {
      const vote = message("vote", node, peer, state.term);
      vote.lastIndex = state.lastIndex();
      vote.lastTerm = state.termAt(state.lastIndex());
      this.send(vote);
    }
    return this.sent;
  }

  heartbeat(node: string): number[] {
    this.sent = [];
    const state = this.node(node);
    if (state.role === "leader") {
      for (const peer of this.peers(node)) this.appendTo(state, peer);
    }
    return this.sent;
  }

  deliver(id: number): number[] {
    this.sent = [];
    const found = this.flight.get(id);
    if (found === undefined) return this.sent;
    this.flight.delete(id);
    const receiver = this.node(found.receiver);
    if (found.kind === "vote") this.onVote(receiver, found);
    else if (found.kind === "vote-reply") this.onVoteReply(receiver, found);
    else if (found.kind === "append") this.onAppend(receiver, found);
    else this.onAppendReply(receiver, found);
    return this.sent;
  }

  lose(id: number): void {
    this.flight.delete(id);
  }

  private onVote(node: RaftNode, request: Message): void {
    const result = node.decideVote(request.sender, request.term, request.lastIndex, request.lastTerm);
    const reply = message("vote-reply", node.name, request.sender, node.term);
    reply.granted = result === "granted";
    this.send(reply);
  }

  private onVoteReply(node: RaftNode, reply: Message): void {
    node.observe(reply.term);
    if (node.role !== "candidate" || reply.term !== node.term || !reply.granted) return;
    node.votes.add(reply.sender);
    if (this.majority(node.votes.size)) this.becomeLeader(node);
  }

  private onAppend(node: RaftNode, request: Message): void {
    node.observe(request.term);
    const reply = message("append-reply", node.name, request.sender, node.term);
    reply.index = request.prevIndex;
    if (request.term < node.term) {
      this.send(reply);
      return;
    }
    if (node.role === "candidate") {
      node.role = "follower";
      node.votes = new Set();
    }
    const prev = request.prevIndex;
    if (prev > node.lastIndex() || node.termAt(prev) !== request.prevTerm) {
      this.send(reply);
      return;
    }
    request.entries.forEach((entry, offset) => {
      const index = prev + 1 + offset;
      if (index <= node.lastIndex() && node.termAt(index) !== entry[0]) node.log.length = index - 1;
      if (index > node.lastIndex()) node.log.push(entry);
    });
    const lastNew = prev + request.entries.length;
    if (request.leaderCommit > node.commit) node.commitTo(Math.min(request.leaderCommit, lastNew));
    reply.success = true;
    reply.index = lastNew;
    this.send(reply);
  }

  private onAppendReply(node: RaftNode, reply: Message): void {
    node.observe(reply.term);
    if (node.role !== "leader" || reply.term !== node.term) return;
    const peer = reply.sender;
    const next = node.nextIndex.get(peer)!;
    if (reply.success) {
      node.matchIndex.set(peer, Math.max(node.matchIndex.get(peer)!, reply.index));
      node.nextIndex.set(peer, Math.max(next, reply.index + 1));
      this.advanceCommit(node);
    } else if (reply.index === next - 1 && next > 1) {
      node.nextIndex.set(peer, next - 1);
      this.appendTo(node, peer);
    }
  }

  // Level 3
  propose(node: string, command: string): number {
    const state = this.node(node);
    if (state.role !== "leader") return -1;
    state.log.push([state.term, command]);
    this.advanceCommit(state);
    return state.lastIndex();
  }

  log(node: string): string[] {
    return this.node(node).log.map(([term, command]) => `${term}:${command}`);
  }

  commitIndex(node: string): number {
    return this.node(node).commit;
  }

  // Level 4
  partition(groups: string[][]): void {
    groups.forEach((group, number) => {
      for (const name of group) this.group.set(name, number);
    });
    for (const [id, waiting] of [...this.flight]) {
      if (this.group.get(waiting.sender) !== this.group.get(waiting.receiver)) this.flight.delete(id);
    }
  }

  heal(): void {
    for (const name of this.order) this.group.set(name, 0);
  }

  applied(node: string): string[] {
    return [...this.node(node).applied];
  }
}
