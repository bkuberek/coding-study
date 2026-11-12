# Raft Simulation: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| message-handlers | optimal | O(n L) per call | O(n L + M) | default answer; it survives all four levels without a rewrite |

Here `n` is the number of nodes, `L` the length of the longest log and `M` the number of messages in flight. The work of a call is bounded by copying a log suffix into each of `n - 1` messages or by the leader's commit check, which compares up to `L` entries with `n - 1` match indexes.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | The vote decision | each node keeps its term, vote and log; one method adopts greater terms and decides a vote |
| 2 | Messages and roles | a table of messages in flight by id; candidates count votes; leaders send AppendEntries; one handler per kind of message |
| 3 | The log | AppendEntries carry a log suffix and the leader's commit index; leaders keep `nextIndex` and `matchIndex` and commit entries of their own term |
| 4 | Partitions | a group number per node decides whether a message is sent at all; nodes record the commands they apply |

The step that makes the later levels easy is level 1 putting "adopt a greater term" in one method. Level 2 calls it at the top of every handler, level 3 only adds what happens after it, and level 4 needs no change to any handler at all: a partition is just messages that are never delivered.

## Approach: message-handlers (One handler per message kind that applies the rules of the Raft summary)

### Intuition

Raft is a small set of rules, each triggered by one event: a timer, a request or a reply. A simulation that mirrors that structure is easy to get right: every event becomes one method that reads the node's state, changes it, and sends messages. Because the network is a table of messages that only the script empties, delays, losses and reordering need no code of their own: they are just the order in which the script delivers.

The safety of the algorithm rests on two overlaps. Any two majorities share a node, so two candidates cannot both collect a majority in one term, because the shared node votes once per term. And the node that stored a committed entry and also voted for a later leader refused any candidate whose log was less up-to-date than its own, so the later leader holds the entry. The rules about terms make sure that stale information, a vote or a reply from an earlier term, never counts.

### Algorithm

1. A node holds `term`, `votedFor`, `log`, `commit`, `applied`, `role`, its `votes` as a candidate, and `nextIndex` and `matchIndex` as a leader. `observe(t)` adopts a greater term: it sets the term, clears the vote and makes the node a follower.
2. `decideVote` calls `observe`, then answers `stale-term`, `already-voted` or `stale-log` in that order, and otherwise records the vote. The log check compares `(lastLogTerm, lastLogIndex)` with the node's own pair as tuples.
3. `send` drops a message whose sender and receiver are in different groups; otherwise it gives it the next id, stores it in flight and records the id in the list of the current call.
4. `timeout` turns a non-leader into a candidate of the next term with its own vote and sends a RequestVote to every other node in cluster order; a cluster of one wins at once. `heartbeat` makes a leader send an AppendEntries to every other node.
5. `deliver` removes the message from the table and calls the handler of its kind on the receiver. The RequestVote handler decides and replies. The reply handler adopts a greater term and counts a granted vote of the current term while the node is still a candidate; a majority makes it leader, which sets `nextIndex` and `matchIndex` and sends AppendEntries.
6. The AppendEntries handler adopts a greater term, refuses an older one, turns a candidate into a follower, checks the entry at `prevLogIndex`, truncates only at the first conflicting entry, appends what is missing, raises the commit index to `min(leaderCommit, last new index)`, and replies with the last new index.
7. The leader's reply handler ignores replies of other terms. A success raises `matchIndex` and `nextIndex` by taking maxima and checks the commit index; a failure that answers the latest probe lowers `nextIndex` and sends again at once.
8. The commit check walks down from the last index while the entries have the current term and commits the first one stored by a majority. `commitTo` appends the newly committed commands to `applied`.
9. `partition` gives each node a group number and drops the messages in flight between groups; `heal` puts every node back in group 0.

### Correctness

Election safety: a node votes at most once per term, because the vote is cleared only when the term grows, and a candidate counts only replies of its current term. Two candidates of the same term would each need a majority, and two majorities share a node that would have voted twice. Leader append-only holds because no code path of a leader removes entries from its own log: truncation happens only in the AppendEntries handler, which a leader never runs for its own term.

Log matching holds by induction on the AppendEntries that succeed. A leader creates at most one entry per index in its term, and entries never change position, so equal index and term mean equal command. A follower accepts entries only after its entry at `prevLogIndex` matched the leader's in term, so by induction the whole prefix matches, and appending the leader's entries after it keeps the two logs identical up to the last new entry. Truncation removes only entries that conflict with the leader's, never a prefix that matches, so a late or repeated request cannot undo a later one.

Leader completeness follows the argument of the paper. Suppose an entry is committed by the leader of term `T` and a later leader `U` lacks it. Some voter of `U` stored the entry, because the replicas and the voters are both majorities. That voter refused candidates less up-to-date than itself, so `U`'s last term was at least the voter's; if equal, `U`'s log was at least as long and contains the voter's log; if greater, the leader that created `U`'s last entry held the committed entry, and log matching puts it in `U`'s log. Either way `U` has it. This argument needs the entry to be committed by a leader of its own term, which is why the commit check skips entries of earlier terms: the Figure 8 case (`h29`) shows such an entry stored on a majority and later replaced, harmlessly, because no one ever committed it.

State machine safety follows: a node applies an entry only once its commit index reaches it, a follower's commit index never passes the last entry it verified against the leader, and every leader of a later term holds the same committed entries, so no two nodes apply different commands at the same index. The content tests of this problem replay every case on an independent model and check all five properties after every step.

### Complexity

- Time: O(n L) per call — a vote decision and a reply count are O(1); handling an AppendEntries compares and appends at most `L` entries; a heartbeat, a timeout or an election win sends one message to each of the other `n - 1` nodes, each carrying up to `L` entries; the commit check walks at most `L` entries and counts `n - 1` match indexes for each.
- Space: O(n L + M) — every node keeps a log of up to `L` entries and its applied commands, a leader keeps two numbers per node, and each of the `M` messages in flight holds up to `L` entries.

### Trade-offs

- Sending the whole log suffix in every AppendEntries keeps the rules short and makes one round trip enough once `nextIndex` is right. Real implementations cap the number of entries per message and send the next batch on each success, which costs one more rule and makes the `min(leaderCommit, last new entry)` of step 6 essential: with a batch, the follower's log may still hold entries from an old term after the last one it verified.
- Lowering `nextIndex` by one per failure is the paper's basic rule. The paper describes an optimization in which the failure carries the conflicting term and the first index of that term, so the leader skips a whole term at once; it costs two fields and saves round trips only when logs differ a lot.
- Ignoring a failure that does not answer the latest probe is a choice of this problem. Without it, a delayed failure from an older request would lower `nextIndex` once more and resend entries the follower already has: harmless, but it would make the message ids depend on more than the latest exchange.
- Proposals wait for the next heartbeat instead of being sent at once. That keeps the number of messages small and predictable here; a real leader sends new entries right away to cut latency.
- A message table indexed by id gives the script full control. A real network adds timeouts and retries; in the simulation, a retry is the script calling `heartbeat` or `timeout` again.

### Pitfalls and edge cases

- Level 1, the order of the checks. Adopt a greater term first, even when the vote is then refused: a node that refuses for its log still moves to the new term and forgets its old vote (`h3`). A stale term is refused before anything else, and a vote already given is reported before a stale log (`h4`). The candidate the node voted for may ask again and gets the same answer (`h1`).
- Level 1, up-to-date. Compare the last terms first and the lengths only between equal last terms (`h2`), use the candidate's last log term and not its current term (`h5`), and accept a log that is exactly as up-to-date as the voter's (`h2`, `h3`).
- Level 2, majorities. A majority is more than half of the whole cluster, not of the nodes that answered: two votes of four are not enough (`h12`), and five nodes need three (`h11`). A candidate counts its own vote, so a cluster of one wins at once (`h13`).
- Level 2, stale replies. A granted vote from an earlier term must not count (`h10`), and every reply, not only every request, can carry a greater term that makes a leader or candidate step down (`h9`, `h16`).
- Level 2, the leader of your term. A candidate that receives an AppendEntries of its own term becomes a follower (`h8`); a leader ignores its election timer, and only a leader sends heartbeats (`h7`). A lost message never arrives later (`h14`).
- Level 3, committing earlier terms. An entry of an earlier term stored on a majority is not committed by counting (`ex6`, `h17`, `h29`); it is committed when an entry of the current term after it is.
- Level 3, truncation. Cutting the log after `prevLogIndex` on every request lets a late, shorter request delete entries that a newer one added (`h18`). Replacing only the conflicting entry and keeping the ones after it leaves entries of an old term in the log (`h19`). Checking only the length at `prevLogIndex`, and not the term, accepts entries on top of a log that differs from the leader's (`h20`).
- Level 3, counting copies. The leader counts itself (`h21`). A failure answering an older probe must not move `nextIndex` a second time (`h23`), and a failure for the latest probe is answered at once (`h17`, `h20`). Only a leader accepts proposals, and a leader that missed a newer term accepts them but never commits them (`h22`).
- Level 4, the network. A partition loses the messages already in flight across it, and healing does not bring them back (`h24`). A message sent across a partition is lost before it gets an id, so the ids stay consecutive among the messages that can arrive (`h25` to `h29`).
- Level 4, applying. Apply an entry only when it is committed: a leader on the minority side, or a follower that received entries it cannot yet confirm, must not apply them, because they may be replaced after the heal (`h25`, `h27`).
- Level 4, the disruptive node. A node that was cut off returns with a greater term and forces an election it cannot win, because its log is behind (`ex8`); the cluster recovers, and nothing committed is lost.

### Language notes

- Python: dataclasses keep the message record readable; tuples compare element by element, so the up-to-date check is one comparison of `(last_term, last_index)`. `dict.fromkeys` builds the per-node maps of a new leader.
- TypeScript: a `Map` keyed by number holds the messages in flight, and deleting while iterating over a copy (`[...this.flight]`) avoids skipping entries. Setting `log.length` truncates an array in place.
- Java: a `HashMap<Integer, Message>` holds the messages; `values().removeIf` drops the ones a partition cuts. `subList(...).clear()` truncates a log in place, and a `record` holds an entry. Boxed `Integer` values are compared with `equals`, never `==`.
- Kotlin: the same JVM collections with `getValue` for keys that must exist and `subList(...).clear()` for truncation. A helper named like a parameter cannot be called inside that method, so the node lookup is `nodeOf`.
- Go: maps hold the nodes and the messages; deleting from a map while ranging over it is allowed. A log is truncated by reslicing, and the leader copies its suffix into each message so that a follower's later appends never write into the leader's backing array. The built-in `min` and `max` work on integers.
- Rust: a message handler needs a node and the network mutably at the same time; keeping the network in a struct of its own lets a method borrow `self.nodes` and `self.net` separately. Moving fields out of an owned message (`reply.sender`) is fine because the struct has no destructor. `Vec::truncate` and `retain` do the truncation and the partition.

## Further reading

- [Ongaro and Ousterhout, "In Search of an Understandable Consensus Algorithm", USENIX ATC 2014, pages 305 to 319](https://www.usenix.org/conference/atc14/technical-sessions/presentation/ongaro): the conference paper, which received a best paper award there.
- [The extended version of the paper](https://raft.github.io/raft.pdf): Figure 2 summarizes the state, the two RPCs and the rules this problem implements; Figure 3 lists the five safety properties; section 5.2 covers elections, split votes and randomized timeouts (150 to 300 ms in its example); section 5.3 covers replication, the consistency check and the optional conflict-term optimization; section 5.4.1 defines up-to-date; section 5.4.2 and Figure 8 explain why entries of earlier terms are not committed by counting; section 8 describes the blank entry a new leader commits at the start of its term.
- [Ongaro, "Consensus: Bridging Theory and Practice", PhD dissertation, Stanford University, 2014](https://web.stanford.edu/~ouster/cgi-bin/papers/OngaroPhD.pdf): section 9.6 describes how a node that was partitioned disrupts the cluster when it returns with a greater term, and the Pre-Vote phase that prevents it.
