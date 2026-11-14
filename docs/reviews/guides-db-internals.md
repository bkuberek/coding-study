# Review: the facts of the database internals guides

The seven guides of the path "Database internals: from pages and B-trees to transactions and query plans" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about research papers, the PostgreSQL and SQLite documentation, and Python's standard library. This page lists each one with where it was checked, so that the independent review starts from the sources.

"Quote" means the exact text was read at that source: in the text extracted from the PDF with `pdftotext`, or on the documentation page. "Run" means an example of the guide printed it, on CPython 3.13.12. "Arithmetic" means the number was computed from the stated inputs. The bibliographic data (authors, venue, volume, pages, year) of every paper comes from its Crossref record. The PostgreSQL documentation is the one served at `postgresql.org/docs/current`, the documentation of PostgreSQL 18 (release 18.7 was current); the SQLite documentation is the one served at `sqlite.org`. A conclusion a guide draws itself from the facts cited next to it is not attributed to a source; the main ones have a section of their own. A fact that could not be checked is not in the guides; the last sections list those, the citation choices, and where a guide comes close to a linked problem.

| Guide | Slug |
|-------|------|
| Pages and records: how a table sits on disk | `pages-and-records` |
| B-tree indexes: balanced trees of pages | `b-tree-indexes` |
| Log-structured storage: LSM trees and compaction | `lsm-trees-and-compaction` |
| Write-ahead logging and crash recovery | `write-ahead-logging` |
| Transactions: ACID, isolation levels and locking | `transactions-and-isolation` |
| MVCC and snapshot isolation: versions, snapshots and write skew | `mvcc-and-snapshot-isolation` |
| Query planning: estimates, join algorithms and join order | `query-planning-and-joins` |

## B-trees

R. Bayer and E. McCreight, *Organization and Maintenance of Large Ordered Indexes*, Acta Informatica 1(3), 1972, pages 173 to 189, [doi:10.1007/BF00288683](https://doi.org/10.1007/BF00288683). The journal text was not available; the claims were read in its 1970 version, *Organization and Maintenance of Large Ordered Indices*, Mathematical and Information Sciences Report No. 20, Boeing Scientific Research Laboratories, July 1970, from [a copy in a course archive](https://infolab.usc.edu/csci585/Spring2010/den_ar/indexing.pdf) whose title page is the report's. D. Comer, *The Ubiquitous B-Tree*, ACM Computing Surveys 11(2), 1979, pages 121 to 137, [doi:10.1145/356770.356776](https://doi.org/10.1145/356770.356776), read from [a scanned copy](http://carlosproal.com/ir/papers/p121-comer.pdf) with the journal's page headers. Used in `b-tree-indexes`.

| # | Claim | Source |
|---|-------|--------|
| B1 | The index is kept on a pseudo random access backup store such as a disc or a drum; retrieval, insertion and deletion take time proportional to log_k I, where I is the size of the index and k a device-dependent natural number describing the page size; storage utilization is at least 50% | Quote: Bayer and McCreight 1970, abstract and §1 |
| B2 | A tree in the class τ(k, h): every path from the root to a leaf has length h; every node except the root and the leaves has at least k + 1 sons; the root is a leaf or has at least two sons; every node has at most 2k + 1 sons | Quote: Bayer and McCreight 1970, §2, Definition 2.1 |
| B3 | A page that is not a leaf and holds ℓ keys has ℓ + 1 sons | Quote: Bayer and McCreight 1970, §3 |
| B4 | The trees grow and contract only by splitting and catenation, initiated at the leaves and propagating toward the root; a root split introduces a new root, the only way the height increases; the opposite happens when the tree contracts | Quote: Bayer and McCreight 1970, §1 |
| B5 | Splitting: the entry is first inserted into the full page; the first k entries stay, entry k + 1 is inserted into the father, the rest go to a new page; this may repeat up to the root, where a new root page is introduced | Quote: Bayer and McCreight 1970, §4, "Splitting a Page" |
| B6 | Deletion: a key not on a leaf is replaced by the smallest key of the subtree its right pointer leads to, taken from a leaf; adjacent brothers (same father, adjacent pointers) are catenated when together they hold at most 2k keys, with the key that separated them in the father; this may propagate to the root; otherwise the keys of the two are equally distributed ("underflow"), which does not propagate | Quote: Bayer and McCreight 1970, §6 |
| B7 | Overflow: a key inserted into a full page whose adjacent brother is not full is distributed between the two; a page splits only when both adjacent brothers are full; without deletions this raises the worst-case storage utilization to about 66% | Quote: Bayer and McCreight 1970, §8 |
| C1 | A node of a B-tree of order d holds at most 2d keys and 2d + 1 pointers, and at least d keys, the root excepted | Quote: Comer, page 124 and Figure 7 |
| C2 | A find never visits more than 1 + log_d n nodes in a B-tree of order d indexing n records; the balancing restricts changes to a single path from a leaf to the root | Quote: Comer, page 125 |
| C3 | A binary search might be useful within a large node (attributed to Knuth) | Quote: Comer, page 129 |
| C4 | In a B+-tree all keys reside in the leaves; the upper levels form only an index, "a roadmap"; the leaves are linked left to right, a list called the sequence set; Comer uses the name B+-tree for an unnamed variant of Knuth's | Quote: Comer, page 129 |
| C5 | A leaf split promotes a copy of the middle key and keeps the key in the right leaf; a find does not stop at a key in the index equal to the query, it follows the nearest right pointer down to a leaf; a deleted key may remain in the index as a separator | Quote: Comer, page 130 and Figure 14 |
| C6 | A B-tree may need log_d n accesses for a "next" operation, a B+-tree at most one; sequential processing accesses no node more than once | Quote: Comer, page 130 |
| C7 | The origin of the name was never explained by its authors; "balanced", "broad" or "bushy" might apply; others suggest Boeing; Comer suggests "Bayer"-trees; Bayer and McCreight were then at Boeing Scientific Research Labs | Quote: Comer, page 123 |

## Log-structured merge trees

P. O'Neil, E. Cheng, D. Gawlick and E. O'Neil, *The Log-Structured Merge-Tree (LSM-Tree)*, Acta Informatica 33(4), 1996, pages 351 to 385, [doi:10.1007/s002360050048](https://doi.org/10.1007/s002360050048), read from [the authors' copy](https://www.cs.umb.edu/~poneil/lsmtree.pdf) marked "To be published: Acta Informatica". C. Luo and M. J. Carey, *LSM-based Storage Techniques: A Survey*, The VLDB Journal 29(1), pages 393 to 418, [doi:10.1007/s00778-019-00555-y](https://doi.org/10.1007/s00778-019-00555-y), whose Crossref record dates it 2019, read from [arXiv:1812.07527](https://arxiv.org/abs/1812.07527). Used in `lsm-trees-and-compaction`.

| # | Claim | Source |
|---|-------|--------|
| O1 | A B-tree index on a fast-growing history table would effectively double the I/O cost of the transaction, increasing the total system cost up to fifty percent | Quote: O'Neil and others, abstract |
| O2 | An LSM tree has components C0, ..., CK of increasing size; C0 is in memory and the others on disk; asynchronous rolling merges between neighbouring components move entries out when the smaller exceeds its threshold, so a long-lived entry migrates from C0 to CK | Quote: O'Neil and others, §2.2 and §3.3 |
| O3 | A log record of each insert is written first, then the entry goes into C0; inserting into C0 has no I/O cost | Quote: O'Neil and others, §2 |
| O4 | "defers and batches index changes, cascading the changes from a memory-based component through one or more disk components in an efficient manner reminiscent of merge sort" | Quote: O'Neil and others, abstract |
| O5 | The rolling merge removes a contiguous segment of entries from C0 and merges it into C1, which is optimized for sequential access in multi-page blocks | Quote: O'Neil and others, §2 |
| O6 | A delete places a delete node entry that migrates outward and annihilates the entry it deletes when it is encountered in a merge; finds filter through delete node entries | Quote: O'Neil and others, §2.3 |
| O7 | The LSM tree is most useful where index inserts are more common than finds that retrieve the entries, as for history tables and log files | Quote: O'Neil and others, abstract |
| O8 | Where most finds concern recently inserted values, many are completed in C0 | Quote: O'Neil and others, §2.2 |
| O9 | Theorem 3.1: with a fixed largest component, insert rate and memory component, the total page I/O rate of the merges is minimized when the ratios between neighbouring component sizes are all equal | Quote: O'Neil and others, §3.3 |
| O10 | With the insert rate and the largest component fixed, the I/O rate grows as the memory component shrinks | Quote: O'Neil and others, §3.3 |
| O11 | The log records of inserts can be treated as logical logs; replaying them recreates the lost content of C0 | Quote: O'Neil and others, §2 |
| S1 | An in-place structure overwrites old records; an out-of-place structure always stores updates in new locations, which exploits sequential I/O and simplifies recovery, at the cost of reads (a record may be in any of several places) and a separate reorganization process | Quote: Luo and Carey, §2.1 |
| S2 | Differential files (1976) applied updates to a file merged periodically into the main one; in the 1980s the Postgres project appended all writes to a sequential log, with fast recovery, "time-travel" queries and a background "vacuum cleaner"; earlier designs lacked a principled cost model | Quote: Luo and Carey, §2.1 |
| S3 | Writes go to a memory component; an insert or update adds an entry and a delete adds an anti-matter entry; today's implementations exploit the immutability of disk components, merging them into new ones, unlike the original rolling merge, which simplifies concurrency control and recovery | Quote: Luo and Carey, §2.2.1 |
| S4 | Memory components are often skip lists or B+-trees; disk components B+-trees or SSTables, a list of data blocks of key-value pairs ordered by key plus an index block of their key ranges; disk components are also called runs, and merging them compaction | Quote: Luo and Carey, §2.2.1 and its footnotes |
| S5 | A query must reconcile components to find the latest version of a key; a point lookup searches from newest to oldest and stops at the first match; a range query merges all components through a priority queue | Quote: Luo and Carey, §2.2.1 |
| S6 | Leveling keeps one component per level, each T times larger than the last; tiering keeps up to T per level and merges them into one at the next level; leveling optimizes queries, tiering writes | Quote: Luo and Carey, §2.2.1, Figure 3 |
| S7 | A Bloom filter sets the bits of several hash functions per key and reports false positives but never false negatives; one per disk component lets a point lookup skip components | Quote: Luo and Carey, §2.2.2 |
| S8 | The false positive rate is (1 − e^(−kn/m))^k, minimized at k = (m / n) ln 2; most systems use 10 bits per key by default, giving 1% | Quote: Luo and Carey, §2.2.2 |
| S9 | Range-partitioning disk components into fixed-size SSTables is commonly adopted; it bounds the time and temporary space of each merge; partitioned leveling merges an SSTable with the overlapping SSTables of the next level | Quote: Luo and Carey, §2.2.2 |
| S10 | The cost table: writes O(T·L/B) leveling and O(L/B) tiering; point lookups O(L) and O(T·L) without Bloom filters; absent keys O(L·e^(−M/N)) and O(T·L·e^(−M/N)); existing keys O(1); short ranges O(L) and O(T·L); long ranges O(s/B) and O(T·s/B); worst-case space amplification O((T+1)/T) and O(T); L ≈ ⌈log_T((N/(B·P))·T/(T+1))⌉; under leveling a component is merged T − 1 times before it moves down | Quote: Luo and Carey, §2.3 and Table 1 |
| S11 | Space amplification is the overall number of entries divided by the number of unique entries | Quote: Luo and Carey, §2.3 |
| S12 | High write amplification also reduces the lifespan of SSDs | Quote: Luo and Carey, §3.1, "Write Amplification" |

## Recovery

T. Haerder and A. Reuter, *Principles of Transaction-Oriented Database Recovery*, ACM Computing Surveys 15(4), 1983, pages 287 to 317, [doi:10.1145/289.291](https://doi.org/10.1145/289.291), read from [a copy at the University of Texas](https://www.cs.utexas.edu/~dsb/cs386d/Readings/Recovery/Principles-of-Recovery.pdf). C. Mohan, D. Haderle, B. Lindsay, H. Pirahesh and P. Schwarz, *ARIES: A Transaction Recovery Method Supporting Fine-Granularity Locking and Partial Rollbacks Using Write-Ahead Logging*, ACM Transactions on Database Systems 17(1), 1992, pages 94 to 162, [doi:10.1145/128765.128770](https://doi.org/10.1145/128765.128770), read from [a course copy](https://cs.stanford.edu/people/chrismre/cs345/rl/aries.pdf). Used in `write-ahead-logging` and `transactions-and-isolation`.

| # | Claim | Source |
|---|-------|--------|
| H1 | Four properties of a transaction: atomicity (all or nothing, and the user knows which state they are in), consistency (a transaction reaching its normal end commits only legal results), isolation (events within a transaction are hidden from concurrent ones), durability (committed results survive any subsequent malfunctions); "These four properties ... (ACID)" | Quote: Haerder and Reuter, §1.1 |
| H2 | STEAL: modified pages may be written at any time; ¬STEAL: they stay in the buffer at least until the end of the transaction, and no logging is needed for UNDO; FORCE: all modified pages are written during end-of-transaction processing, and no partial REDO is needed; ¬FORCE: nothing is propagated then | Quote: Haerder and Reuter, §3.2.1 |
| H3 | Log data is classified as physical (the bit pattern) or logical (operators and arguments), and as state (before and after images) or transition | Quote: Haerder and Reuter, §3.2.2 and Table 2 |
| H4 | The transaction concept was restricted to database systems by Eswaran and others (1976) and given its current name | Quote: Haerder and Reuter, §1.1 |
| R1 | The WAL protocol: log records representing changes must be on stable storage before the changed data replaces the previous version on nonvolatile storage, at least the undo portions; every page stores the LSN of the log record of its most recent update | Quote: ARIES, §1.1 |
| R2 | Steal and force as buffer policies; even with large memories steal is very desirable, since with no-steal and fine-granularity locking a page may never get written if it always contains uncommitted updates, worse with long-running transactions | Quote: ARIES, §1.4 and §2 |
| R3 | The buffer manager may have to force the log up to the LSN of a dirty page before writing the page | Quote: ARIES, §1.4 |
| R4 | Restart: an analysis pass from the first record of the last checkpoint to the end of the log finds the dirty pages, the losers and where redo starts; the redo pass repeats history for every transaction, losers included, redoing an update when the page's LSN is less than the record's; the undo pass rolls the losers back in reverse chronological order in one sweep, unconditionally | Quote: ARIES, §3 and §6 |
| R5 | Compensation log records are redo-only and never undone; their UndoNxtLSN points to the next record to undo; logging during rollbacks stays bounded even with repeated failures or nested rollbacks | Quote: ARIES, abstract and §3 |
| R6 | Fuzzy checkpoints are taken while processing continues; the end-checkpoint record holds the transaction table and the dirty pages table, each dirty page with its RecLSN, from which point its disk version may lack updates | Quote: ARIES, §5.4 and §4 |
| R7 | In the shadow page technique an updated page is written to a different location and the previous version is used for recovery until the next checkpoint; System R paradigms based on it must change under WAL | Quote: ARIES, §1.1 |
| R8 | ARIES supports partial rollbacks, fine-granularity locking, fuzzy checkpoints, media recovery and parallel restart, with page-oriented redo and logical undo; a key moved by another transaction from page 10 to page 20 is undone by retraversing the tree | Quote: ARIES, abstract and §3 |

## Isolation

H. Berenson, P. Bernstein, J. Gray, J. Melton, E. O'Neil and P. O'Neil, *A Critique of ANSI SQL Isolation Levels*, SIGMOD 1995, pages 1 to 10, [doi:10.1145/223784.223785](https://doi.org/10.1145/223784.223785), read from [arXiv:cs/0701157](https://arxiv.org/abs/cs/0701157), whose pages carry the SIGMOD citation. A. Fekete, E. O'Neil and P. O'Neil, *A Read-Only Transaction Anomaly Under Snapshot Isolation*, ACM SIGMOD Record 33(3), 2004, pages 12 to 14, [doi:10.1145/1031570.1031573](https://doi.org/10.1145/1031570.1031573), read from [the authors' copy](https://www.cs.umb.edu/~poneil/ROAnom.pdf). A. Fekete, D. Liarokapis, E. O'Neil, P. O'Neil and D. Shasha, *Making Snapshot Isolation Serializable*, ACM Transactions on Database Systems 30(2), 2005, pages 492 to 528, [doi:10.1145/1071610.1071615](https://doi.org/10.1145/1071610.1071615), read from [a course copy](https://classpages.cselabs.umn.edu/Spring-2018/csci8980/Papers/ConcurrencyControl/serializable-snapshot.pdf). D. R. K. Ports and K. Grittner, *Serializable Snapshot Isolation in PostgreSQL*, Proceedings of the VLDB Endowment 5(12), 2012, pages 1850 to 1861, [doi:10.14778/2367502.2367523](https://doi.org/10.14778/2367502.2367523), read from [arXiv:1208.4179](https://arxiv.org/abs/1208.4179). Used in `transactions-and-isolation`, `mvcc-and-snapshot-isolation` and `write-ahead-logging`.

| # | Claim | Source |
|---|-------|--------|
| I1 | A transaction transforms the database from one consistent state to another; histories in the notation r1[x], w1[x], c1, a1; two actions conflict when distinct transactions touch the same item and one writes; conflicting pairs are the edges of the dependency graph; equivalent histories have the same committed transactions and dependency graph; a history is serializable when equivalent to a serial one | Quote: Berenson and others, §2.1 |
| I2 | The phenomena P1 (dirty read), P2 (fuzzy or non-repeatable read), P3 (phantom), and their strict forms A1, A2, A3 | Quote: Berenson and others, §2.2 and §3 |
| I3 | The ANSI levels by the three phenomena (Table 1) | Quote: Berenson and others, Table 1 |
| I4 | Read and write locks conflict when one is a write lock; a predicate lock covers every item satisfying a search condition, phantoms included; well-formed and two-phase transactions; long duration locks are held until commit or abort; well-formed two-phase locking guarantees serializability | Quote: Berenson and others, §2.3 |
| I5 | The locking levels: read uncommitted takes no read locks; read committed short read locks; repeatable read long item read locks and short predicate read locks; serializable long read locks on items and predicates; long write locks at every level from degree 1 | Quote: Berenson and others, Table 2 |
| I6 | Degrees 1, 2 and 3 of Gray, Lorie, Putzolu and Traiger correspond to locking read uncommitted, read committed and serializable; no degree matches locking repeatable read; "Repeatable Reads" first meant serializable, and the ANSI meaning is called unfortunate; that paper was originally published in 1977 | Quote: Berenson and others, §2.3 and the reference [GLPT] |
| I7 | P0, dirty write; without protection from it, a rollback cannot restore before-images without wiping out another transaction's write; even the weakest locking systems hold long write locks; Remark 3: P0 should be required at every level | Quote: Berenson and others, §3 |
| I8 | History H1, a transfer of 40 between x and y keeping a total of 100, read by T2 as 60; H1 violates none of A1, A2 and A3 | Quote: Berenson and others, §3 |
| I9 | The English phenomena are ambiguous (broad and strict interpretations); the phenomena are incomplete (Remark 5) | Quote: Berenson and others, §2.2 and §3 |
| I10 | P4, lost update, and history H4: r1[x=100] r2[x=100] w2[x=120] c2 w1[x=130] c1 | Quote: Berenson and others, §4.1 |
| I11 | Cursor stability holds a read lock on the current row of a cursor and is designed to prevent the lost update | Quote: Berenson and others, §4.1 and Table 2 |
| I12 | Snapshot isolation: reads from a snapshot of committed data as of the start timestamp; sees its own writes; never blocked reading; a commit timestamp larger than any existing; commits only if no transaction with a commit timestamp in its interval wrote data it also wrote (first-committer-wins), which prevents lost updates; visible to transactions that start later | Quote: Berenson and others, §4.2 |
| I13 | Snapshot isolation extends the Multiversion Mixed Method, which allowed snapshot reads by read-only transactions; its histories map to single-valued histories preserving data flow | Quote: Berenson and others, §4.2 |
| I14 | "Snapshot Isolation is non-serializable because a transaction's Reads come at one instant and the Writes at another"; history H5 with the constraint that x + y stays positive | Quote: Berenson and others, §4.2 |
| I15 | A5A, read skew, and A5B, write skew, with their histories | Quote: Berenson and others, §4.2 |
| I16 | Read committed is weaker than snapshot isolation (Remark 8); repeatable read and snapshot isolation are incomparable (Remark 9); snapshot isolation precludes A1, A2 and A3 (Remark 10) | Quote: Berenson and others, §4.2 |
| I17 | Tasks under a predicate may add up to 8 hours; two transactions each find 7 and add a 1-hour task; first-committer-wins does not catch it | Quote: Berenson and others, §4.2 |
| I18 | Snapshot isolation allows transactions with very old timestamps ("time travel"); update transactions with old timestamps abort if they update data changed since | Quote: Berenson and others, §4.2 |
| I19 | A long-running update transaction is unlikely to be the first writer of everything it writes, and so will probably abort | Quote: Berenson and others, §4.2 |
| F1 | First-committer-wins checks only the items a transaction writes, not those it reads | Quote: Fekete, O'Neil and O'Neil, §1 |
| F2 | Write skew: a married couple's checking balances x and y, with x + y > 0 allowed, x = 70 and y = 80, each transaction subtracting 100 from one account; the final state violates the constraint | Quote: Fekete, O'Neil and O'Neil, §2, Example 1.2 |
| F3 | Two fixes: make the read of the other balance behave like a write (select for update), or materialize the constraint in a row both update | Quote: Fekete, O'Neil and O'Neil, §2 |
| F4 | The read-only anomaly: a deposit of 20 to savings, a withdrawal of 10 from checking with an overdraft charge of 1, and a read-only transaction that prints X = 0 and Y = 20 while the final values are X = −11 and Y = 20; without the read-only transaction the updates always execute serializably | Quote: Fekete, O'Neil and O'Neil, abstract and §3, Example 1.3 |
| F5 | A variant enforces the rule at update time with write locks, which these authors call first updater wins; either way one of two concurrent updaters of an item aborts | Quote: Fekete, O'Neil and O'Neil, §1; Fekete and others 2005, §1.1 |
| D1 | Theorem 2.1: in a non-serializable snapshot isolation history, every cycle of the serialization graph has three consecutive transactions, the first and third possibly the same, with concurrent rw-antidependency edges from the first to the second and from the second to the third | Quote: Fekete and others 2005, §2.2, Theorem 2.1 and Lemma 2.3 |
| D2 | A static dependency graph of an application's programs with no dangerous structure means every execution under snapshot isolation is serializable; the converse does not hold | Quote: Fekete and others 2005, §3.2, Definition 3.5 and the text after Theorem 3.1 |
| G1 | The wr-dependency, ww-dependency and rw-antidependency, in which T1 writes a version of an object whose previous version T2 read, so T1 appears to have executed after T2 | Quote: Ports and Grittner, §3.2 |
| G2 | SSI, introduced by Cahill and others (SIGMOD 2008), checks for a "dangerous structure" of two adjacent rw-antidependency edges and aborts one of the transactions involved; it ensures serializability with false positives, costs less than testing for cycles, and need not track wr and ww edges | Quote: Ports and Grittner, §3.3 and reference [7] |
| G3 | SIREAD locks do not block conflicting writes; a conflict between a SIREAD lock and a write lock flags an rw-antidependency | Quote: Ports and Grittner, §3.3 |
| G4 | SSI allows some rw-conflicts that strict two-phase locking and optimistic concurrency control both prevent | Quote: Ports and Grittner, §3.3 |
| G5 | The first implementation of SSI in a production database release, PostgreSQL 9.1; its serializable mode cost less than 7% relative to snapshot isolation in their benchmarks | Quote: Ports and Grittner, abstract |

## Query optimization

P. G. Selinger, M. M. Astrahan, D. D. Chamberlin, R. A. Lorie and T. G. Price, *Access Path Selection in a Relational Database Management System*, SIGMOD 1979, pages 23 to 34, [doi:10.1145/582095.582099](https://doi.org/10.1145/582095.582099), read from [a course copy](https://courses.cs.duke.edu/compsci516/cps216/spring03/papers/selinger-etal-1979.pdf). Crossref records the first page, 23; the copy ends on page 34. Used in `query-planning-and-joins` and `b-tree-indexes`.

| # | Claim | Source |
|---|-------|--------|
| Q1 | System R is an experimental database management system based on the relational model | Quote: Selinger and others, §1 |
| Q2 | COST = PAGE FETCHES + W × (RSI CALLS), a weighted measure of I/O and CPU, RSI calls being the predicted tuples returned from the storage layer | Quote: Selinger and others, §4 |
| Q3 | The statistics: NCARD, TCARD, P, ICARD and NINDX; updated by an UPDATE STATISTICS command any user can run, not on every insert, delete or update, because of the extra operations and the locking bottleneck at the catalogs | Quote: Selinger and others, §4 |
| Q4 | The selectivity factors of Table 1, with their assumptions: column = value, column1 = column2, open-ended comparisons, BETWEEN, IN (at most 1/2); 1/3 has "no significance" other than being less selective than the guess for an equality without an index and less than 1/2 | Quote: Selinger and others, §4, Table 1 |
| Q5 | The query cardinality is the product of the cardinalities of the FROM list times the product of the selectivity factors | Quote: Selinger and others, §4 |
| Q6 | A lack of statistics is taken to mean the relation is small | Quote: Selinger and others, §4 |
| Q7 | An order is interesting when GROUP BY or ORDER BY names it, and every join column defines one; the cheapest path is kept for each interesting order and for the unordered case; equivalence classes such as E.DNO = D.DNO = F.DNO | Quote: Selinger and others, §4 and §5 |
| Q8 | The costs of a clustered index scan, F(preds) × (NINDX + TCARD), and of a non-clustered one, F(preds) × (NINDX + NCARD) unless it fits in the buffer | Quote: Selinger and others, §4, Table 2 |
| Q9 | Blasgen and Eswaran (1976) found that, for other than very small relations, one of two join methods was always optimal or near optimal | Quote: Selinger and others, §5 |
| Q10 | Nested loops and merging scans; merging scans apply only to equi-joins, sort an input without an index on the join column into a temporary list, and avoid rescanning the inner relation | Quote: Selinger and others, §5 |
| Q11 | n relations have n! join orders; once k are joined, how to join the next is independent of their order; the search finds the best way to join successively larger subsets; n-way joins are sequences of 2-way joins of a composite outer and an inner relation; only orders with a join predicate to the relations already joined are considered when possible, so Cartesian products come as late as possible | Quote: Selinger and others, §5 |
| Q12 | For each set of relations the estimated cardinality is saved, with the cheapest solution for the unordered case and for each interesting order | Quote: Selinger and others, §5 |
| Q13 | C-nested-loop = C-outer + N × C-inner; the merge has the same form, the inner scan reading the group matching one join value, plus sorts; composite relations are stored only when a sort is needed | Quote: Selinger and others, §5 |
| Q14 | Typical cases needed a few thousand bytes of storage and a few tenths of a second of CPU time; joins of 8 tables were optimized in a few seconds | Quote: Selinger and others, §5 |

## PostgreSQL

| # | Claim | Source |
|---|-------|--------|
| P1 | Every table and index is an array of fixed-size pages, usually 8 kB, selectable when compiling; in a table every page is equivalent, so a row can be stored in any page | Quote: [*Database Page Layout*](https://www.postgresql.org/docs/current/storage-page-layout.html) |
| P2 | The page header is 24 bytes; item identifiers are 4 bytes each, an offset and a length; new identifiers are allocated from the start of the free space, items from its end | Quote: *Database Page Layout*, Table 66.2 and the text after it |
| P3 | An item identifier is never moved until freed, so it can reference an item long-term even when the item moves to compact free space; an ItemPointer, also known as CTID, is a page number and an item identifier's index | Quote: *Database Page Layout* |
| P4 | A row has a fixed header of 23 bytes on most machines, an optional null bitmap of one bit per column, and data starting at an offset that is a multiple of MAXALIGN | Quote: *Database Page Layout*, §66.6.1 |
| P5 | The page header's `pd_lsn` is the WAL position just past the record of the page's last change | Quote: *Database Page Layout*, Table 66.3 |
| P6 | Without ORDER BY, rows are returned in whatever order the system finds fastest to produce | Quote: [*SELECT*](https://www.postgresql.org/docs/current/sql-select.html), Description |
| P7 | A table or index over 1 GB is split into gigabyte-sized segment files, avoiding file size limits of some platforms; 1 GB is the default, set when building | Quote: [*Database File Layout*](https://www.postgresql.org/docs/current/storage-file-layout.html) |
| P8 | The free space map keeps one byte per heap page, in a tree of map pages | Quote: [*Free Space Map*](https://www.postgresql.org/docs/current/storage-fsm.html) |
| P9 | The visibility map keeps two bits per heap page: all-visible, and all-frozen | Quote: [*Visibility Map*](https://www.postgresql.org/docs/current/storage-vm.html) |
| P10 | MVCC updates add new row versions, which can need new index entries; a heap-only tuple needs none when no indexed column changes (summarizing indexes aside) and the old row's page has room; the identifier indexes point to becomes a redirect to the oldest version still possibly visible; lowering `fillfactor` makes such updates more likely | Quote: [*Heap-Only Tuples (HOT)*](https://www.postgresql.org/docs/current/storage-hot.html) |
| P11 | Rows cannot span pages; TOAST compresses or moves large values out of line, into a separate table, when a row is wider than TOAST_TUPLE_THRESHOLD, normally 2 kB | Quote: [*TOAST*](https://www.postgresql.org/docs/current/storage-toast.html) |
| P12 | A table's fillfactor below 100 makes inserts pack pages only to that percentage, leaving room for updates on the same page | Quote: [*CREATE TABLE*](https://www.postgresql.org/docs/current/sql-createtable.html), storage parameters |
| P13 | Disks write whole sectors, commonly 512 bytes; PostgreSQL typically writes 8,192 bytes, 16 sectors, at a time; a power failure can leave a page partly written; full page images in the WAL let recovery restore it | Quote: [*Reliability*](https://www.postgresql.org/docs/current/wal-reliability.html) |
| P14 | The B-tree is a multi-way balanced tree; an entry cannot exceed about a third of a page | Quote: [*B-Tree Indexes*](https://www.postgresql.org/docs/current/btree.html), §65.1.1 |
| P15 | Page splits cascade upward; a root split adds a level; typically over 99% of pages are leaves | Quote: *B-Tree Indexes*, §65.1.4.1 |
| P16 | Bottom-up index deletion removes entries of old versions from updates that did not change indexed columns, usually avoiding a page split; before PostgreSQL 14 only simple deletion existed | Quote: *B-Tree Indexes*, §65.1.4.2 |
| P17 | Deduplication stores a key once with a sorted array of TIDs, a posting list; it is enabled by default; a long-running transaction holding a snapshot blocks garbage collection | Quote: *B-Tree Indexes*, §65.1.4.3 |
| P18 | A B-tree serves `<`, `<=`, `=`, `>=`, `>`, BETWEEN, IN, IS NULL, and LIKE patterns anchored at the start (with the C locale or a special operator class); it can return sorted rows; CREATE INDEX makes a B-tree by default | Quote: [*Index Types*](https://www.postgresql.org/docs/current/indexes-types.html), §11.2.1 |
| P19 | A hash index stores a 32-bit hash code and handles only equality | Quote: *Index Types*, §11.2.2 |
| P20 | A multicolumn B-tree is most efficient with constraints on the leading columns: equality on leading columns plus an inequality on the first column without equality limit the scanned part; later columns are checked in the index; skip scan applies them through repeated index searches | Quote: [*Multicolumn Indexes*](https://www.postgresql.org/docs/current/indexes-multicolumn.html) |
| P21 | Skip scans of B-tree indexes arrived in PostgreSQL 18 | Quote: [*Release 18*](https://www.postgresql.org/docs/18/release-18.html); the PostgreSQL 17 page on multicolumn indexes has no skip scan |
| P22 | All indexes are secondary; heap access in an index scan is largely random; bitmap scans sort the heap accesses, which only goes so far; an index-only scan skips the heap when the visibility map's all-visible bit is set | Quote: [*Index-Only Scans and Covering Indexes*](https://www.postgresql.org/docs/current/indexes-index-only-scans.html) |
| P23 | A B-tree's fillfactor sets how full an initial build packs the leaves; the default is 90 | Quote: [*CREATE INDEX*](https://www.postgresql.org/docs/current/sql-createindex.html), storage parameters |
| P24 | Changes to data files are written only after the WAL records describing them are flushed; at commit only the WAL is flushed; it is written sequentially; one fsync can commit many small concurrent transactions | Quote: [*Write-Ahead Logging*](https://www.postgresql.org/docs/current/wal-intro.html) |
| P25 | A checkpoint flushes all dirty pages and writes a checkpoint record; recovery starts from the redo record it names; older segments can be recycled; checkpoints start every `checkpoint_timeout` or before `max_wal_size` is exceeded, 5 minutes and 1 GB by default | Quote: [*WAL Configuration*](https://www.postgresql.org/docs/current/wal-configuration.html) |
| P26 | More frequent checkpoints make recovery faster but flush more; with `full_page_writes`, on by default, the first change of each page after a checkpoint logs the whole page | Quote: *WAL Configuration* and [*Write Ahead Log* settings](https://www.postgresql.org/docs/current/runtime-config-wal.html), `full_page_writes` |
| P27 | Since replay always starts from a checkpoint, one full page image per page after each checkpoint suffices | Quote: *Write Ahead Log* settings, `full_page_writes` |
| P28 | An LSN is a byte offset into the WAL, increasing with each record; LSNs are compared to measure replication and recovery progress; WAL segment files are normally 16 MB, divided into 8 kB pages | Quote: [*WAL Internals*](https://www.postgresql.org/docs/current/wal-internals.html) |
| P29 | Asynchronous commit may lose the most recent transactions in a crash but not corrupt data; the window is at most three times `wal_writer_delay`; a bank would not use it for a transaction recording an ATM's cash; `fsync = off` can cause arbitrarily bad corruption after an operating system or hardware crash | Quote: [*Asynchronous Commit*](https://www.postgresql.org/docs/current/wal-async-commit.html) |
| P30 | Each statement sees a snapshot; with MVCC, reading never blocks writing and writing never blocks reading, even at serializable through SSI | Quote: [*Introduction*](https://www.postgresql.org/docs/current/mvcc-intro.html) to concurrency control |
| P31 | The standard defines serializable by one-at-a-time execution and the other levels by phenomena; Table 13.1 of the levels; any of the four can be requested but three are implemented, read uncommitted behaving like read committed; phantoms are "allowed, but not in PG" at repeatable read | Quote: [*Transaction Isolation*](https://www.postgresql.org/docs/current/transaction-iso.html), §13.2 |
| P32 | Read committed is the default; an UPDATE that finds a row updated by a concurrent transaction waits, then applies its change to the updated version, re-evaluating its WHERE clause; the example of transferring money between accounts | Quote: *Transaction Isolation*, §13.2.1 |
| P33 | Repeatable read is snapshot isolation; it waits for a concurrent updater of the same row and fails with `could not serialize access due to concurrent update` if that one commits; the transaction should be retried from the beginning; enforcing business rules there needs careful explicit locking; a read-only transaction can see a control record of a completed batch without one of its detail records; some other systems offer repeatable read and snapshot isolation as distinct levels | Quote: *Transaction Isolation*, §13.2.2 |
| P34 | Serializable is SSI; predicate locks never block and cannot cause deadlocks; data read is not valid until the transaction commits; locks depend on the plan, a sequential scan takes a relation-level predicate lock, and fine locks may be combined into coarser ones, raising failure rates | Quote: *Transaction Isolation*, §13.2.3 |
| P35 | Serialization failures have SQLSTATE 40001 and must be retried; deadlocks (40P01) may be; unique-key violations can effectively be serialization failures; retry the complete transaction, including the logic deciding what to issue | Quote: [*Serialization Failure Handling*](https://www.postgresql.org/docs/current/mvcc-serialization-failure-handling.html) |
| P36 | Row-level locks block only writers and lockers of the same row, not queries; FOR UPDATE makes other updaters, deleters and lockers of the rows wait until the transaction ends | Quote: [*Explicit Locking*](https://www.postgresql.org/docs/current/explicit-locking.html), §13.3.2 |
| P37 | PostgreSQL detects deadlocks and aborts one of the transactions; acquiring locks in a consistent order is the best defense | Quote: *Explicit Locking*, §13.3.4 |
| P38 | NOWAIT and SKIP LOCKED; skipping locked rows gives an inconsistent view, unsuitable for general work but useful for queue-like tables | Quote: *SELECT*, the locking clause |
| P39 | UPDATE and DELETE leave the old version until no transaction can see it; VACUUM reclaims it; standard VACUUM runs alongside normal work and returns space to the operating system only at the end of a table; VACUUM FULL rewrites the table under an ACCESS EXCLUSIVE lock; disabling autovacuum completely is unwise unless the workload is extremely predictable | Quote: [*Routine Vacuuming*](https://www.postgresql.org/docs/current/routine-vacuuming.html), §24.1.1 and §24.1.2 |
| P40 | Transaction ids are 32 bits, compared modulo 2³², so two billion are older and two billion newer; more than 4 billion transactions wrap around; VACUUM freezes old versions; every table must be vacuumed at least once every two billion transactions | Quote: *Routine Vacuuming*, §24.1.5 |
| P41 | The planner creates a sequential scan for every table and index scans for matching indexes; nested loop, merge and hash join as described; near-exhaustive search below `geqo_threshold`, preferring pairs with a join clause, all plans for every pair considered; heuristics (the genetic optimizer) above it, reasonable and not necessarily optimal; the finished plan tree | Quote: [*Planner/Optimizer*](https://www.postgresql.org/docs/current/planner-optimizer.html) |
| P42 | Costs are in arbitrary units, conventionally page fetches with `seq_page_cost` 1.0; EXPLAIN ANALYZE runs the query and shows actual rows and milliseconds; whether estimated rows are close to reality matters most; dead-on estimates are quite unusual | Quote: [*Using EXPLAIN*](https://www.postgresql.org/docs/current/using-explain.html) |
| P43 | Row and page counts are not updated on the fly; ANALYZE and VACUUM ANALYZE update the planner's statistics, which are approximate even when fresh | Quote: [*Statistics Used by the Planner*](https://www.postgresql.org/docs/current/planner-stats.html) |
| P44 | `seq_page_cost` 1.0 and `random_page_cost` 4.0 by default, the latter lower than real random access because most random reads are assumed cached; `geqo_threshold` 12; `join_collapse_limit` defaults to `from_collapse_limit`, eight, and 1 fixes the written join order, for advanced users | Quote: [*Query Planning* settings](https://www.postgresql.org/docs/current/runtime-config-query.html) |

## SQLite

| # | Claim | Source |
|---|-------|--------|
| L1 | The page size is a power of two between 512 and 65,536; all pages of a database are the same size | Quote: [*Database File Format*](https://www.sqlite.org/fileformat2.html), §1.3 |
| L2 | A B-tree page holds a header of 8 or 12 bytes, a cell pointer array of 2-byte offsets in key order, unallocated space and the cell content area, placed toward the end to leave room for the pointer array | Quote: *Database File Format*, §1.6 |
| L3 | Table B-trees use a 64-bit signed integer key, the rowid, and store all data in the leaves; index B-trees have arbitrary keys and no data; an interior page holds K keys and K + 1 pointers; large index keys go to overflow pages so every interior page holds at least 4 keys | Quote: *Database File Format*, §1.6 |
| L4 | A payload too large for the page continues in a linked list of overflow pages | Quote: *Database File Format*, §1.6 |
| L5 | Corresponding rows of an index and its table share the same rowid | Quote: *Database File Format*, §2.5 |
| L6 | Before changing the database file, SQLite writes the original content of the pages into a rollback journal; the transaction commits when the journal is deleted; a hot journal left by a crash is played back; moving or renaming either file hides it | Quote: [*Atomic Commit In SQLite*](https://www.sqlite.org/atomiccommit.html), §3.5, §3.11, §4.2 and §9.5 |
| L7 | A new file may exist only in the operating system's cache until later; SQLite assumes a flush or fsync does not return until writes are done, and has been told these primitives are broken on some systems | Quote: *Atomic Commit In SQLite*, §2 and §3.5 |
| L8 | In WAL mode the database keeps the original content and changes are appended to the WAL; a commit is a commit record appended; a checkpoint copies changes back, automatically at 1,000 pages by default; a reader keeps an end mark and reads as of it; readers do not block writers nor writers readers | Quote: [*Write-Ahead Logging*](https://www.sqlite.org/wal.html), §1 and §2 |
| L9 | Except for shared cache with read uncommitted, all transactions are serializable, by serializing the writes: one writer at a time | Quote: [*Isolation In SQLite*](https://www.sqlite.org/isolation.html) |
| L10 | Rollback (DELETE) mode is the default and locks readers out while a writer changes the file; WAL mode exists since 3.7.0 (2010-07-21) and gives readers snapshot isolation | Quote: *Isolation In SQLite* |
| L11 | Joins are computed as nested loops, one per table, each a full scan or using an index | Quote: [*The Next-Generation Query Planner*](https://www.sqlite.org/queryplanner-ng.html), §2.1; [*The SQLite Query Optimizer Overview*](https://www.sqlite.org/optoverview.html) |
| L12 | The next generation query planner arrived in 3.8.0 (2013-08-26); its N nearest neighbors search keeps the N best paths at each step | Quote: *The Next-Generation Query Planner*, §1 and §3.4 |

## Python

The documentation as served at docs.python.org/3.

| # | Claim | Source |
|---|-------|--------|
| Y1 | `OrderedDict` handles frequent reordering, which suits LRU caches; `move_to_end` and `popitem(last=False)` | Quote: [`collections`](https://docs.python.org/3/library/collections.html); run: `buffer_pool.py` |
| Y2 | A topological order exists if and only if the graph has no directed cycle; `CycleError` holds the detected cycle in `args[1]`, each node an immediate predecessor of the next and the first repeated at the end | Quote: [`graphlib`](https://docs.python.org/3/library/graphlib.html); run: `schedules.py` |
| Y3 | `zlib.crc32` computes an unsigned 32-bit checksum | Quote: [`zlib`](https://docs.python.org/3/library/zlib.html); run: `torn_page.py` |
| Y4 | `struct` packs and unpacks offsets into a byte buffer | Quote: [`struct`](https://docs.python.org/3/library/struct.html); run: `slotted_page.py` |

## The examples and the arithmetic

| # | Claim | Source |
|---|-------|--------|
| E1 | After four inserts 17 bytes are free; the 28-byte record fails before and after deleting slot 1, with 31 bytes free in two pieces; compaction moves slot 2 from byte 72 to 86 and slot 3 from 37 to 51; the insert then reuses slot 1 | Run: `slotted_page.py` |
| E2 | Hot pages: 12 requests, 9 hits, 3 reads; a scan of 4 pages twice through 3 frames: no hit; of 3 pages: 3 hits; page 7 changed 5 times: 1 write; 5 pages changed once: 5 writes | Run: `buffer_pool.py` |
| E3 | 512 entries per page; levels for 10³ to 10¹² keys: 10, 20, 30, 40 for a binary tree, 2, 3, 4 (5 for fan-out 100), 5 (6) for pages | Run: `fanout.py` |
| E4 | Full scan 1,000 pages; the index on `order_id`: 10 page reads; on `customer`: 1,000 reads over 951 distinct pages | Run: `heap_fetches.py` |
| E5 | The runs after 6 and 9 writes; `fig` found in 1 run, `lime` as a tombstone in 2, `date` absent after 3; 9 entries written, 13 after compaction; every read then searches 1 run | Run: `tiny_lsm.py` |
| E6 | Leveling 45,056 entries written, 11.0 per key, at most 4 runs; tiering 20,480, 5.0 per key, at most 12 runs | Run: `merge_policies.py` |
| E7 | With the rule: on disk A = 60, B = 80, C = 10, log LSNs 1 to 5; redo LSN 3; undo LSNs 5 and 2 with compensation LSNs 6 and 7; A = 70, B = 50, C = 40. Without: the log holds LSNs 1 to 4, and A = 60 survives | Run: `crash_recovery.py` |
| E8 | The torn page carries LSN 9 with the old data and a failing checksum; redo of LSN 9 skips it; the logged image is valid | Run: `torn_page.py` |
| E9 | H4, H1 and H5 have a cycle T1 → T2 → T1; the harmless interleaving has only T1 → T2 and is equivalent to T1 then T2 | Run: `schedules.py` |
| E10 | Plain reads deadlock on the upgrade and T2 is aborted, stock 6; reads for update give 7 with no abort; opposite transfers deadlock; same-order transfers end at a = 30, b = 70 | Run: `two_phase_locking.py` |
| E11 | The lost update aborts T2, which retried gives 7; write skew commits both, x + y = −50; serially T2 refuses, 50; covered, T2 aborts, 50; the phantom commits both, 9 hours | Run: `write_skew.py` |
| E12 | 13 rows from each method; 84 comparisons, 20 inserts and lookups, 19 merge steps; order 104 is not returned | Run: `join_methods.py` |
| E13 | Uniform data: 1,010 rows for the orders starting from regions or stores then regions, 5,000 for those joining sales second; two orders skipped; estimate 1,000. Skewed: 2,810 and 6,800, estimate still 1,000 | Run: `join_orders.py` |
| M1 | 8,192-byte pages, 24-byte header, 4-byte slot, 24-byte row header and 100 bytes of data: 128 bytes per row, 63 rows per page; 1,000,000 rows fill 15,874 pages, about 124 MiB; a 4-byte integer row carries 27 bytes of header and slot | Arithmetic |
| M2 | 256⁵ ≈ 1.1 · 10¹², over a trillion; 512⁴ ≈ 6.9 · 10¹⁰ | Arithmetic |
| M3 | 1,000 random reads at 4.0 against 1,000 sequential at 1.0: about 4,000 against 1,000 | Arithmetic |
| M4 | ⌈log_4(256 · 4 / 5)⌉ = ⌈3.84⌉ = 4 levels | Arithmetic |
| M5 | 10 · ln 2 ≈ 6.93; (1 − e^(−0.7))⁷ ≈ 0.0082 | Arithmetic |
| M6 | C(8, 3) = 56; C(20, 10) = 184,756 | Arithmetic |
| M7 | H4 run serially ends at 100 + 20 + 30 = 150; the write skew ends at −30 + −20 = −50; serially T2 sees −30 + 80 = 50 | Arithmetic |
| M8 | 1,000 updates a second for 3,600 seconds: 3.6 million versions | Arithmetic |
| M9 | 14 × 6 = 84; 3! = 6; 10! = 3,628,800 against 2¹⁰ = 1,024 subsets | Arithmetic |

That is 176 sourced facts: 7 from Bayer and McCreight, 7 from Comer, 11 from O'Neil and others, 12 from Luo and Carey, 4 from Haerder and Reuter, 8 from ARIES, 19 from Berenson and others, 5 from Fekete, O'Neil and O'Neil, 2 from Fekete and others, 5 from Ports and Grittner, 14 from Selinger and others, 44 from the PostgreSQL documentation, 12 from the SQLite documentation, 4 from Python's documentation, 13 from running the examples and 9 computed.

## Conclusions the guides draw themselves

The main conclusions the guides draw from the facts above, without attributing them to a source:

| Where | Statement | Grounds |
|-------|-----------|---------|
| `pages-and-records`, The idea | Without an index, a lookup by value reads every page of a heap | P1, P6 |
| `pages-and-records`, A worked example | A pool that evicts the least recently used page gets no hit on a repeated scan larger than itself; a miss with a dirty victim costs two disk operations | E2 and the eviction rule of the example |
| `b-tree-indexes`, How shallow | The top levels tend to stay in the buffer pool | Every lookup reads them (B2, C2), and a pool keeps what is used often (E2) |
| `b-tree-indexes`, Complexity | The CPU cost of a search is O(log n), like a binary tree's; the difference is the number of pages | C2, C3 |
| `lsm-trees-and-compaction`, The idea | In a large index with keys in no order, nearly every B-tree insert lands on a leaf not in the buffer pool | O1 and the in-place updates of S1 |
| `lsm-trees-and-compaction`, Common traps | A tombstone may be dropped only in a merge that includes every older run | S3, S5, E5 |
| `write-ahead-logging`, A worked example | Without the write-ahead rule, an uncommitted value can survive recovery | R1, R4, E7 |
| `write-ahead-logging`, A torn page | Redo skips a torn page whose first sector already carries the new LSN | R4's redo condition, P13, E8 |
| `write-ahead-logging`, Common traps | Comparing the page LSN with the record's makes redo safe to repeat | R4 |
| `transactions-and-isolation`, The idea | A history is serializable when its dependency graph has no cycle | I1's definitions and Y2 |
| `transactions-and-isolation`, Complexity | Deadlocks are found as cycles of waits | E10's detector; P37 states only that PostgreSQL detects and resolves them |
| `mvcc-and-snapshot-isolation`, Old versions | One long-running transaction holds back the cleanup of every table it might read | P39, P17 |
| `mvcc-and-snapshot-isolation`, Serializable snapshot isolation | The write skew has rw-antidependencies both ways | G1 applied to F2 |
| `query-planning-and-joins`, The idea | Multiplying the factors assumes the conditions are independent | Q5 |
| `query-planning-and-joins`, A worked example | Skewed values make the uniform rules mis-estimate, here by 2.8 times | Q4, E13 |

## Citations and names

The guides endorse no product and name no company's product. They name PostgreSQL and SQLite as open-source illustrations, each fact cited from the project's own documentation; System R, the experimental system of the 1979 paper they cite; the Postgres research project, as the LSM survey describes it; and Python's standard library, the language of the examples. Papers are cited by their authors, as the other guides do. Boeing appears once, in the history of the name "B-tree" as Comer tells it and in the bibliographic record of the 1970 report, because the authors worked there.

Not repeated from the sources: the authors' affiliations; the commercial systems named in the ARIES paper, in Berenson and others' critique, in the two Fekete papers and in the LSM survey's examples of key-value stores; the hardware named by Bayer and McCreight and by Selinger and others; the benchmarks named in several papers; the file system named in PostgreSQL's documentation on full page writes; and the company that, with Date, first used "repeatable read" to mean serializable.

## Not verified

- The 1972 journal text of Bayer and McCreight was not read: the publisher's link returned an HTML page, not the article. Every claim B1 to B7 comes from the 1970 report, which the 1972 paper revises; the guide cites the 1972 paper and says the work first appeared in 1970.
- Cahill, Röhm and Fekete's SSI paper (SIGMOD 2008) was not read; the copy found online returned an HTML page. The guides describe SSI as Ports and Grittner describe it, and take its year from their reference list.
- Gray, Lorie, Putzolu and Traiger's degrees of consistency, Blasgen and Eswaran's 1976 study of join methods, Eswaran and others' 1976 paper, Bloom's 1970 paper and the 1976 paper on differential files were not read; each is attributed through the paper that cites it.
- O'Neil and others was read from the authors' copy marked "To be published", Luo and Carey from arXiv and Berenson and others from arXiv, not from the journals' final texts.
- The term "tombstone" is in neither LSM source; the guide introduces it as its own word for what the survey calls an anti-matter entry and O'Neil and others a delete node entry.
- PostgreSQL's documentation gives the row header as 23 bytes and the alignment as MAXALIGN, without a value; the guide's 24-byte row header is a stated assumption of its model ("on a machine that aligns to 8 bytes").
- Whether PostgreSQL's full page image holds the page before or after the change that logs it was not checked. The example logs the page as written by the change; the guide says only that the image lets recovery rebuild the page.
- PostgreSQL's deadlock detection algorithm and its buffer replacement policy were not read; the guides say only that it detects deadlocks and aborts one transaction, and say nothing about its replacement policy.
- The Graefe surveys were not read; the guides cite none of them, and the hash join is described from PostgreSQL's documentation.
- The ACM Digital Library was not used; bibliographic data comes from Crossref, and each text from the copy linked above.

## Links to guides on other branches

The distributed systems path has a guide on consistency models, and the operating systems path guides on locks and deadlock; both paths are on `release/v0.48-integration`, not on `main`, where this branch starts. So `transactions-and-isolation` and `mvcc-and-snapshot-isolation` name "the guide on consistency models in the distributed systems path" in prose, without a link and without listing it in `related`, which would fail G4 here. Once both are on one branch, `consistency-models` belongs in the `related` lists of those two guides, and `mvcc-snapshot-isolation`'s `guides` becomes `[consistency-models, mvcc-and-snapshot-isolation]` (on `release/v0.48-integration` it is `[consistency-models]`). The consistency-models guide defines snapshot isolation, first-committer-wins and write skew from Berenson and others in one expert note; `mvcc-and-snapshot-isolation` goes deeper from the same source and does not repeat its treatment of linearizability, CAP or causal consistency.

## Practice links

The guides and the path link eight problems, all on `main`. Each problem's `meta.yaml` lists its guides after `related:`:

| Problem | `guides:` | Path step |
|---------|-----------|-----------|
| 0367 `btree-index` | `[b-tree-indexes]` | after `b-tree-indexes` |
| 0190 `transactional-kv-store` | `[write-ahead-logging]` | after `write-ahead-logging` |
| 0275 `supplier-records-locking-typescript` | `[transactions-and-isolation]` | after `transactions-and-isolation` |
| 0282 `inventory-reservations-typescript` | `[transactions-and-isolation]` | after `transactions-and-isolation` |
| 0283 `postgres-job-queue-typescript` | `[pipeline-orchestration, transactions-and-isolation]` | after `transactions-and-isolation` |
| 0368 `mvcc-snapshot-isolation` | `[mvcc-and-snapshot-isolation]` | after `mvcc-and-snapshot-isolation` |
| 0382 `query-planner` | `[query-planning-and-joins]` | after `query-planning-and-joins` |
| 0319 `triple-store` | `[query-planning-and-joins]` | after `query-planning-and-joins` |

`pages-and-records` and `lsm-trees-and-compaction` link no problem: no problem in the catalog builds a page layout or an LSM tree. Their practice sections point to the later guides and to the guide on table formats.

## Where a guide comes close to a linked problem

Each guide was read against the statement, hints, solution explanation and follow-ups of every problem it links. Each teaches its idea with examples of its own, but some ideas are the problem's subject. These are the places the review should weigh against the rule that a guide never gives away a linked problem's solution:

| Problem | Guide | Overlap the guide states | Kept back |
|---------|-------|--------------------------|-----------|
| `btree-index` | b-tree-indexes | Bayer and McCreight's rules, splits that move the middle key up, catenation and redistribution in their words; the B+ tree with copied separators, equal keys going right, separators left behind by deletes, and linked leaves for range scans, all of which the statement also explains; composite keys compared column by column and PostgreSQL's leading-column rule; PostgreSQL's default build fill factor of 90 | Any tree code; the problem's split sizes, its repair order (left borrow, right borrow, left merge, right merge) and the inner rotation; how the scan counts visits; the bulk load with its short last group; where a prefix scan starts (the explanation's negative-field pitfall); follow-ups 1 (splits that favour increasing keys: PostgreSQL's behaviour at the right edge is not mentioned), 2 (what evening out siblings changes: the guide names Bayer and McCreight's redistribution, not its effect), 3 (short separators: prefix B-trees are not mentioned), 4 (backward scans: PostgreSQL's doubly linked levels are not mentioned) and 5 (locking nodes: not mentioned) |
| `transactional-kv-store` | write-ahead-logging | Log records hold the value before and after a change, and undo walks a transaction's changes backwards restoring the values before, as the crash example does; hint 2 states the same for an in-memory store; SQLite's rollback journal keeps the original pages | Nested transactions and handing remembered values to the parent while keeping the older one (hint 3); per-value counts (hint 1); snapshots numbered by commit; follow-ups 1 (two clients) and 2 (constant-time commit) |
| `supplier-records-locking-typescript` | transactions-and-isolation | The lost update as Berenson and others define it, and that a write based on a stale read loses another's change, which the statement also describes; a single `UPDATE` whose `WHERE` clause carries the condition, in general; row locks with `FOR UPDATE` as one way to make read-then-write safe; retrying failed transactions | Versions per record and the 409 contract; the merge rules; truthful answers to retries; the counter's add and swap; hint 5's value that returns to 5; deletes and comebacks; follow-up 1 (what the `PUT` becomes and what the row count tells: the guide mentions neither versions nor row counts); follow-up 2 (when a lock beats retrying under a nightly job: the guide weighs no such choice); follow-ups 3 and 4 |
| `inventory-reservations-typescript` | transactions-and-isolation | The tools level 2 itself lists: `SELECT ... FOR UPDATE`, a conditional `UPDATE` in one statement, unique keys and check constraints; deadlocks from opposite lock orders and PostgreSQL's advice of a consistent order, which level 3 states; that serializable transactions fail with 40001 and must be retried, PostgreSQL's general rule, which touches follow-up 1 | Reading availability after taking the lock (hint 3); availability as stock minus active holds with their expiry, and sorting by SKU (hint 5); the reservation keyed by order (hint 1); the level 4 migration; what serializable would change for this service (follow-up 1 applied); follow-ups 2 to 6 |
| `postgres-job-queue-typescript` | transactions-and-isolation | `SKIP LOCKED` and PostgreSQL's note that it suits queue-like tables, which the statement names and explains; row locks | The claim as one statement (hint 3); one "not claimable before" time (hint 2); completes fenced by the attempt (hint 4); one connection per transaction (hint 5); backoff, dead letters, priorities, fair shares and the migration; every follow-up |
| `mvcc-snapshot-isolation` | mvcc-and-snapshot-isolation | Snapshot isolation and first-committer-wins, and write skew, which the statement explains (the guide uses Fekete, O'Neil and O'Neil's accounts, not its replicas); an example that implements both by copying the committed state at each start and comparing write sets, the semantics of levels 1 and 2 by another technique; rw-antidependencies, Theorem 2.1, the dangerous structure, and SSI aborting a transaction with an edge in and an edge out, with false positives, all of which the statement states; PostgreSQL's first-updater behaviour, the premise of follow-up 2; old versions kept while any transaction may see them, `VACUUM`, and long transactions holding back cleanup, the idea of level 4; that a read-only transaction can see an anomaly (the hidden case `h9` and the premise of follow-up 4) | Version lists searched by stamp (hints 1 to 3) and buffered writes in the store; the problem's statuses and its clock; the level 3 rules: which transaction aborts when the pivot has already committed, at a read or at a write, edges of aborted transactions, and keeping the reads of committed transactions; how the read-only case is detected; the horizon and the vacuum report; follow-ups 1 (visibility from the list of running transactions: not described), 2 (what each rule costs), 3 (when reads may be dropped: Ports and Grittner's answer is not repeated), 4 (safe snapshots and deferrable transactions: not mentioned) and 5 (flags against edges: not mentioned) |
| `query-planner` | query-planning-and-joins | Selinger and others' selectivity factors, among them 1/3 for open-ended comparisons and 1/max for joins, which the statement uses; the product of factors and its independence assumption; left-deep plans and the rule against Cartesian products; dynamic programming over subsets explained in prose as the 1979 paper does, as the statement also does; nested loops and hash joins; PostgreSQL's default `random_page_cost` of 4.0, where the statement charges 4 reads per random read; an example that runs every left-deep order of its own three-table query on real rows and estimates its result with the 1979 rules | The parser and the printer; the problem's rounding, integer arithmetic, cost definition and tie rules; the dynamic programming itself (hints 4 and 5); level 4's cost model of access paths and join methods; follow-ups 1 (histograms and common values: not described), 2 (detecting correlation: not described), 3 (an index nested loop's cost and when it beats a hash join: PostgreSQL's remark on index scans in nested loops is not repeated), 4 (bushy plans: only left-deep ones are defined) and 5 (how many entries interesting orders add: the guide explains interesting orders, not the count) |
| `triple-store` | query-planning-and-joins | That the order of a join matters and that the most selective pattern should come first, which level 2 states; the B-tree guide's section on keys of several columns explains why an index on (a, b) serves conditions on a | The eight pattern shapes and their indexes (level 1); variable binding, paths, history and sources; follow-ups 1 (three sorted orders against six hash tables) and 4 (estimating a better order from bound variables) |

## Independent accuracy review

Pending: the owner runs the independent accuracy review of these seven guides, the path and this page.
