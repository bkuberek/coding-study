# Review: the facts of the distributed systems guides

The eight guides of the path "Distributed systems: from partial failure to consensus" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts taken from papers, an RFC and a standard library module. This page lists each one with where it was checked, and the changes of the independent accuracy review.

"Quote" means the exact text was read at that source, in the text extracted from the PDF with `pdftotext`, or in the RFC's text edition. "Run" means an example of the guide printed it, on CPython 3.13.12. "Arithmetic" means the number was computed from the stated inputs. "Reasoning" marks an explanation in the guide's own words that rests on no source and is shown by an example or by the arithmetic. A fact that could not be checked was left out of the guides; the last sections list those, the citation choices, and where a guide comes close to a linked problem.

| Guide | Slug |
|-------|------|
| Why distributed systems are hard | `why-distribution-is-hard` |
| Time and order: happened-before, Lamport clocks and vector clocks | `time-and-order` |
| Partitioning and consistent hashing | `partitioning-and-consistent-hashing` |
| Replication: leaders, logs and quorums | `replication-and-quorums` |
| Idempotency and exactly-once effects | `idempotency-and-exactly-once` |
| Consistency models: from linearizable to eventual, and CAP | `consistency-models` |
| CRDTs: replicated data that merges without conflicts | `crdts` |
| Consensus with Raft | `consensus-with-raft` |

## Time, clocks and partial failure

Lamport, *Time, Clocks, and the Ordering of Events in a Distributed System*, Communications of the ACM 21(7), July 1978, pages 558 to 565, read from [the author's PDF](https://lamport.azurewebsites.net/pubs/time-clocks.pdf). Mattern, *Virtual Time and Global States of Distributed Systems*, Proceedings of the International Workshop on Parallel and Distributed Algorithms (Chateau de Bonas, October 1988), Elsevier (North-Holland), 1989, read from [the ETH Zurich PDF](https://www.vs.inf.ethz.ch/publ/papers/VirtTimeGlobStates.pdf). Waldo, Wyant, Wollrath and Kendall, *A Note on Distributed Computing*, technical report TR-94-29, November 1994, read from [an archived copy](https://web.archive.org/web/2010/http://www.cc.gatech.edu/classes/AY2010/cs4210_fall/papers/smli_tr-94-29.pdf). Fischer, Lynch and Paterson, *Impossibility of Distributed Consensus with One Faulty Process*, Journal of the ACM 32(2), April 1985, pages 374 to 382, read from [the MIT PDF](https://groups.csail.mit.edu/tds/papers/Lynch/jacm85.pdf). Used in `why-distribution-is-hard`, `time-and-order` and `consensus-with-raft`.

| # | Claim | Source |
|---|-------|--------|
| L1 | A distributed system consists of a collection of distinct processes that are spatially separated and communicate by exchanging messages | Quote: Lamport, first paragraph |
| L2 | Physical clocks are not perfectly accurate and do not keep precise physical time; the paper derives a bound on how far out of synchrony they can drift | Quote: Lamport, *The Partial Ordering*, *Introduction* |
| L3 | In a distributed system it is sometimes impossible to say which of two events occurred first; happened-before is only a partial ordering | Quote: Lamport, *Introduction* |
| L4 | Happened-before is the smallest relation with the three conditions (same process, send before receipt, transitivity); two distinct events are concurrent when neither happened before the other; the relation is an irreflexive partial ordering | Quote: Lamport, *The Partial Ordering*, Definition |
| L5 | `a → b` means it is possible for `a` to causally affect `b`; concurrent events cannot causally affect each other | Quote: Lamport, *The Partial Ordering* |
| L6 | Clock Condition: if `a → b` then `C(a) < C(b)`; the converse cannot be expected, since it would make concurrent events occur at the same time | Quote: Lamport, *Logical Clocks* |
| L7 | IR1: a process increments its clock between any two successive events; IR2: a message carries the sender's timestamp, and the receiver sets its clock greater than or equal to its present value and greater than the timestamp | Quote: Lamport, *Logical Clocks* |
| L8 | Ties are broken by an arbitrary total ordering of the processes; the result completes happened-before to a total ordering; it is not unique; any total ordering that extends happened-before is yielded by some system of clocks; only the partial ordering is determined by the events | Quote: Lamport, *Ordering the Events Totally* |
| L9 | The total order is used to grant a shared resource in the order requests are made; a central scheduler granting requests in the order received fails when `P1` sends a request and then a message to `P2`, whose later request can arrive first | Quote: Lamport, *Ordering the Events Totally* |
| L10 | Anomalous behavior: a request on computer A, then a phone call, then a request on computer B that can be ordered first; remedies are to put the ordering information into the system explicitly, or physical clocks satisfying the Strong Clock Condition | Quote: Lamport, *Anomalous Behavior* |
| M1 | No process has a consistent view of the global state, and a common time base does not exist; this is the cause of most typical problems of distributed systems | Quote: Mattern, abstract |
| M2 | A process ticks by incrementing its own component, `Ci[i] := Ci[i] + 1`; each message carries the sender's vector; the receiver sets `Ci := sup(Ci, t)`, the componentwise maximum | Quote: Mattern, §7 |
| M3 | Ticking is considered to occur before any other action of an event; at any instant `Ci[i] ≥ Cj[i]`, since only `Pi` advances the `i`-th component (Theorem 5) | Quote: Mattern, §7 |
| M4 | `u ≤ v`, `u < v` and `u ‖ v` defined entry by entry (Definition 4, §7); `e < e′` exactly when `C(e) < C(e′)`, and `e ‖ e′` exactly when `C(e) ‖ C(e′)` (Theorem 10, §8) | Quote: Mattern, §7 and §8 |
| M5 | With Lamport's clocks, `C(e) < C(e′)` does not decide whether `e < e′` or `e ‖ e′` | Quote: Mattern, §6 |
| M6 | `(N^n, ≤)` is a lattice whose least upper bound is the componentwise maximum (Theorem 7) | Quote: Mattern, §8 |
| M7 | A consistent cut is a set of events closed under causal predecessors (Definition 3); its cut events can occur simultaneously in an equivalent diagram (Theorem 4) | Quote: Mattern, §3 and §4 |
| M8 | Independently of Mattern, the use of vectors of logical clocks for distributed debugging was suggested and discussed by Fidge, in references [5] and [4]: *Timestamps in Message-Passing Systems that Preserve Partial Ordering*, Proceedings of the 11th Australian Computer Science Conference, pages 56 to 66, February 1988; and *Partial orders for parallel debugging*, Proceedings of the ACM SIGPLAN and SIGOPS Workshop on Parallel and Distributed Debugging, pages 183 to 194, May 1988 | Quote: Mattern, §10 and references |
| W1 | Local failures are either total or detectable by a central resource allocator such as the operating system; in a distributed system one component can fail while the others continue, no common agent can determine what failed and tell the others, and the failure of a network link is indistinguishable from the failure of the processor on the other side | Quote: Waldo et al., *Partial failure and concurrency* |
| W2 | Hiding the difference between local and remote objects is a mistake; distributed programming must deal with latency, memory access, concurrency and partial failure | Quote: Waldo et al., abstract |
| W3 | An application that retried every queue operation after time-outs until it succeeded found requests processed two, three, four or more times; the culprit was the way the queue was used | Quote: Waldo et al., the queue example |
| F1 | No completely asynchronous consensus protocol can tolerate even a single unannounced process death; the message system is assumed reliable, delivering every message correctly and exactly once; "the stopping of a single process at an inopportune time can cause any distributed commit protocol to fail to reach agreement. Thus, this important problem has no robust solution without further assumptions about the computing environment or still greater restrictions on the kind of failures to be tolerated!" | Quote: FLP, §1 |
| F2 | Asynchronous: no assumptions about the relative speeds of processes or message delays, no synchronized clocks, so time-outs cannot be used; it is impossible to tell whether a process has died or is running very slowly | Quote: FLP, §1 |
| F3 | Byzantine failures are those in which faulty processes may go completely haywire, even sending messages according to some malevolent plan (the guide's gloss of "non-Byzantine") | Quote: FLP, §1 |
| F4 | Each process acts deterministically according to a transition function; the conclusion calls for more refined models of timing and less stringent requirements, for example termination required only with probability 1 | Quote: FLP, §2 and §5 |

## Partitioning

Karger, Lehman, Leighton, Panigrahy, Levine and Lewin, *Consistent Hashing and Random Trees: Distributed Caching Protocols for Relieving Hot Spots on the World Wide Web*, STOC 1997, pages 654 to 663, read from [the Brown University copy](https://cs.brown.edu/courses/csci2950-u/f09/papers/chash97stoc.pdf). Used in `partitioning-and-consistent-hashing`.

| # | Claim | Source |
|---|-------|--------|
| K1 | With a classical hash function such as `ax + b mod p`, a change of the range sends almost every item to a new location, and all cached data becomes useless | Quote: §4 |
| K2 | A consistent hash function changes minimally as its range changes; the protocols do not require users to have a current or even consistent view of the network; consistent hashing may be useful for distributed name servers and quorum systems | Quote: abstract |
| K3 | Views; smoothness (the expected fraction of objects moved is the minimum needed for a balanced load), spread and load; balance; monotonicity, defined for buckets being added: items move from old buckets only to new ones; the paper does not commit to a precise definition of consistency, and states these properties instead | Quote: §4, §4.1 |
| K4 | Buckets and items are mapped to the unit interval and an item goes to the closest bucket; each bucket gets about `κ log C` points | Quote: §4.2 |
| K5 | A balanced search tree gives O(log C) per lookup and O(log² C) per bucket added or removed; dividing the interval into about `C log C` equal segments, each with its own tree, gives O(1) expected per lookup | Quote: §4.3 |
| K6 | Hot spots occur when a large number of clients want data from one server at once; random cache trees use a different tree for each page, assigned to caches by a hash function, so that no server is swamped | Quote: §1, §1.2 |
| K7 | The leaving half, a key moving only away from a leaving node, follows from the same clockwise rule | Run: `moves.py` shows the joining half, every moved key going to `E`; reasoning for the leaving half |

## Replication

Gifford, *Weighted Voting for Replicated Data*, Proceedings of the 7th ACM Symposium on Operating Systems Principles, December 1979, pages 150 to 162, read from [the UMass copy](https://none.cs.umass.edu/~shenoy/courses/fall04/readings/gifford.pdf). Abadi, *Consistency Tradeoffs in Modern Distributed Database System Design*, IEEE Computer 45(2), February 2012, pages 37 to 42, read from [the author's PDF](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf). Used in `replication-and-quorums` and `consistency-models`.

| # | Claim | Source |
|---|-------|--------|
| V1 | Replication puts information close to its point of use, lets many nodes serve requests in parallel, and increases availability by masking partial failures | Quote: Gifford, §1 |
| V2 | Every copy gets votes; reads collect `r` votes and writes `w` votes, with `r + w` greater than the total, so every read quorum and write quorum intersect; version numbers determine which copies are current | Quote: Gifford, abstract and §1 |
| V3 | The first write of a transaction increments the version numbers of its write quorum | Quote: Gifford, §3.3 |
| V4 | Example 2: the local server has two votes and two remote servers one each, so writes need the local server and one remote one; Example 3, on three servers: users read from any server and updates go to all copies | Quote: Gifford, §3 |
| V5 | Weak representatives have no votes and serve as local copies; the paper notes that a write quorum of other representatives is always current, so one found in error can be invalidated | Quote: Gifford, §3 and §4.1 |
| V6 | The algorithm runs in a transactional file system with locking and two-phase commit, and the appendix shows that it maintains serial consistency; the guide glosses serially consistent as the outcome of the transactions run one at a time, Herlihy and Wing's serializability (H4) | Quote: Gifford, §1 and §3.1 |
| A1 | There are only three ways to send updates to replicas: to all at the same time, to an agreed-upon master node first, or to an arbitrary node first; each has a consistency/latency tradeoff; sending to all at once diverges unless a preprocessing layer or agreement protocol orders updates; the second routes every update to that node; with the third, two updates of the same item can start at different locations at once | Quote: Abadi, *Data replication* |
| A2 | Synchronous replication waits for the replicas and is limited by the slowest; asynchronous replication treats an update as complete before it is replicated; reads from any node can be inconsistent; update sequence numbers can bound this, for example to read-your-writes | Quote: Abadi, *Data replication* |
| A3 | Reads that reach a synchronously updated node, as when `R + W > N`, preserve consistency; simply using a quorum protocol is not sufficient to guarantee consistency as Gilbert and Lynch define it | Quote: Abadi, *Data replication* |
| A4 | CAP's tradeoff comes from a partition actually happening, not from partition tolerance alone; CAP imposes no restriction when there is no partition, allowing the complete set of ACID guarantees (atomicity, consistency, isolation and durability) with high availability; the consistency/latency tradeoff is present at all times | Quote: Abadi, *CAP is for failures*, conclusion |
| A5 | PACELC: if there is a partition (P), how does the system trade off availability and consistency (A and C); else (E), how does it trade off latency (L) and consistency (C) | Quote: Abadi, *PACELC* |

## Consensus

Ongaro and Ousterhout, *In Search of an Understandable Consensus Algorithm (Extended Version)*, May 2014, read from [the Raft site's PDF](https://raft.github.io/raft.pdf); the conference version appeared at USENIX ATC 2014. Used in `consensus-with-raft`, and in `why-distribution-is-hard`, `time-and-order`, `replication-and-quorums`, `idempotency-and-exactly-once` and `consistency-models` where noted.

| # | Claim | Source |
|---|-------|--------|
| R1 | Practical consensus algorithms ensure safety under all non-Byzantine conditions, including network delays, partitions, and packet loss, duplication and reordering; are available as long as a majority of servers is up and communicating, so five servers tolerate any two failures; do not depend on timing for the consistency of the logs, so faulty clocks and extreme delays can at worst cause availability problems | Quote: §2 |
| R2 | Replicated state machines: each log holds the same commands in the same order and the state machines are deterministic, so each computes the same state; large systems with a single cluster leader typically keep leader election and configuration in a separate replicated state machine | Quote: §2 (in `replication-and-quorums` too) |
| R3 | Raft produces a result equivalent to (multi-)Paxos and is as efficient; it separates leader election, log replication and safety; Paxos has dominated the discussion of consensus | Quote: abstract, §1 |
| R4 | Each server is a leader, follower or candidate; in normal operation exactly one leader handles all client requests, and followers only respond to leaders and candidates | Quote: §5.1, Figure 4 |
| R5 | Terms are consecutive integers, each beginning with an election, with at most one leader; terms act as a logical clock; a server that sees a larger term adopts it; a candidate or leader with an out-of-date term reverts to follower; a request with a stale term is rejected | Quote: §5.1 (in `time-and-order` too) |
| R6 | Heartbeats are AppendEntries without entries; a follower that hears nothing for the election timeout increments its term, becomes a candidate, votes for itself and requests votes; a majority of the full cluster wins; each server votes for at most one candidate per term, first come first served; the majority rule allows at most one winner per term; a candidate that receives AppendEntries with a term at least its own returns to follower; split votes end in timeouts and new terms | Quote: §5.2, Figure 4 |
| R7 | Election timeouts are chosen randomly from a fixed interval, such as 150 to 300 ms, so that usually one server times out first | Quote: §5.2 |
| R8 | An entry holds a command and the leader's term; it is committed once the leader that created it has replicated it on a majority, which also commits the entries before it; committed entries are durable and eventually executed by all available state machines; the leader sends its commit index in later AppendEntries | Quote: §5.3 |
| R9 | Log Matching: equal index and term mean equal command and identical preceding entries; the consistency check on the preceding entry's index and term is the induction step; after a rejection the leader decrements `nextIndex` and retries; conflicting follower entries are overwritten | Quote: §5.3 |
| R10 | A leader never overwrites or deletes entries in its own log | Quote: §5.3, Figure 3 |
| R11 | A voter denies its vote to a candidate whose log is less up-to-date: a later last term is more up-to-date, and with equal last terms the longer log is; every committed entry is on at least one server of any majority | Quote: §5.4.1 |
| R12 | A leader cannot conclude that an entry from a previous term is committed once it is on a majority; in Figure 8 the term-2 entry is on S1, S2 and S3, and with S1 down, S5, whose last entry has term 3, is elected with the votes of S2, S3 and S4 and overwrites it; only entries of the current term are committed by counting replicas, which commits the entries before them | Quote: §5.4.2, Figure 8 |
| R13 | The leader completeness argument goes through a voter that stored the committed entry and voted for the later leader | Quote: §5.4.3, Figure 9 |
| R14 | Safety must not depend on timing; availability inevitably depends on timing; the timing requirement is broadcastTime ≪ electionTimeout ≪ MTBF | Quote: §5.6 (in `why-distribution-is-hard` too) |
| R15 | Without randomness, elections consistently took longer than 10 seconds because of split votes; 5 ms of randomness gave a median downtime of 287 ms; timeouts below 12 to 24 ms break the timing requirement and cause unnecessary leader changes | Quote: §9.3 |
| R16 | Switching configurations directly is unsafe, since the cluster can split into two independent majorities; joint consensus needs separate majorities of the old and new configurations | Quote: §6 |
| R17 | Snapshotting writes the whole current state to stable storage and discards the log up to that point; the leader sends snapshots to followers that lag behind | Quote: §7 |
| R18 | The goal is linearizable semantics, each operation taking effect instantaneously, exactly once, between invocation and response; a leader crash after committing and before responding makes the client retry and the command execute twice; clients assign unique serial numbers, and the state machine keeps the latest serial number per client with its response | Quote: §8 (in `idempotency-and-exactly-once` too) |
| R19 | A leader must commit an entry from its term to know which entries are committed, and exchanges heartbeats with a majority to check that it has not been deposed before answering a read-only request without the log; the guide states both steps and leaves out the paper's reason for the first, which `raft-sim`'s follow-up 2 asks | Quote: §8 (in `consistency-models` too) |
| R20 | Raft is similar to Viewstamped Replication; its novel features are a strong leader, randomized timers and joint consensus; in Viewstamped Replication a leader can be elected without all committed entries, with extra mechanisms to transfer them | Quote: §1, §5.4.1 |
| R21 | A user study with 43 students at two universities: 33 answered questions about Raft better than about Paxos | Quote: §1 |

## Consistency models

Herlihy and Wing, *Linearizability: A Correctness Condition for Concurrent Objects*, ACM TOPLAS 12(3), July 1990, pages 463 to 492, read from [the Brown University PDF](https://cs.brown.edu/~mph/HerlihyW90/p463-herlihy.pdf). Lamport, *How to Make a Multiprocessor Computer That Correctly Executes Multiprocess Programs*, IEEE Transactions on Computers C-28(9), September 1979, pages 690 to 691, read from [the author's PDF](https://lamport.azurewebsites.net/pubs/multi.pdf). Lloyd, Freedman, Kaminsky and Andersen, *Don't Settle for Eventual: Scalable Causal Consistency for Wide-Area Storage with COPS*, SOSP 2011, pages 401 to 416, read from [the CMU PDF](https://www.cs.cmu.edu/~dga/papers/cops-sosp2011.pdf). Gilbert and Lynch, *Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services*, ACM SIGACT News 33(2), June 2002, pages 51 to 59, read from [the author's PDF](https://www.comp.nus.edu.sg/~gilbert/pubs/BrewersConjecture-SigAct.pdf). Berenson, Bernstein, Gray, Melton, O'Neil and O'Neil, *A Critique of ANSI SQL Isolation Levels*, SIGMOD 1995, pages 1 to 10, read from [arXiv cs/0701157](https://arxiv.org/abs/cs/0701157). Used in `consistency-models`, and in `why-distribution-is-hard` where noted.

| # | Claim | Source |
|---|-------|--------|
| H1 | Linearizability: each operation appears to take effect instantaneously at some point between its invocation and its response; the order respects real-time precedence; operations unrelated by it are concurrent | Quote: Herlihy and Wing, abstract and §2 |
| H2 | Linearizability is local: a system is linearizable if each object is; sequential consistency and serializability are not, with history H8 over two queues; linearizability is nonblocking for totally defined operations | Quote: Herlihy and Wing, §1, §3 |
| H3 | Sequential consistency is weaker than linearizability, since it does not preserve the real-time precedence order | Quote: Herlihy and Wing, §3.3 |
| H4 | Serializability and strict serializability defined; strict serializability is ensured by two-phase locking but not by multiversion timestamp schemes; linearizability is a special case of strict serializability with transactions of one operation on one object | Quote: Herlihy and Wing, §3.3 |
| S1 | Sequential consistency: the result of any execution is the same as if the operations of all processors ran in some sequential order, each processor's operations in program order | Quote: Lamport 1979 |
| C1 | Potential causality: execution thread, gets from, transitivity | Quote: Lloyd et al., §3 |
| C2 | Causal consistency: it must appear that a write occurs after all operations that causally precede it; concurrent operations are not ordered; two concurrent puts to one key let one replica return one value forever and another the other; causal+ consistency is causal consistency with convergent conflict handling, in which all replicas handle conflicting puts the same way, with an associative and commutative handler, so that the results converge | Quote: Lloyd et al., §2, §3 and §3.1 |
| C3 | In decreasing strength: linearizability, sequential, causal, FIFO, per-key sequential, eventual | Quote: Lloyd et al., §3.2 |
| C4 | Dependencies are kept in each version's metadata; a datacenter receiving a replicated write checks its dependencies before committing it | Quote: Lloyd et al., §3 |
| G1 | Brewer made the conjecture at PODC 2000 | Quote: Gilbert and Lynch, §1 |
| G2 | Atomic or linearizable consistency: a total order of operations in which each looks as if completed at a single instant, as if on a single node; a read that begins after a write completes returns that value or a later one | Quote: Gilbert and Lynch, §2.1 |
| G3 | Atomic consistency differs from the database notion; it subsumes the Atomic and Consistent of ACID | Quote: Gilbert and Lynch, footnote 3 |
| G4 | Availability: every request received by a non-failing node must result in a response, with no bound on time | Quote: Gilbert and Lynch, §2.2 |
| G5 | Partition tolerance: the network may lose arbitrarily many messages; in a partition all messages between the components are lost | Quote: Gilbert and Lynch, §2.3 |
| G6 | Theorem 1 and its proof: two groups, all messages between them lost, a write completes in one, a later read in the other returns the initial value | Quote: Gilbert and Lynch, §3.1 |
| G7 | In the asynchronous model there is no clock and an algorithm cannot tell a lost message from one arbitrarily delayed; Corollary 1.1: no read/write object is available in all fair executions and atomic in the fair executions in which no messages are lost | Quote: Gilbert and Lynch, §3.1 (in `why-distribution-is-hard` too) |
| G8 | Partially synchronous model: every node has a timer, and a message is delivered within a known time or lost; Theorem 2, the impossibility when messages are lost, still holds; the analogue of Corollary 1.1 does not: atomic data can be returned whenever all messages are delivered, using time-outs | Quote: Gilbert and Lynch, §4 |
| B1 | Snapshot isolation: a transaction reads from a snapshot of committed data as of its start timestamp; it commits only if no transaction that committed in its interval wrote data it also wrote, first-committer-wins, which prevents lost updates | Quote: Berenson et al., §4.2 |
| B2 | Snapshot isolation is not serializable because reads come at one instant and writes at another; write skew (A5B), with the constraint that `x + y` stays positive in history H5 | Quote: Berenson et al., §4.2 |

## CRDTs

Shapiro, Preguiça, Baquero and Zawirski, *Conflict-free Replicated Data Types*, 13th International Symposium on Stabilization, Safety, and Security of Distributed Systems (SSS 2011), Lecture Notes in Computer Science, pages 386 to 400, read from [the Tufts copy](https://www.cs.tufts.edu/~nr/cs257/archive/marc-shapiro/CRDTs_SSS-2011.pdf). Used in `crdts`, and in `consistency-models` where noted.

| # | Claim | Source |
|---|-------|--------|
| D1 | Published eventual consistency approaches are ad hoc and error-prone; updates take effect at all replicas asynchronously and possibly in different orders; concurrent updates may conflict, and arbitration may require consensus and rollback | Quote: abstract, §1 |
| D2 | Eventual consistency: eventual delivery, convergence, termination; strong eventual consistency adds strong convergence; informally, replicas eventually reach the same value if clients stop submitting updates | Quote: §2.2 (in `consistency-models` too) |
| D3 | State-based: replicas occasionally send their state to another replica, which merges it; links are fair-lossy; a join semilattice with a least upper bound, which is commutative, idempotent and associative; the monotonic semilattice condition (Definition 4) and Theorem 1 | Quote: §2.1, §2.3 |
| D4 | Operation-based: reliable causally ordered broadcast delivering every message exactly once; concurrent updates commute (Definition 6); Theorem 2 | Quote: §2.4 |
| D5 | Each style can emulate the other (Theorems 3 and 4) | Quote: §3.2 |
| D6 | A strongly eventually consistent replica is always available for reads and writes; any communicating subset converges; up to `n − 1` crashes are tolerated; consensus is not needed | Quote: §3.1 |
| D7 | Concurrent add and remove: add wins, remove wins, the replica with the highest IP address wins, or a reset; the add-wins scenario reaches a state no sequential execution reaches; strong eventual and sequential consistency are incomparable | Quote: §3.3 (in `consistency-models` too) |
| D8 | The add-only set, ordered by inclusion with union as least upper bound | Quote: §4.2 |
| D9 | The last-writer-wins register is credited to Johnson et al. and ensures a total order at the cost of losing concurrent updates; operational transformation, and Oster et al.'s finding that most decentralized transformation algorithms are incorrect; designing for commutativity is cleaner and simpler | Quote: §6 |
| D10 | Keeping the write with the largest timestamp, ties broken by replica id, is a merge that obeys the three laws: it takes the maximum in a total order | Reasoning |

## Idempotency

RFC 9110, *HTTP Semantics*, June 2022, read from [the text edition](https://www.rfc-editor.org/rfc/rfc9110.txt). Akidau and others, *MillWheel: Fault-Tolerant Stream Processing at Internet Scale*, Proceedings of the VLDB Endowment 6(11), August 2013, pages 1033 to 1044, read from [the VLDB PDF](https://www.vldb.org/pvldb/vol6/p1033-akidau.pdf). Used in `idempotency-and-exactly-once`.

| # | Claim | Source |
|---|-------|--------|
| I1 | A method is idempotent if the intended effect of several identical requests is the same as of one; such requests can be repeated automatically after a communication failure | Quote: RFC 9110, §9.2.2 |
| I2 | A client should not automatically retry a non-idempotent request unless it knows the request is idempotent anyway or that the original was never applied | Quote: RFC 9110, §9.2.2 |
| I3 | Idempotency applies only to what was requested; a server may log each request separately or keep a revision history | Quote: RFC 9110, §9.2.2 |
| I4 | Every record is guaranteed to be delivered, and processing is idempotent, making delivery exactly once from the user's perspective | Quote: Akidau et al., §1 |
| I5 | Deliveries are retried until acknowledged, an at-least-once requirement that is a prerequisite for exactly-once; a receiver may crash after persisting its state and before acknowledging | Quote: Akidau et al., §6.1.1 |
| I6 | Records get unique ids when produced; the id is stored in the same atomic write as the state change; a retried duplicate is discarded and acknowledged | Quote: Akidau et al., §6.1.1 |
| I7 | A Bloom filter gives a fast path for records provably never seen; ids are garbage collected once all senders have finished retrying, later by a slack of a few hours for sources that often deliver late | Quote: Akidau et al., §6.1.1 |
| I8 | Strong productions: produced records are checkpointed before delivery, in the same atomic write as the state change | Quote: Akidau et al., §6.1.2 |
| I9 | Exactly-once and strong productions can be disabled for computations that are idempotent anyway, as they cost resources and latency; weak productions send before persisting state | Quote: Akidau et al., §6.1.3 |
| I10 | When code contacts external systems, making those effects idempotent is up to the user | Quote: Akidau et al., §4.1 |
| I11 | A sender that must not lose a message resends and may cause duplicates, one that never resends may lose it, and to the sender a lost acknowledgement looks exactly like a lost message | Reasoning; run: `crash_points.py` |

## Python

| # | Claim | Source |
|---|-------|--------|
| Y1 | `hashlib.sha256` gives the digest whose first four bytes are the positions of `moves.py` | Run: `moves.py`; [`hashlib`](https://docs.python.org/3/library/hashlib.html) |

## The examples and the arithmetic

| # | Claim | Source |
|---|-------|--------|
| E1 | Four of five fates show the client `timeout`; without a retry the balance stays 100 in two of them, with one retry it reaches 120 in two | Run: `silent_failures.py` |
| E2 | With B's clock 250 ms slow, the merged log puts B's receipt (790) and reply (795) before A's send (1000) | Run: `two_clocks.py` |
| E3 | The stamps of the ten events; `p1` before `r2` and `r1` before `p4`; `p3` concurrent with `q3` (Lamport 3 and 4) and with `r3` (3 and 6) | Run: `stamps.py` |
| E4 | From 4 to 5 nodes a key stays under modulo placement only when its hash mod 20 is 0 to 3, 4 values in 20; generally `N/(N + 1)` of the keys move | Arithmetic |
| E5 | 812 keys move under modulo placement, to all five nodes; 103 with one point per node, all to `E`, with loads from 15 to 391; 207 with 64 points, all to `E`, with loads from 161 to 216 | Run: `moves.py` |
| E6 | The log gives 17 on both replicas, 8 for the first two commands, 14 in the other order; adding 3 then doubling 5 gives 16, doubling then adding 3 gives 13 | Run: `replicated_log.py`; arithmetic |
| E7 | With `w = r = 3` no read set misses a write set out of 100 pairs; with `w = 5, r = 1` none of 5; with `w = r = 2`, 30 of 100; the read finds `(2, 'green')`; two concurrent writes leave `(3, 'red')` and `(3, 'white')` | Run: `quorums.py` |
| E8 | Ack first gives 0 points after a crash after the ack; credit first gives 100 after a crash after the commit; dedupe gives 50 in all three cases | Run: `crash_points.py` |
| E9 | The four histories: yes/yes, yes/no, yes/yes, no/no for sequential and linearizable | Run: `histories.py` |
| E10 | With the link up, the consistent read takes 81 ms and returns `v2`, the available one 1 ms and `v1`; with the link cut, no answer or `v1` | Run: `partition_choice.py`; the 1 ms and 80 ms are the model's inputs |
| E11 | 720 orders of 6 messages; union and maximum agree in every order; take theirs agrees on 3, 4 or 9 or disagrees; concatenation always disagrees; the removed `milk` comes back | Run: `merge_laws.py`; 720 = 6! |
| E12 | Majorities and tolerated failures for 1 to 7 servers; 0 of 45 pairs of groups of three out of five are disjoint, 15 of 45 of groups of two | Run: `majorities.py` |
| E13 | In the model, equal 150 ms timeouts never elect a leader in 1,000 trials; 150 to 175 ms elects in the first round 395 times, 2.55 rounds on average; 150 to 300 ms 845 times, 1.17 rounds | Run: `split_votes.py` |

## Citations and names

The guides endorse no product and name no company. They name algorithms (Raft, Paxos, Viewstamped Replication), papers, one RFC, and Python's `hashlib`, the language of the examples.

| Name | Why it is named |
|------|-----------------|
| Raft, Paxos, Viewstamped Replication | Algorithms, the subject of the Raft guide and of its paper's comparisons |
| *MillWheel* | Part of a paper's title, cited by title in Further reading; the prose says "a paper by Akidau and others on a fault-tolerant stream processor" |
| *COPS* | Part of a paper's title, cited by title in Further reading; the prose says "Lloyd and others, in a 2011 paper on causal consistency" |
| PODC, SOSP, SSS, STOC, SIGMOD | Conferences, in citations |

Papers are cited by their authors. The affiliations printed in the papers are not repeated, and neither are the systems the Raft, CRDT, Abadi and COPS papers name as examples. The Waldo et al. note is a company technical report, cited by its authors, title and number; the company is not named. Brewer is named as the author of the conjecture, as Gilbert and Lynch name him.

## Not verified, so left out or reworded

- **Fidge, 1988.** Not read; credited only through Mattern (M8).
- **Ahamad, Neiger, Burns, Kohli and Hutto, *Causal memory*, 1995.** Not read; causal consistency is defined from Lloyd et al. (C1 to C3), who cite it.
- **INRIA research report RR-7506**, the longer CRDT report. Not read; the guides cite only the SSS paper.
- **Hybrid logical clocks, bounded loads, delta-state CRDTs.** Not read and not stated; each is a later level of a linked problem, whose statement teaches it.
- **Raft's reason for a new leader's first entry, Pre-Vote, the conflict-term optimization, which state must be persistent, batching of entries.** Left out as answers to `raft-sim`'s follow-ups; Pre-Vote is in Ongaro's thesis, not the paper.
- **The SSS paper's counter construction (§4.1), its U-Set with unique elements (§4.2) and its graph with unique vertex identifiers (§5).** Left out as answers to `crdt-replicas`.
- **When removal information can be forgotten.** Left out as the answer to `crdt-replicas`'s follow-up 1.
- **Gifford and `w > n/2`.** The paper does not state it, and the guide does not claim it.
- **"Exactly once is impossible".** No source for the two-party argument; the guide gives it as reasoning (I11), shown by `crash_points.py`.
- **The name "outbox".** No primary source for the term; the guide attributes it to the practice problem and grounds the technique in strong productions (I8).
- **The complexity of checking linearizability** in general is not stated; the guide says only that its brute-force checker tries `n!` orders.
- **The strength order** follows Lloyd et al.'s list in decreasing strength (C3); their figure also places per-key sequential consistency on a separate branch, which the guide does not draw.

## Practice links

Every problem is on the main branch. Each guide's `problems:` names it in `## Practice`, and each problem's `meta.yaml` names its guides in `guides:`, after `related:`:

| Problem | `guides:` | Path step |
|---------|-----------|-----------|
| 0369 `logical-clocks` | `[time-and-order, why-distribution-is-hard, crdts]` | Level 2 after `time-and-order`; all levels after `crdts` |
| 0370 `consistent-hash-ring` | `[hash-functions, partitioning-and-consistent-hashing]` | After `partitioning-and-consistent-hashing` |
| 0333 `cdc-apply` | `[change-data-capture, replication-and-quorums]` | After `replication-and-quorums` |
| 0272 `idempotent-document-consumer-typescript` | `[idempotency-and-exactly-once, why-distribution-is-hard]` | After `idempotency-and-exactly-once` |
| 0273 `transactional-outbox-typescript` | `[idempotency-and-exactly-once]` | After `idempotency-and-exactly-once` |
| 0368 `mvcc-snapshot-isolation` | `[consistency-models]` | After `consistency-models` |
| 0371 `crdt-replicas` | `[crdts]` | After `crdts` |
| 0372 `raft-sim` | `[consensus-with-raft]` | After `consensus-with-raft` |

`hash-functions` keeps its link to `consistent-hash-ring`.

## Where a guide comes close to a linked problem

Each guide teaches its idea with examples of its own. These are the places where a guide comes close to a linked problem, and what it keeps back so as not to give away the solution:

| Problem | Guide | What the guide states | Kept back |
|---------|-------|-----------------------|-----------|
| `logical-clocks` | `time-and-order` | The Lamport and vector rules and comparison, which the statement gives, in a replay of a fixed history (`stamps.py`); the total order by stamp and process in prose; that vectors tell concurrent versions apart, in one sentence; the trap of sharing a vector (hint 4) | Refusals, the API, `totalOrder` code, siblings and the dominance filter (hint 5), hybrid clocks (level 4) |
| `logical-clocks` | `why-distribution-is-hard`, `crdts` | Why clocks disagree; the practice line names the later levels | Everything above |
| `consistent-hash-ring` | `partitioning-and-consistent-hashing` | The ring, arcs, monotonicity and virtual nodes, which the statement explains; owners found by a scan for the smallest clockwise distance over SHA-256 positions; Karger's balanced search tree in the complexity table, near hint 2's idea | FNV-1a, the point labels and their reason, `arcShare` (hint 4), the move report (hint 5), replica walks and bounded loads (level 4, hint 6) |
| `cdc-apply` | `replication-and-quorums` | A follower applies a leader's log in order and is behind, not different; the trap of applying entries twice | Positions, snapshots, transactions and schema changes; the change data capture guide covers positions |
| `idempotent-document-consumer-typescript` | `idempotency-and-exactly-once` | An id named by whoever decides the change, not the delivery, with no example of a delivery id that changes (near hint 1); id and effect in one commit, then the ack, which level 5's statement requires; ids kept as long as duplicates can arrive, from the stream processing paper (near follow-up 2); effects outside the commit repeat (near follow-up 3) | The content-plus-version key (level 2, hint 3), "done" against "shown" (hint 2), late deliveries (level 3), poison messages and the delivery count (level 4, hint 4) |
| `transactional-outbox-typescript` | `idempotency-and-exactly-once` | Commit the message with the change, send afterwards until acknowledged (strong productions), consumers deduplicate, which the statement's levels 2, 3 and 5 say; the at-least-once rule of the consumer example is the reasoning hint 4 asks for | The relay, reading only the outbox row (hint 3), order per rental and skipping (level 4, hint 5), id numbering and pruning (hint 2) |
| `mvcc-snapshot-isolation` | `consistency-models` | Snapshot isolation, first-committer-wins and write skew, from Berenson et al., which the statement also explains | Version lists, the read rule, antidependencies, dangerous structures and their detection (level 3), the horizon and vacuum (level 4) |
| `crdt-replicas` | `crdts` | The three laws, which the statement states; union and maximum as semilattices; that a removal must leave information behind; last-writer-wins with ties broken by replica id, which level 2's statement specifies | The per-replica counter design (hints 2 and 5), tags for adds (hint 3), the last-writer-wins code, delta sync and acknowledgements (level 4, hint 4); when removal information can be forgotten (follow-up 1); the paper's counter, U-Set and graph sections; that a vector clock is a CRDT |
| `raft-sim` | `consensus-with-raft` | Roles, terms, elections, randomized timeouts (near follow-up 6), commit by majority, the consistency check and retry, the up-to-date rule and the Figure 8 rule, all in the statement; that a new leader first commits an entry of its own term before answering reads without the log, without the reason; a model of split votes that has no logs or messages | Handlers, the message table, the order of the vote checks, `nextIndex` and `matchIndex` bookkeeping (hint 4), the commit walk (hint 5), the blank entry, Pre-Vote, the conflict-term optimization, persistence and batching (follow-ups 1 to 5) |

## Independent accuracy review

The review checks every claim against the source this page gives for it, runs every example and compares what it prints with the guide, and reads the guides against the linked problems' statements and solutions. Every example matches its guide, no guide names a company or product, and the guides on Raft and CRDTs keep their problems' solutions back. These are its findings and the changes they make.

| Finding | Change |
|---------|--------|
| `consistency-models` drew causal consistency as implying eventual consistency, which it does not alone: concurrent writes to one key may diverge forever | The text and the drawing's last arrow say that causal consistency implies eventual consistency only with convergent conflict handling, the paper's causal+ (C2) |
| `consensus-with-raft` said that a voter holding a committed entry refuses any candidate without it, which holds only for entries committed by counting in their own leader's term | The voter refuses such a candidate provided the entry was committed by counting in its own leader's term, which is the second rule; Figure 8 shows the holders that are still up voting for a candidate with a later last term (R12, R13) |
| `replication-and-quorums` said that quorums make the first way of sending updates safe, which no source says | The guide starts with a leader; quorums decide how many replicas a write and a read reach, and do not order concurrent writes on their own (A3, E7) |
| The FLP notes in `why-distribution-is-hard` and `consensus-with-raft` said that consensus needs a timing assumption, leaving out the paper's other ways out | Titled "No deterministic consensus in a fully asynchronous system", with the paper's whole sentence, and the ways out: timing assumptions, which Raft uses for progress only, restricting the failures, or termination with probability 1 (F1, F4) |
| `consensus-with-raft` and `consistency-models` described reads at a leader with one step of two | A new leader first commits an entry of its own term, and exchanges heartbeats with a majority before answering a read-only request without the log; the reason for the first step is not given, so that `raft-sim`'s follow-up 2 stays open (R19) |
| `consistency-models` said that outside partitions there is no choice to make, without the condition | Outside partitions, once replicas can time out on lost messages, there is no choice; the expert notes set the asynchronous model, with Corollary 1.1, against the partially synchronous one (G7, G8) |
| `partitioning-and-consistent-hashing` called both halves of the property monotonicity | The paper's monotonicity is the joining half; the leaving half follows from the same rule (K3, K7) |
| The same guide said that the paper defines consistency through four properties | The paper states four properties as notions of consistency, without a precise definition (K3) |
| `time-and-order` credited Fidge with vector clocks in general | Fidge independently suggested vectors of logical clocks for distributed debugging, in two papers of 1988, references [4] and [5] of Mattern's paper (M8) |
| `idempotency-and-exactly-once` said the last acknowledgement can always be the lost one | To the sender, a lost acknowledgement looks exactly like a lost message (I11) |
| `crdts` limited fast clocks to ties, and gave last-writer-wins without its tie-break | A fast clock wins every conflict; last-writer-wins breaks ties by replica id, a maximum in a total order (D10) |
| Spoilers: `crdts` said when removal information can be forgotten, and `idempotency-and-exactly-once` described a delivery id that changes on a producer's retry | Both are cut; the table above keeps `crdt-replicas`'s follow-up 1 back, and `split_votes.py` and `stamps.py` stay with their rows |
| This page carried discussion wording, put Definition 4 in Mattern's §8, and its count of claim rows was wrong | Outcomes only; Definition 4 is in §7; the claim tables hold 118 rows, with F4 and D10 |
| Wording: "processes" in Lamport's definition, Gifford "requires" a current write quorum, Gifford's third example given five replicas | "Processors"; Gifford notes it; the third example uses the rule on three servers (S1, V4, V5) |
| Jargon before its definition | Glosses for consensus algorithm, deterministic, transaction, serially consistent and ACID where each first appears (A4, V6) |
