# Review: the facts of the data engineering guides

The eight guides of the path "Data engineering: from batch and streams to table formats and lineage" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about papers, open specifications, the documentation of open-source projects, a standard library module and an RFC. This page lists each one with where it was checked, so that the independent review starts from the sources.

"Quote" means the exact text was read at that source: on the web page or in the raw file fetched from the project's repository, or in the text extracted from the PDF with `pdftotext`. "Run" means an example of the guide, or a one-off program, printed it, on CPython 3.13.12. "Arithmetic" means the number was computed from the stated inputs. A fact that could not be checked was left out of the guides; the last sections list those, the citation choices, and where a guide comes close to a linked problem.

| Guide | Slug |
|-------|------|
| Batch and streaming | `batch-and-streaming` |
| Event time, windows and watermarks | `event-time-and-windows` |
| Change data capture and log-based replication | `change-data-capture` |
| Orchestrating batch pipelines | `pipeline-orchestration` |
| Dimensional modeling and slowly changing dimensions | `dimensional-modeling` |
| Data quality checks and data contracts | `data-quality-and-contracts` |
| Table formats: snapshots, time travel and optimistic commits | `table-formats-and-snapshots` |
| Data lineage | `data-lineage` |

## Stream processing papers

Akidau and others, *The Dataflow Model: A Practical Approach to Balancing Correctness, Latency, and Cost in Massive-Scale, Unbounded, Out-of-Order Data Processing*, Proceedings of the VLDB Endowment 8(12), 2015, pages 1792 to 1803, read in full from [the VLDB PDF](https://www.vldb.org/pvldb/vol8/p1792-Akidau.pdf). Akidau and others, *MillWheel: Fault-Tolerant Stream Processing at Internet Scale*, Proceedings of the VLDB Endowment 6(11), 2013, read from [the VLDB PDF](https://www.vldb.org/pvldb/vol6/p1033-akidau.pdf). Used in `batch-and-streaming`, `event-time-and-windows` and `pipeline-orchestration`.

| # | Claim | Source |
|---|-------|--------|
| D1 | The paper prefers bounded and unbounded for data, and reserves batch and streaming for execution engines; unbounded datasets have been processed by repeated runs of batch systems since their conception, and streaming systems can process bounded data | Quote: Dataflow, §1.1 |
| D2 | Event time is when the event occurred, a record of the clock of the system that generated it; processing time is when it is observed during processing; event time essentially never changes, processing time changes constantly; the skew between them varies, from communication delays, scheduling, processing time and more | Quote: Dataflow, §1.3 |
| D3 | On unbounded data, windowing is required for most forms of grouping (aggregation, outer joins) and unnecessary for filtering, mapping and inner joins; on bounded data it is optional, but useful, for example to backfill updates to part of a previous result | Quote: Dataflow, §1.2 |
| D4 | Fixed windows, sometimes called tumbling windows, have a static size and are generally aligned; they are sometimes unaligned by shifting each key's windows by a random phase, to spread window completion load | Quote: Dataflow, §1.2 |
| D5 | Sliding windows have a size and a slide period, such as hourly windows starting every minute; a period smaller than the size makes them overlap; fixed windows are sliding windows whose size equals their period | Quote: Dataflow, §1.2 |
| D6 | Sessions capture a period of activity per key, defined by a timeout gap, and are unaligned; each element gets a window extending the gap beyond its timestamp, and overlapping windows merge; with a 30-minute gap, elements at 13:02 and 13:20 merge into `[13:02, 13:50)`, and one at 13:57 is `[13:57, 14:27)` | Quote: Dataflow, §2.2.2 and Figure 4 |
| D7 | Sessions are the main contribution of the paper's windowing model over existing models | Quote: Dataflow, §3.3.2 |
| D8 | The watermark considered is MillWheel's, a lower bound, often heuristic, on the event times processed; for most real-world data a completely correct watermark is impossible, as with a mobile device taken offline; for structured sources that expose metadata about unobserved data, such as log files, heuristics are remarkably accurate | Quote: Dataflow, §1.3 and footnote 6 |
| D9 | Watermarks are sometimes too fast, with late data behind them, and sometimes too slow, held back for the whole pipeline by a single slow datum | Quote: Dataflow, §2.3 |
| D10 | Four dimensions: what results are computed, where in event time, when in processing time they are materialized, how earlier results relate to later refinements; triggers emit results as panes, at completion estimates (watermarks, including percentile watermarks), at points in processing time, on data arriving (counts and more), and in combinations | Quote: Dataflow, §1 and §2.3 |
| D11 | The discarding, accumulating, and accumulating and retracting modes, with the consumers each fits; a retraction of the previous value is emitted first, then the new value; retractions are needed when a window's successive results can land on different keys in a later grouping | Quote: Dataflow, §2.3 |
| D12 | Percentile watermarks suit cases where processing a minimum percentage of the input quickly matters more than processing every last piece | Quote: Dataflow, §2.3 |
| D13 | The paper names the Lambda Architecture, citing *How to beat the CAP theorem*; Lambda gives the streaming pipeline's best low-latency estimate with the promise of correctness once the batch pipeline runs; batch output is correct only if the input is complete when the batch job runs | Quote: Dataflow, §1, §2.3 and footnote 10; reference [25] |
| D14 | A team ran a weakly consistent streaming pipeline with a nightly batch job to produce the truth; its users stopped trusting the weak results, and the system was rebuilt around strong consistency | Quote: Dataflow, §3.3.1 |
| D15 | An initial motivation was a single implementation that runs in streaming and batch mode without modification; the choice among batch, micro-batch and streaming engines can then rest on latency and resource cost | Quote: Dataflow, §1 and §3.3.1 |
| M1 | A computation's low watermark is the minimum of its oldest unfinished work and the low watermarks of the computations that output to it; it bounds the timestamps of future records | Quote: MillWheel, §4.5 |
| M2 | Injectors seed low watermarks; pending work in external systems is often an estimate, so computations should expect a small rate of late records; one pipeline dropped them while tracking how many (around 0.001%), others corrected their aggregates; low watermarks stay monotonic even with late data | Quote: MillWheel, §4.5 |
| M3 | Deliveries are retried until acknowledged, an at-least-once requirement that is a prerequisite for exactly-once; records get unique ids when produced, stored in the same atomic write as the state change, and a retried duplicate is discarded; the guarantee does not extend to external systems | Quote: MillWheel, §3 and §6.1.1 |

## Lambda and Kappa

Both are posts, cited by title; the guides do not name their authors.

| # | Claim | Source |
|---|-------|--------|
| L1 | A batch workflow precomputes the query for everything but the last few hours; a realtime system runs in parallel for those hours with incremental algorithms; queries merge the batch view and the realtime view; everything the realtime layer computes is eventually overridden by the batch layer. The post does not use the word "Lambda" | Quote: [*How to beat the CAP theorem*, 13 October 2011](http://nathanmarz.com/blog/how-to-beat-the-cap-theorem.html) |
| L2 | The problem with Lambda is maintaining code that must produce the same result in two complex distributed systems; the alternative retains the full log, starts a second instance of the stream job from the beginning of the retained data writing to a new output table, switches the application to it once caught up, then stops the old job and deletes the old table; "Maybe we could call this the Kappa Architecture" | Quote: [*Questioning the Lambda Architecture*, 2 July 2014](https://www.oreilly.com/radar/questioning-the-lambda-architecture/) |

## Change data capture

PostgreSQL's documentation, version 18 (18.6 at the time of reading); Debezium's documentation, version 3.7; the DBLog paper on arXiv. Used in `change-data-capture`.

| # | Claim | Source |
|---|-------|--------|
| W1 | Write-ahead logging is a standard method for ensuring data integrity; changes to data files must be written only after the WAL records describing them are flushed to permanent storage; after a crash, changes not yet in the data pages are redone from the WAL | Quote: [*Write-Ahead Logging*](https://www.postgresql.org/docs/current/wal-intro.html) |
| W2 | WAL records are appended as each new record is written; the LSN is a byte offset into the WAL, increasing monotonically with each new record | Quote: [*WAL Internals*](https://www.postgresql.org/docs/current/wal-internals.html) |
| W3 | Logical decoding extracts all persistent changes to a database's tables into a format that can be interpreted without knowledge of the database's internal state | Quote: [*Logical Decoding Concepts*](https://www.postgresql.org/docs/current/logicaldecoding-explanation.html) |
| W4 | A replication slot represents a stream of changes replayed to a client in the order they were made; slots persist across crashes and prevent removal of required WAL even with no connection, consuming storage; an unneeded slot should be dropped | Quote: *Logical Decoding Concepts* |
| W5 | A logical slot emits each change once in normal operation; its position is persisted only at checkpoints, so after a crash it may return to an earlier LSN and send recent changes again; clients are responsible for handling the same message more than once | Quote: *Logical Decoding Concepts* |
| C1 | Log-based CDC, unlike polling or dual writes, captures all changes, with very low delay and without the CPU cost of frequent polling, needs no data model change such as a "Last Updated" column, can capture deletes, and can capture the old record state and metadata such as the transaction id, depending on the database | Quote: [Debezium, *Features*](https://debezium.io/documentation/reference/stable/features.html) |
| C2 | An initial snapshot can be taken when a connector starts and not all logs still exist, typically because the database discarded logs no longer needed for transaction recovery or replication | Quote: Debezium, *Features* |
| C3 | Change event values have optional `before` and `after` fields and a mandatory `op`: `c` create, `u` update, `d` delete, `r` read (snapshots only), `t` truncate, `m` message; a delete's `after` is null | Quote: [Debezium, PostgreSQL connector](https://debezium.io/documentation/reference/stable/connectors/postgresql.html) |
| C4 | After a delete event a tombstone follows, with the same key and a null value, so that log compaction can remove all earlier messages with that key | Quote: Debezium, PostgreSQL connector |
| C5 | When things go wrong, consumers can see events at least once; after a crash a consumer restarts from its last recorded offsets and sees some events again | Quote: [Debezium FAQ](https://debezium.io/documentation/faq/) |
| C6 | Polling may miss intermediary changes between two runs of the poll loop, cannot identify deleted records, and needs a column such as `LAST_UPDATE_TIMESTAMP` | Quote: [*Five Advantages of Log-Based Change Data Capture*, 19 July 2018](https://debezium.io/blog/2018/07/19/advantages-of-log-based-change-data-capture/) |
| C7 | Dual writes and distributed transactions have limitations; transaction logs typically do not contain the full history; DBLog interleaves log events with rows selected directly from tables, in chunks that can pause and resume, without locks; each chunk is framed by a low and a high watermark written to a watermark table, which appear in the log as change events | Quote: [Andreakis and Papapanagiotou, *DBLog: A Watermark Based Change-Data-Capture Framework*, arXiv 2010.12597, 23 October 2020](https://arxiv.org/abs/2010.12597), abstract and §3.2 |

## Python and HTTP

| # | Claim | Source |
|---|-------|--------|
| Y1 | `graphlib` is new in Python 3.9, with `TopologicalSorter` | Quote: [What's New in Python 3.9](https://docs.python.org/3/whatsnew/3.9.html) |
| Y2 | The graph maps each node to an iterable of its predecessors; `get_ready` returns every node whose predecessors are done, `done` marks nodes processed, `is_active` says whether progress is possible; `prepare` raises `CycleError`, a subclass of `ValueError` whose second argument lists one cycle, each node an immediate predecessor of the next, first and last the same, the choice among several cycles undefined; the order among nodes ready together may depend on insertion order; `static_order` | Quote: [`graphlib`](https://docs.python.org/3/library/graphlib.html); run: `run_order.py` |
| Y3 | A method is idempotent if the intended effect of multiple identical requests is the same as for one; such requests can be repeated automatically after a communication failure; a client should not automatically retry a non-idempotent request unless it knows the request is idempotent anyway or that the original was never applied | Quote: [RFC 9110, §9.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#name-idempotent-methods) (from the RFC's text edition) |

## Dimensional modeling

The Kimball Group's *Dimensional Modeling Techniques* pages, each read in full; and the SQL:2011 temporal features as described by Kulkarni and Michels. Used in `dimensional-modeling`.

| # | Claim | Source |
|---|-------|--------|
| K1 | Declaring the grain is the pivotal step; the grain says exactly what a fact row represents; different grains must not be mixed in one fact table | Quote: [*Grain*](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/grain/) |
| K2 | The four steps: select the business process, declare the grain, identify the dimensions, identify the facts | Quote: [*Four-Step Dimensional Design Process*](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/four-4-step-design-process/) |
| K3 | Dimensions provide the "who, what, where, when, why, and how" context of a business process event; their descriptive attributes are used for filtering and grouping | Quote: [*Dimensions for Descriptive Context*](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/dimensions-for-context/) |
| K4 | Facts are measurements, almost always numeric; a fact row corresponds one to one to a measurement event, so a fact table models a physical observable event, not the demands of a report | Quote: [*Facts for Measurements*](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/facts-for-measurement/) |
| K5 | Star schemas are fact tables linked to dimension tables by primary and foreign keys | Quote: [*Star Schemas and OLAP Cubes*](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/star-schema-olap-cube/) |
| K6 | The primary key cannot be the natural key, which has several rows once changes are tracked; surrogate keys are simple integers assigned in sequence starting with 1; the date dimension is exempt | Quote: [*Dimension Surrogate Keys*](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/dimension-surrogate-key/) |
| K7 | A durable key never changes while surrogate keys of versions do; an employee number changed on rehiring is the example | Quote: [*Natural, Durable, and Supernatural Keys*](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/natural-durable-supernatural-key/) |
| K8 | Type 0 retains the original value; type 1 overwrites and destroys history; type 2 adds a row with a new surrogate key, used by facts from the change until the next one, with at least an effective date, an expiration date and a current row indicator; type 3 adds an attribute that keeps the old value | Quote: the [type 0](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/type-0/), [type 1](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/type-1/), [type 2](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/type-2/) and [type 3](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/type-3/) pages |
| K9 | Type 6 embeds the current type 1 value beside the type 2 value, overwritten on every row of the durable key; type 7 puts both the durable key and the surrogate key in the fact table, for an as-is view and an as-was view | Quote: the [type 6](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/type-6/) and [type 7](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/type-7/) pages |
| K10 | Conformed dimensions share column names and domain contents, so results of separate fact tables align in a drill-across report | Quote: [*Conformed Dimensions*](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/conformed-dimension/) |
| K11 | For a late-arriving fact, search the dimension for the keys effective when the event occurred | Quote: [*Late Arriving Facts*](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/late-arriving-fact/) |
| K12 | A retroactive type 2 change inserts a new dimension row and the associated facts are restated | Quote: [*Late Arriving Dimensions*](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/late-arriving-dimension/) |
| S1 | SQL:2011 adopted a closed-open period model; valid time is when a row reflects reality, transaction time when it is recorded; application-time period tables support valid time and system-versioned tables transaction time; an update `FOR PORTION OF` a period splits an overlapping row into two or three contiguous rows, updating the part inside the period | Quote: [Kulkarni and Michels, *Temporal features in SQL:2011*, SIGMOD Record 41(3), September 2012](https://sigmodrecord.org/publications/sigmodRecord/1209/pdfs/07.industry.kulkarni.pdf), §2 and §2.2 |

## Data quality and contracts

The Open Data Contract Standard, read from its repository's `README.md` and `docs/` on the main branch; the PSI paper, version 4 on arXiv (29 December 2025); Apache Iceberg's documentation, version 1.12.0. Used in `data-quality-and-contracts`, and the SLA properties in `pipeline-orchestration`.

| # | Claim | Source |
|---|-------|--------|
| Q1 | ODCS describes the structure of a data contract, which defines the agreement between a data producer and consumers; its current version is v3.2.0, under the Apache 2.0 license; the citation names Bitol and the LF AI & Data Foundation; contracts are YAML | Quote: [ODCS `README.md`](https://github.com/bitol-io/open-data-contract-standard), and the [reader-friendly site](https://bitol-io.github.io/open-data-contract-standard/latest/) |
| Q2 | The sections: fundamentals, schema, references, data quality, support and communication channels, pricing, team, roles, service-level agreement, infrastructures and servers, authoritative definitions, tags, custom and other properties | Quote: ODCS `README.md` |
| Q3 | Quality rules can be text, library metrics (`nullValues`, `missingValues`, `invalidValues`, `duplicateValues`, `rowCount` among them), SQL, or custom rules for a specific tool; operators include `mustBe`, `mustNotBe`, `mustBeGreaterThan`, `mustBeLessThan`, `mustBeBetween`; rules have `severity` and `businessImpact`; the dimensions are accuracy, completeness, conformity, consistency, coverage, timeliness and uniqueness | Quote: [ODCS `docs/data-quality.md`](https://github.com/bitol-io/open-data-contract-standard/blob/main/docs/data-quality.md) |
| Q4 | SLA properties include `latency`, `retention`, `frequency` and `timeOfAvailability`; a `driver` is one of regulatory, analytics or operational | Quote: [ODCS `docs/service-level-agreement.md`](https://github.com/bitol-io/open-data-contract-standard/blob/main/docs/service-level-agreement.md) |
| Q5 | The earliest reference to the PSI is Lewis (1994), who coined the name; equation (1) defines it as the sum over bins of `(p̂ - p0)(log p̂ - log p0)`, counting only bins with a non-zero current share, a consistent estimator of the symmetric Kullback-Leibler divergence; in Lewis's example below 0.10 needs no action, 0.10 to 0.25 calls for investigation, above 0.25 signals a material change; fixed thresholds too often call for rebuilding on small samples and miss shifts on large ones; the proposed statistic, based on the Pearson chi-square, has critical values set by sample size and number of categories | Quote: [Potgieter, Van Zyl, Schutte and Lombard, *The Population Resemblance Statistic: A Chi-Square Measure of Fit for Banking*, arXiv 2307.11878v4](https://arxiv.org/abs/2307.11878), abstract, §1 and §2.2 |
| Q6 | With write-audit-publish, writes go to an audit branch independent of the main history, a validation workflow checks it (for example for data quality), and the main branch is fast-forwarded to it | Quote: [Apache Iceberg, *Branching and Tagging*](https://iceberg.apache.org/docs/latest/branching/) |

## Table formats

The Apache Iceberg table specification as served at [iceberg.apache.org/spec](https://iceberg.apache.org/spec/); the Delta Lake transaction protocol, `PROTOCOL.md` on the main branch of its repository; Apache Hudi's documentation, version 1.2.1; Kung and Robinson's paper. Used in `table-formats-and-snapshots`, and in `batch-and-streaming` and `pipeline-orchestration` where noted.

| # | Claim | Source |
|---|-------|--------|
| I1 | Goals: reads isolated from concurrent writes, always using a committed snapshot; writes that add and remove files in a single operation, never partially visible; readers acquire no locks; O(1) remote calls to plan a scan, not O(n) in the partitions or files | Quote: Iceberg spec, *Goals* |
| I2 | The format tracks individual data files, not directories; all changes create a new metadata file that replaces the old one with an atomic swap; a snapshot is the complete set of data files at some time; manifests hold a row per data file with its partition data and metrics, and are reused across snapshots; in versions 1 to 3 a manifest list stores a snapshot's manifests; version 4 replaces it with a root manifest | Quote: Iceberg spec, *Overview* |
| I3 | Writers create metadata optimistically and commit by swapping the metadata pointer from the base version to the new one; if the base is no longer current, they must retry on the new current version; what a writer validates determines the isolation level | Quote: Iceberg spec, *Optimistic Concurrency* |
| I4 | Only one of two concurrent commits on the same version succeeds; appends can always be applied; replace operations (compaction is an example) and deletes of specific files must verify that the files they delete are still in the table; deletes by expression can always be applied; schema changes must verify the schema did not change | Quote: Iceberg spec, *Commit Conflict Resolution and Retry* |
| I5 | Metastore tables commit with a check-and-put of a pointer; the file-system scheme, by atomic rename, is deprecated and unsafe in object stores and local file systems | Quote: Iceberg spec, *File System Tables*, *Metastore Tables* |
| I6 | Snapshot operations: `append` (only added data files), `replace` (files added and removed without changing table data, such as compaction), `overwrite`, `delete` | Quote: Iceberg spec, *Snapshots* |
| I7 | Expiry retains snapshots younger than `max-snapshot-age-ms` or among the first `min-snapshots-to-keep` of a branch | Quote: Iceberg spec, *Snapshot Retention Policy* |
| I8 | Point-in-time reads use the snapshot log to find the snapshot current at a timestamp | Quote: Iceberg spec, *Point in Time Reads (Time Travel)* |
| I9 | Data and metadata files are immutable once written, until deleted | Quote: Iceberg spec, *File System Operations* |
| I10 | Manifest entries have a status, among them existing, added and deleted | Quote: Iceberg spec, manifest entry fields |
| I11 | Versions 1, 2 and 3 are complete and adopted; version 4 is under active development and not formally adopted; version 2 added delete files that encode rows deleted in existing data files | Quote: Iceberg spec, *Format Versioning* |
| I12 | Branches and tags are named references to snapshots with independent lifecycles and their own retention | Quote: Iceberg, *Branching and Tagging* |
| T1 | The protocol's goals include incremental processing: readers can tail the log to see what data was added, allowing efficient streaming | Quote: Delta `PROTOCOL.md`, *Overview* (in `batch-and-streaming`) |
| T2 | Writers first optimistically write data files, then commit by adding a new log entry recording files to add and remove; readers see one consistent snapshot through the log; files no longer in the latest version are deleted lazily by vacuum after a retention period, 7 days by default | Quote: Delta `PROTOCOL.md`, *Overview* |
| T3 | A table has a single serial history of atomic versions named by contiguous, monotonically increasing integers; log entries are newline-delimited JSON files in `_delta_log`, named by version zero-padded to 20 digits, each an atomic set of actions applied to the previous version; a checkpoint holds the complete table state at its version | Quote: Delta `PROTOCOL.md`, *Delta Table Specification*, *Delta Log Entries* |
| T4 | Writers must never overwrite an existing log entry and should use atomic primitives of the storage | Quote: Delta `PROTOCOL.md`, *Creation of New Log Entries* |
| T5 | Transaction identifiers, `appId` and `version` pairs, are recorded atomically with the table changes so that external systems can make their writes idempotent | Quote: Delta `PROTOCOL.md`, *Transaction Identifiers* (in `pipeline-orchestration`) |
| H1 | The timeline is a log of all actions on the table at instants and the source of truth for its state; actions include commits, cleans, compactions, rollbacks (removing partial files of an unsuccessful write) and savepoints (file slices the cleaner keeps, for restore or time travel); states are requested, inflight and completed | Quote: [Apache Hudi, *Timeline*](https://hudi.apache.org/docs/timeline) |
| R1 | Optimistic methods: reads unrestricted; a transaction has a read phase writing to local copies, a validation phase, and a write phase that makes the copies global; a transaction that fails validation is backed up and starts again | Quote: [Kung and Robinson, *On Optimistic Methods for Concurrency Control*, ACM TODS 6(2), June 1981, pages 213 to 226](https://www.eecs.harvard.edu/~htk/publication/1981-tods-kung-robinson.pdf), §1 |

## Lineage

OpenLineage's documentation, version 1.55.0, and its JSON schema `spec/2-0-2/OpenLineage.json`; the W3C PROV-O Recommendation. Used in `data-lineage`, and the facets also in `pipeline-orchestration` and `data-quality-and-contracts`.

| # | Claim | Source |
|---|-------|--------|
| O1 | OpenLineage is an open framework for data lineage collection and analysis, with an extensible specification at its core; an open standard for lineage metadata collection; defined using OpenAPI, extended through custom facets; an LF AI & Data Foundation graduate project | Quote: [OpenLineage, *About*](https://openlineage.io/docs/) |
| O2 | Jobs, runs and datasets: a job is a process that consumes or produces datasets, identified by a name unique within a namespace; a run is one occurrence of a job, with a client-generated id, UUIDv7 recommended; a dataset is a discrete collection of data, named uniquely within a namespace from its physical location; the model includes jobs because it cares how datasets come into being; a lineage graph is built by weaving together observations of many jobs across platforms | Quote: [OpenLineage, *Object Model*](https://openlineage.io/docs/spec/object-model) |
| O3 | Run events are emitted at runtime; job events and dataset events carry design-time metadata and are not associated with a run | Quote: *Object Model* |
| O4 | Run states `START`, `RUNNING`, `COMPLETE`, `ABORT`, `FAIL`, `OTHER`, `COMPLETE`, `ABORT` and `FAIL` being terminal; `BATCH` jobs are finite, `STREAMING` and `SERVICE` jobs continuous, emitting periodically | Quote: [OpenLineage, *The Run Cycle*](https://openlineage.io/docs/spec/run-cycle) |
| O5 | Facets: job source code location; run `nominalTime` (the scheduled time, different from the actual run time) and parent; dataset schema and version (a table format's snapshot id is the example); input data quality metrics (row count, null count, distinct count and more) and assertions; output statistics | Quote: *Object Model* |
| O6 | A run event requires `eventTime`, `producer`, `schemaURL`, `run` (with `runId`) and `job` (with `namespace` and `name`) | Quote: [`OpenLineage.json`, 2-0-2](https://openlineage.io/spec/2-0-2/OpenLineage.json), `BaseEvent`, `RunEvent`, `Run`, `Job` |
| O7 | Column lineage types: `DIRECT` (derived from the input) with subtypes `IDENTITY`, `TRANSFORMATION`, `AGGREGATION`; `INDIRECT` (affects the output without being derived) with `JOIN`, `GROUP_BY`, `FILTER`, `SORT`, `WINDOW`, `CONDITIONAL`; `masking` marks an obfuscated input, hash and count being the examples | Quote: [OpenLineage, *Column Level Lineage Dataset Facet*](https://openlineage.io/docs/spec/facets/dataset-facets/column_lineage_facet) |
| P1 | PROV-O is a W3C Recommendation of 30 April 2013; an entity is a thing with some fixed aspects, an activity occurs over time and acts on entities, an agent bears responsibility for an activity or an entity; a derivation is a transformation of an entity into another, an update resulting in a new one, or the construction of a new entity from a pre-existing one | Quote: [W3C, *PROV-O*](https://www.w3.org/TR/prov-o/) |

## The examples and the arithmetic

| # | Claim | Source |
|---|-------|--------|
| E1 | Monday's batch total is 2000 at hour 24 and 2300 when run again at hour 50; the stream reports 2300 for Monday at hour 27 | Run: `batch_vs_stream.py` |
| E2 | By event time the windows' maxima are 35 and 25; by processing time 21 and 35 | Run: `two_clocks.py` |
| E3 | With a bound of 0, `[0, 10)` is reported after minute 11 with 22, and 31 and 40 are dropped; with a bound of 5, after minute 21 with 31, and only 40 is dropped | Run: `watermarks.py` |
| E4 | The second poll returns only `1 team`; the log holds five changes, the delete included | Run: `polling_vs_log.py` |
| E5 | The replica skips 10 to 30 and the redelivered 40 and 50, ending at `{'1': 'team'}`; without positions, the redelivered insert fails | Run: `replica_apply.py` |
| E6 | Four rounds; the cycle `daily_revenue -> weekly_revenue -> load_rates -> daily_revenue`; the same output under four hash seeds | Run: `run_order.py`, also with `PYTHONHASHSEED` 0 to 3 |
| E7 | Appending twice gives 30 for day 3, overwriting 15; the clock-based task reads 0 for day 2 when rerun on day 9 | Run: `idempotent_writes.py` |
| E8 | One rewritten daily partition makes stale 1 daily, 1 churn and 7 weekly partitions: nine | Arithmetic: a 7-day window |
| E9 | As it was: Home office 275, Lighting 75; as it is: Home office 350; the late sale finds key 2 | Run: `star.py` |
| E10 | A million customers changing twice a year add two million rows a year | Arithmetic |
| E11 | Three breaking changes and two compatible ones | Run: `schema_changes.py` |
| E12 | The first batch is published as version 2; the second is blocked on three checks | Run: `write_audit_publish.py` |
| E13 | PSI terms 0.1022, 0 and 0.1386, sum 0.2408 | Run: a one-off program, `sum((a - e) * log(a / e))` over the shares |
| E14 | The append commits version 1, the compaction retries and commits version 2, the delete conflicts on `b.data` | Run: `table_log.py` |
| E15 | An hourly rewrite kept for 7 days leaves up to 168 copies | Arithmetic: 24 × 7 |
| E16 | Four datasets upstream of the finance report and four downstream of the rates; three column edges | Run: `lineage.py` |

## Citations and names

The guides endorse no product. Where they name software, it is an open specification, an open standard or the documentation of an open-source project, cited for a fact it documents:

| Name | Why it is named |
|------|-----------------|
| PostgreSQL | Its documentation is the source for write-ahead logging, the LSN, logical decoding and replication slots |
| Debezium | Its documentation is the source for change event fields, tombstones, snapshots and redelivery |
| Apache Iceberg, Delta Lake, Apache Hudi | Their table specification, transaction protocol and documentation are the sources of the table format guide |
| OpenLineage, Open Data Contract Standard, PROV-O | Open standards, cited for their models |
| Python's `graphlib` | The language of the examples, with its official documentation |

The two posts on Lambda and Kappa and the 2018 post on log-based capture are cited by title and date; the guides do not name their authors, although the 2011 post's address carries its author's name. Papers are cited by their authors, as the other guides do. No guide names a company; the affiliations printed in the Dataflow, MillWheel and DBLog papers are not repeated. Where the Dataflow paper names the systems it compares, the guides leave them out.

## Not verified, so left out or reworded

- A post on functional data engineering, often cited for idempotent partition overwrites, could not be read: WebFetch got HTTP 403. The orchestration guide states the idea in its own words, grounded in RFC 9110's definition and its own example, and cites nothing for it.
- The DOIs of the two VLDB papers resolve to the ACM Digital Library, which refused the request with HTTP 403; the guides cite the VLDB copies, which were read.
- The name "hopping" for sliding windows is not in the Dataflow paper; it is kept because the practice problem `stream-windows` uses it.
- The Iceberg manifest entry status also lists `REPLACED` and `MODIFIED`; the spec page does not say in which format version they appear, so the guide names only existing, added and deleted.
- Hudi: a sentence that only completed actions count was not found in the documentation and was removed.
- Debezium's `source` block: the fields it holds were not read, so the guide's table says only that it carries metadata such as the table and, on some databases, the transaction (C1).
- PostgreSQL: an early draft said the WAL is "in commit order"; the documentation says records are appended as they are written, and slots replay changes in the order they were made, so the guide says that.
- The Kimball Group's pages on null attributes and null fact keys returned no technique text. The advice to keep a reserved "unknown" dimension row, in `dimensional-modeling`'s traps, is given as design advice, without a citation.
- The SQL:2011 standard itself is sold by ISO and was not read; its temporal features are cited from the SIGMOD Record article that describes them.

## Practice links to problems not yet merged

The guides and the path reference seven problems that live on two other branches, by the slugs of their folders: `stream-windows` (0332), `cdc-apply` (0333) and `pipeline-scheduler` (0334) on `feat/data-eng-streams-problems`; `scd-type2-dimension` (0335), `data-quality-gate` (0336), `snapshot-table` (0337) and `lineage-graph` (0338) on `feat/data-eng-tables-problems`. Each problem's statement and solution explanation were read before its guide was written. `cstudy verify --static` passed on a temporary merge of this branch with both, with these `guides:` lists added to the new problems' `meta.yaml`, after `related:`:

| Problem | `guides:` |
|---------|-----------|
| 0332 `stream-windows` | `[event-time-and-windows, batch-and-streaming]` |
| 0333 `cdc-apply` | `[change-data-capture]` |
| 0334 `pipeline-scheduler` | `[pipeline-orchestration]` |
| 0335 `scd-type2-dimension` | `[dimensional-modeling]` |
| 0336 `data-quality-gate` | `[data-quality-and-contracts]` |
| 0337 `snapshot-table` | `[table-formats-and-snapshots]` |
| 0338 `lineage-graph` | `[data-lineage]` |

## Where a guide comes close to a linked problem

Each guide teaches its idea with examples of its own, but some ideas are the problem's subject. These are the places the review should weigh against the rule that a guide never gives away a linked problem's solution:

| Guide | Close to | What the guide shows |
|-------|----------|----------------------|
| `event-time-and-windows` | `stream-windows` hints 1 and 5 | The tumbling window start as `minute - minute % SIZE`, and a single-key watermark loop with a maximum, dropping late readings; no hopping or session code, no grace period, retractions or the problem's API |
| `change-data-capture` | `cdc-apply` level 2 | One position for one ordered log, with the snapshot setting it; the closing paragraph says, as the statement does, that out-of-order channels need positions per key |
| `pipeline-orchestration` | `pipeline-scheduler` levels 1 and 4 | The run order comes from `graphlib`, not the problem's own sort; the backfill section explains staleness through windows and recorded inputs, as the statement defines it, without code |
| `dimensional-modeling` | `scd-type2-dimension` hint 4 | A point-in-time lookup by a linear scan, and the remark that a binary search over sorted versions takes O(log v); no loader |
| `data-quality-and-contracts` | `data-quality-gate` levels 2 and 3 | A fixed set of checks in a write-audit-publish example, and the PSI formula with one worked number; no rule engine, no zero-share replacement in code |
| `table-formats-and-snapshots` | `snapshot-table` level 3 | A log-based table where a retry checks that removed files are still live, Iceberg's rule; not the problem's partition conflict rule, expiry or compaction |
| `data-lineage` | `lineage-graph` level 2 | A dataset-level walk with a visited set; no distances, cycle groups, impact rules or labels |

## Independent accuracy review

Pending.
