# Raft Simulation

## Statement

Build `RaftCluster`, a step-by-step simulation of Raft, an algorithm that lets a group of servers agree on one sequence of commands even when messages are lost, delayed or reordered and when the network splits. You control everything that happens: the test script says which server's timer fires, which message arrives and which one is lost, so every run is the same. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is consensus?** Many systems keep several copies of the same data on different servers, so that the data survives when a server dies. If clients send commands such as "set x to 1" and "set x to 2", every copy must apply them in the same order, or the copies end up different: one says `x = 2`, another `x = 1`. Consensus is getting several servers to agree on a value, here the command at each position of a list, so that once they have agreed, the answer never changes, even if some servers crash and messages go missing.

**The leader.** Raft simplifies the problem by electing one server as the leader. Clients send commands to the leader, the leader decides their order and copies them to the other servers, the followers. When the leader stops being heard from, the others elect a new one. Worked example: in a cluster of `s1`, `s2` and `s3` led by `s1`, a client sends `x`. `s1` puts `x` at position 1 of its list and sends it to `s2` and `s3`. As soon as `s2` confirms that it stored `x`, two of the three servers hold it, so `s1` can treat position 1 as settled, even if `s3` is down. Nobody else ever proposes a different command for position 1 while `s1` leads, so there is nothing to argue about.

**Terms.** Time is divided into terms, numbered 1, 2, 3 and so on. Each term starts with an election and has at most one leader. Every message carries the sender's term, and a server that sees a greater term than its own adopts it at once and becomes a follower: a greater term means newer news. Worked example: `s1` is the leader of term 1 when the network cuts it off. `s2` hears nothing from it, starts term 2 and wins. When `s1` is reachable again, the first message it gets from term 2 tells it that it is out of date, and it steps down. Terms work like edition numbers on a document: whoever holds an older edition knows to discard it.

**The log.** Each server keeps a log: a list of entries, numbered from 1, where each entry holds a command and the term in which the leader received it. This problem writes an entry as `"<term>:<command>"`, so the log `["1:x", "1:y", "2:z"]` holds `x` and `y`, received in term 1, and `z`, received in term 2. Once an entry is safely stored on enough servers it is **committed**: it will never change or disappear, and each server **applies** it, carrying out the command, in log order.

**Majorities.** A majority is more than half of all the servers of the cluster: 2 of 3, 3 of 4, 3 of 5. A leader needs the votes of a majority, and an entry needs copies on a majority to be committed. Any two majorities of the same cluster share at least one server, and that shared server is what stops two leaders in one term, or a new leader that has forgotten a committed entry.

**The simulation.** There are no clocks and no threads. Each method call is one event of the script: a node's election timer fires (`timeout`), a leader's heartbeat timer fires (`heartbeat`), the network delivers or loses a message (`deliver`, `lose`), a client sends a command (`propose`). Every message a node sends waits in flight until the script delivers or loses it, in any order the script chooses; that is how delays and reordering happen. Messages are numbered 1, 2, 3 and so on across the whole cluster, in the order they are sent, and the methods that make nodes send return the ids of what they sent.

The rules follow the summary of Raft in Ongaro and Ousterhout's paper, and the levels say exactly what a node does where the paper leaves a choice open.

Aim to finish in 150 minutes. A good split: read the statement in the first 15 minutes, then finish level 1 by about minute 35, level 2 by 70, level 3 by 115 and level 4 by 140, keeping the last minutes for a final run.

## Input

- `RaftCluster(nodes)`: creates one node per id. Ids are distinct, and their order in `nodes` is the **cluster order**. Every node starts as a follower in term 0, with no vote, an empty log and a commit index of 0.
- Every `node` and `candidate` argument is an id of the cluster.
- Log entries are written `"<term>:<command>"`.
- Each level's section describes the methods it adds and their parameters.

## Output

- `status()` returns one line per node, in cluster order: `"<node> <role> <term>"`, where the role is `follower`, `candidate` or `leader`.
- Methods that make nodes send messages return the ids of the messages sent, in the order they were sent, `[]` when none.
- Absence is `""` for a vote and `-1` for a log index. `load`, `lose`, `partition` and `heal` return nothing.

## Level 1: The voting rules

A node's state is its current term, its vote (the candidate it voted for in its current term, or none) and its log. A candidate asks for a vote with a RequestVote, which carries four values: the candidate's term, its id, and the index and the term of the last entry of its log (`0` and `0` for an empty log).

- `load(node, term, vote, entries)`: sets the node's state as given, with `vote` as `""` for none. The node becomes a follower with a commit index of 0 and nothing applied.
- `requestVote(node, candidate, term, lastLogIndex, lastLogTerm)`: `node` handles a RequestVote from `candidate` and returns its answer, one of `"granted"`, `"stale-term"`, `"already-voted"` and `"stale-log"`.
- `votedFor(node)`: the node's vote in its current term, `""` when it has none.
- `status()`: every node's role and term.

**Deciding a vote.** The node applies these steps in order and stops at the first answer:

1. If `term` is greater than its own, the node adopts it: its term becomes `term`, it forgets its vote and it becomes a follower. This happens even when the vote is refused below.
2. If `term` is smaller than its own term: `"stale-term"`.
3. If it has already voted in this term for a different candidate: `"already-voted"`. A node asked again by the candidate it voted for answers as if asked for the first time.
4. If the candidate's log is not at least as up-to-date as its own: `"stale-log"`.
5. Otherwise it records the vote for `candidate`: `"granted"`.

**Up-to-date.** Compare the last entries of the two logs. If their terms differ, the log whose last entry has the greater term is more up-to-date, whatever the lengths. If the terms are equal, the longer log is more up-to-date. So `["1:a", "3:b"]` is more up-to-date than `["1:a", "1:b", "1:c"]`, and two logs that end with the same term and have the same length are equally up-to-date, which is enough for a vote. This rule is what keeps a node that missed committed entries from becoming leader.

### Example 1

<!-- case: ex1 -->

`s2` votes for `s1` in term 1. In the same term it refuses `s3`, and grants `s1` again when `s1` asks again. In term 2 the vote of term 1 no longer counts, so `s2` votes for `s3`. A request changes only the node that handles it: `s1` and `s3` stay in term 0.

### Example 2

<!-- case: ex2 -->

`s2`'s log ends with an entry of term 3. `s1`'s log is longer but ends with term 2, so it is less up-to-date and `s2` refuses, after adopting term 4 and forgetting any vote. `s3`'s log ends with term 3 and has the same length, so `s2` votes for it. A request from term 3 is now too old.

## Level 2: Leader election

Nodes now talk through messages. There are four kinds, and every message carries its sender's term:

| Message | Sent by | Fields beside the term |
|---------|---------|------------------------|
| RequestVote | a candidate | candidate id, last log index, last log term |
| RequestVote reply | the node asked | whether the vote was granted |
| AppendEntries | the leader | leader id, prevLogIndex, prevLogTerm, entries, leaderCommit (level 3) |
| AppendEntries reply | the node that got it | success, index (level 3) |

- `timeout(node)`: the node's election timer fires. A leader ignores it. Any other node starts an election: it adds 1 to its term, becomes a candidate, votes for itself, and sends a RequestVote to every other node, in cluster order. In a cluster of one node, its own vote is a majority and it becomes leader at once. Returns the ids of the messages sent.
- `heartbeat(node)`: the node's heartbeat timer fires. A leader sends an AppendEntries to every other node, in cluster order; any other node does nothing. Returns the ids sent.
- `deliver(message)`: the network hands the message with that id to its receiver, which handles it as below. Returns the ids of the messages the receiver sent while handling it. A message that is not in flight (never sent, or already delivered or lost) changes nothing, and the result is `[]`.
- `lose(message)`: the network loses the message with that id; it will never arrive. A message that is not in flight changes nothing.

**Every message.** A node that receives a message whose term is greater than its own first adopts that term, forgets its vote and becomes a follower (step 1 of level 1), whatever the kind of the message.

**RequestVote.** The receiver decides as in level 1 and sends a RequestVote reply to the candidate with its term after the decision and whether it granted the vote.

**RequestVote reply.** If the receiver is still a candidate, the reply's term equals its own term and the vote was granted, the receiver counts the sender's vote. A reply from an earlier term, or one that reaches a node that is no longer a candidate, is ignored. A candidate whose votes, its own included, form a majority becomes leader.

**Becoming leader.** The new leader sets, for every other node, `nextIndex` to its own last log index plus 1 and `matchIndex` to 0 (level 3 uses both), and sends an AppendEntries to every other node, in cluster order, so they learn who leads.

**AppendEntries.** If the request's term is smaller than the receiver's term, the receiver replies with a failure. Otherwise the sender is the leader of the receiver's term: a candidate becomes a follower, and the receiver handles the log fields as level 3 describes and replies. In this level's cases every log is still empty when such a request arrives, so it always succeeds.

**AppendEntries reply.** A leader handles a reply of its own term as level 3 describes; every other reply is ignored once its term has been adopted.

**Ids and order.** Every message that is sent gets the next id. When one event makes a node send to several nodes, it sends in cluster order and skips itself.

### Example 1

<!-- case: ex3 -->

`s1` times out and asks `s2` (message 1) and `s3` (message 2) for votes. `s2`'s yes (3) gives `s1` two votes of three, so `s1` becomes leader and sends AppendEntries 4 and 5. Message 5 moves `s3` into term 1. The old RequestVote 2 then reaches `s3`, which has no vote yet in term 1 and grants it; the reply changes nothing, because `s1` is already leader.

### Example 2

<!-- case: ex4 -->

Four nodes need three votes. `s1` and `s2` both start term 1; `s3` votes for `s1` and `s4` for `s2`, and `s2` refuses `s1` because it voted for itself, so both candidates stop at two votes: a split vote. `s1` times out again, starts term 2, and wins with the votes of `s2` and `s3`. `s4` has not heard of term 2 yet.

## Level 3: Log replication

The leader now accepts commands, copies them to the followers and commits them.

- `propose(node, command)`: if the node is a leader, it appends the entry `(its term, command)` to its log and returns the entry's index; otherwise it returns `-1` and nothing changes. Proposing sends no message: the entry travels with the leader's next AppendEntries.
- `log(node)`: the node's log, each entry written `"<term>:<command>"`.
- `commitIndex(node)`: the index of the node's highest committed entry, 0 when none.

**What an AppendEntries carries.** When the leader sends to node `f`, it uses `nextIndex[f]`, the index of the next entry it believes `f` needs: `prevLogIndex = nextIndex[f] - 1`, `prevLogTerm` the term of the leader's entry at `prevLogIndex` (0 when it is 0), `entries` every entry of the leader's log from `nextIndex[f]` to the end (possibly none), and `leaderCommit` the leader's commit index.

**The follower's side.** After the term checks of level 2, the receiver:

1. Checks that its log has an entry at `prevLogIndex` whose term is `prevLogTerm` (index 0 always matches). If not, it replies with a failure and `index = prevLogIndex`, and changes nothing else.
2. Takes the entries in order, the `k`-th one going to index `prevLogIndex + k`. Where it holds an entry with a different term at that index, it deletes that entry and every entry after it. Where it holds no entry, it appends. Where it holds an entry with the same term, it keeps it, so a late or repeated request never cuts a log short.
3. If `leaderCommit` is greater than its commit index, it raises its commit index to `min(leaderCommit, prevLogIndex + number of entries)`: it only knows that its log matches the leader's up to the last entry of this request.
4. Replies with a success and `index = prevLogIndex + number of entries`.

**The leader's side.** A leader that receives a reply of its own term from `f`:

- On a success, sets `matchIndex[f]` to the larger of its value and the reply's index, and `nextIndex[f]` to the larger of its value and the reply's index plus 1. Then it checks its commit index.
- On a failure, if the reply's index is `nextIndex[f] - 1`, the reply answers the latest probe: the leader lowers `nextIndex[f]` by 1 and sends `f` a new AppendEntries at once. Any other failure is an answer to an older request and is ignored.

**Committing.** The leader looks for the greatest index `N` above its commit index such that the entry at `N` has the leader's current term and is stored on a majority, counting the leader itself and every follower `f` with `matchIndex[f] >= N`. If there is one, the commit index becomes `N`, which commits every entry before it too. The leader checks after every successful reply and after every `propose`, so a cluster of one node commits a proposal at once. A leader never commits an entry of an earlier term by counting its copies: such an entry can be stored on a majority and still be replaced by a later leader. It is committed only when an entry of the current term after it is. A commit index never goes down.

### Example 1

<!-- case: ex5 -->

`s1` leads term 1 and accepts `x` at index 1; `s2` is not a leader and answers `-1`. The heartbeat carries `x` to `s2` (message 7) and `s3` (8). Once `s2`'s success arrives, `x` is on two of three nodes, so `s1` commits it. `s2` learns about the commit from the next heartbeat. Message 8 is still in flight, so `s3` has nothing yet.

### Example 2

<!-- case: ex6 -->

`s1` wins term 3: its last entry has term 2, newer than the last entry of `s2`. The first AppendEntries to `s2` fails, because `s2` has a term 1 entry at index 2. `s1` retries with `nextIndex` one lower, and `s2` replaces `1:c` and `1:d` with `2:b`. Now `2:b` is on two of three nodes, but it comes from term 2, so `s1` does not commit it. Once `3:e` from term 3 is on two nodes, `s1` commits index 3, and `2:b` with it.

## Level 4: Partitions and recovery

The network can now split into groups that cannot reach each other. Every node also has a state machine that carries out the commands of its committed entries.

- `partition(groups)`: from now on, only nodes of the same group can reach each other; every node is in exactly one group. Messages in flight between nodes of different groups are lost at once, and messages sent between them later are lost as they are sent: they get no id and are not in the returned lists. A new `partition` replaces the previous one.
- `heal()`: every node can reach every other node again. Messages that were lost stay lost.
- `applied(node)`: the commands the node has applied, in order. A node applies the entries up to its commit index, in index order, each once, as soon as its commit index rises.

Nothing else changes: a leader cut off from the majority still believes it leads and accepts proposals, but it can no longer commit them. The majority side elects a new leader of a higher term and goes on committing. When the groups meet again, the higher term makes the old leader step down, and the new leader's AppendEntries replace the entries it never managed to commit. Raft guarantees that this never touches a committed entry. The paper states the guarantees as five properties, and a correct implementation keeps all of them on every schedule of this problem:

- **Election safety**: at most one leader is elected in a term.
- **Leader append-only**: a leader never overwrites or deletes entries in its own log.
- **Log matching**: if two logs hold an entry with the same index and term, they are identical up to that index.
- **Leader completeness**: an entry committed in a term is in the log of every leader of every later term.
- **State machine safety**: no two nodes ever apply different commands at the same index.

### Example 1

<!-- case: ex7 -->

Every node has committed and applied `a` when the partition cuts `s1` off. `s1` still leads term 1 and accepts `lost`, but its heartbeat reaches no one. On the other side, `s2` wins term 2 and commits `b` with `s3`. After the heal, `s2`'s heartbeat makes `s1` a follower of term 2, replaces `1:lost` with `2:b`, and tells it that index 2 is committed, so `s1` applies `b`. The committed `a` was never at risk.

### Example 2

<!-- case: ex8 -->

`s3` is cut off while `s1` and `s2` commit `b`. Alone, `s3` times out three times and reaches term 4. After the heal, its failure reply carries term 4, so the leader `s1` steps down. `s3` then starts term 5, but its log lacks `b`, so both others refuse it. `s1` wins term 6 and brings `s3` up to date, and `s3` applies `b`. A node that rejoins with a high term can force an election, but it cannot win it with a stale log.

## Constraints

- `1 <= nodes.length <= 7`.
- Ids and commands are 1 to 10 characters, each a lowercase letter or a digit.
- In `load`: `0 <= term <= 1000`; `vote` is `""` or an id of the cluster; entry terms are between 1 and `term` and never decrease along the log; at most 50 entries.
- In `requestVote`: `candidate` differs from `node`; `1 <= term <= 1000`; `0 <= lastLogIndex <= 50`; `0 <= lastLogTerm <= term`; `lastLogTerm` is 0 exactly when `lastLogIndex` is 0.
- In `partition`, every node of the cluster appears in exactly one group.
- At most 200 method calls per case.

## Follow-ups

- In level 4's second example, a node that was cut off forces a healthy leader to step down. Ongaro's thesis describes a Pre-Vote phase in which a candidate first asks whether it could win before raising its term. How would that change the schedule of that example?
- In level 3's second example, the leader cannot commit `2:b` until a client sends a new command. The paper has every new leader commit a blank entry at the start of its term. What does that buy, and what would it change in the cases here?
- A follower that refuses an AppendEntries could also return the term of its conflicting entry and the first index it holds for that term, so that the leader skips a whole term per round trip. How many messages would that save in level 3's second example?
- Here the leader sends every missing entry at once. Real leaders cap the entries per message. With a cap, why must a follower commit only up to the last entry of the request and not up to the end of its log?
- A crashed node restarts. Which parts of its state must it have kept on disk, and which can it rebuild?
- The script decides when timers fire. Why do real clusters pick election timeouts at random, and what happens when every node times out at the same moment?

## Hints

### Hint 1

Begin with level 1 alone: a node is a term, a vote and a log, and a vote is five checks in a fixed order. Write the "greater term" step as a small function of its own: from level 2 on, every message of every kind goes through it first, and most bugs in elections come from a path that forgets it.

### Hint 2

Keep the network in one place: a map from id to message for what is in flight, a counter for the next id, and a list that collects the ids sent during the current call. Sending a message is then one function, and the public methods only reset the list, do their work and return it.

### Hint 3

Write one handler per kind of message. Track how a node changes role: a follower or candidate becomes a candidate on a timeout, a candidate becomes leader on a majority, and any node becomes a follower when it sees a greater term, as does a candidate that hears from the leader of its own term. A reply is only worth counting if it answers the current term.

### Hint 4

For replication, think of `nextIndex[f]` as the leader's guess of where `f`'s log stops matching and `matchIndex[f]` as what `f` has confirmed. A failure moves the guess down by one; a success moves both up. On the follower, cut the log only at the first entry whose term differs from the leader's, never just because a request ends earlier.

### Hint 5

To commit, walk down from the leader's last index and stop at the first entry of an earlier term: no entry below it can be committed by counting. For each entry of the current term, count the leader plus the followers whose `matchIndex` reaches it, and stop at the first one a majority stores.

### Hint 6

One structure that carries all four levels: a node record with `term`, `votedFor`, `log`, `commit`, `applied`, `role`, `votes`, `nextIndex` and `matchIndex`; a message record with the fields of all four kinds and a `kind`; a table of messages in flight by id; and a group number per node for the partition, where sending to a node of another group does nothing. `deliver` removes the message from the table and calls the handler of its kind on the receiver; every handler starts by adopting a greater term, and `commitTo(i)` raises the commit index and appends the newly committed commands to `applied`.
