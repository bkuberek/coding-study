# Spec: Content

What the catalog contains: tracks, the DSA pattern taxonomy with Phase targets, non-autograded item formats, and the copyright policy. How to write a problem is in [authoring](authoring.md).

## Tracks

DSA is roughly a third of a senior or staff loop, so the catalog covers the other rounds too.

| Track id | Name | Autograded | Location | Format | Target |
|----------|------|------------|----------|--------|--------|
| `dsa` | Data structures and algorithms | yes | `problems/` | `function` or `design` | 185 (Phases 1 and 3) |
| `practical` | Practical multi-level | yes, level by level | `problems/` | `progressive`, or `project` (a seeded folder in one language) | 6 (Phase 4); 2 project problems (Phase 8) |
| `lld` | Object-oriented and low-level design | API by ops tests; design by rubric | `problems/` | `design` plus `rubric.md` | 8 (Phase 4) |
| `concurrency` | Concurrency | yes, per language subset | `problems/` | `concurrent` | 6 (Phase 5) |
| `debugging` | Debugging | yes | `problems/` | `function` or `design` with `stub: buggy` | 8 (Phase 6) |
| `system-design` | System design | no (rubric) | `tracks/system-design/` | item | 10 (Phase 6) |
| `code-review` | Code review | no (rubric) | `tracks/code-review/` | item | 6 (Phase 6) |
| `behavioral` | Behavioral | no | `tracks/behavioral/README.md` | guidance only | 0 items |

Placement rule: autograded content lives in `problems/`, everything else in `tracks/`. Slugs are unique across both, because `progress.db` keys on the slug.

### Track notes

| Track | Notes |
|-------|-------|
| `practical` | Modeled on multi-level assessments: one class, 4 levels, each extending the API (example: in-memory database with set/get, then prefix scans, then TTL, then point-in-time history). Time is always an explicit `timestamp` argument. Candidates: in-memory database, banking ledger, file storage with quotas, task scheduler, key-value store with nested transactions, API gateway with rate limits |
| `lld` | Ops tests check the public behavior; `rubric.md` lists design criteria (responsibilities, extension points, patterns, testability) used for self-review after `cstudy done`, then the reference design; `cstudy solution` shows it before the code ([format](authoring.md#rubricmd)). Candidates: parking lot, rate limiter, event bus, LFU cache, logger with sinks, vending machine, elevator controller, library checkout |
| `concurrency` | Language differences are the content: Java platform and virtual threads and `java.util.concurrent`; Kotlin threads (coroutines as explanation sections, PRD Q5); Python `threading` under the GIL or `asyncio`; TypeScript async concurrency on the event loop (no `worker_threads`). Each problem lists its `languages` and a model per language; format and verdict rules in [problem-format](problem-format.md#concurrent-problems). Phase 5 problems: [below](#concurrency-problems) |
| `debugging` | Buggy code per language in `buggy/solution.<ext>`; the user fixes it until tests pass. Bugs may be language-specific (integer overflow, mutable default arguments, boxed equality), so `languages` may be a subset |
| `system-design` | Prompt, scale assumptions, rubric and a reference design. Items reference public articles and, optionally, sections of a distributed-systems study guide under your [study-guides root](#study-guides) (fundamentals, databases, messaging, storage, networking, observability, example designs). Candidates: URL shortener, distributed rate limiter, news feed, chat, distributed cache, notification system, web crawler, metrics ingestion, payment ledger, job scheduler |
| `code-review` | A diff or small set of files plus a prompt ("review this PR"); `reference.md` lists the issues a strong reviewer finds, by severity |
| `behavioral` | `tracks/behavioral/README.md` describes how to prepare from your own story bank (stories by theme, question-to-story map), which stays outside this repository |

### Concurrency problems

The 6 Phase 5 problems and their model per language (`-`: not listed in `languages`).

| Slug | Java | Kotlin | Python | TypeScript | Core skill | Broken references (bug classes) |
|------|------|--------|--------|------------|------------|---------------------------------|
| `bounded-blocking-queue` | threads | threads | threads | async | Condition waits, `while` re-checks, FIFO hand-off | no lock; `if` instead of `while` |
| `thread-safe-lru-cache` | threads | threads | threads | - | Making a compound structure atomic; lock granularity | no lock; lock on `get` only |
| `token-bucket-limiter` | threads | threads | threads | - | Atomic check-then-act with explicit timestamps; exact grant counts | unsynchronized refill and take |
| `read-write-lock` | threads | threads | threads | async | Shared versus exclusive access, writer preference (probe sections) | reader count without a lock; writer enters while readers hold |
| `bank-transfers` | threads | threads | threads | - | Deadlock avoidance by lock ordering; conservation invariants (`sum`) | no lock; locks taken in argument order (`STALLED`) |
| `concurrency-limiter` | threads | threads | async | async | Counting semaphore, at most `k` holders (`max_occupancy`), FIFO fairness | `if` instead of `while`; release without a waiter hand-off |

`worker-pool` and `async-promise-pool` from earlier drafts are folded into `concurrency-limiter`: the type DSL has no function values, so a pool that runs caller-supplied tasks cannot be expressed, and limiting concurrency is the part interviews probe. TypeScript is omitted where a correct and a broken solution behave identically on one event loop (synchronous methods are atomic there).

## Non-autograded item format

```text
tracks/system-design/<slug>/
  item.yaml       # validated by schemas/item.schema.json
  prompt.md       # the question, functional and non-functional requirements, scale
  rubric.md       # checklist of what a strong senior or staff answer covers
  reference.md    # reference answer, revealed by cstudy solution
  template.md     # copied to notes/<track>/<slug>.md by cstudy start
tracks/code-review/<slug>/
  item.yaml, prompt.md, rubric.md, reference.md, template.md
  change.diff     # or files/ with the code under review
```

Every directory directly inside `tracks/<track>/` is an item; its name is the slug. Other entries, such as a track's `README.md`, are ignored. Items have no numeric id.

```yaml
# yaml-language-server: $schema=../../../schemas/item.schema.json
slug: url-shortener
title: URL Shortener
track: system-design          # system-design or code-review; equals the parent directory
difficulty: medium
estimate_minutes: 45
status: draft                 # draft or ready
order: 1                      # optional curriculum order within the track (default 1000)
references:                   # optional
  study_guides:               # relative to the user's study-guides root, optionally with a #section anchor
    - "distributed-systems-study-guide.md#databases"
  links: [https://example.com/article]
related: [distributed-cache]  # optional slugs of problems or items
```

Each Markdown file starts with a `#` title and uses `##` sections; `cstudy verify` enforces the sections below in this order (extra sections are allowed, except in a code review reference) and rejects `TODO` in the prompt, rubric and reference ([checks](authoring.md#items)).

| File | Title | Required `##` sections |
|------|-------|------------------------|
| `prompt.md` | `# <title>` | system design: `Question`, `Functional requirements`, `Non-functional requirements`, `Scale`; code review: `Context`, `Task` |
| `rubric.md` | `# <title>: Rubric` | One or more areas (any titles), each with at least one `- [ ] <criterion>` line |
| `reference.md` | `# <title>: Reference` | system design: `Requirements`, `Estimates`, `API`, `Data model`, `High-level design`, `Deep dives`, `Trade-offs`; code review: only severities, most severe first, from `Blocker`, `Major`, `Minor`, `Nit`, each listing `- ` issues (at least one severity) |
| `template.md` | `# <title>: Notes` | At least one; usually the reference's sections with empty bodies or `<!-- guidance -->` comments, so self-review compares section by section |

A code review item carries exactly one of `change.diff` (a unified diff, not empty) or `files/` (the files under review); other items carry neither. `cstudy start` renders the prompt to `.statements/<slug>.md` and appends the change: the diff in a `diff` block, or each file of `files/` in a block named after its extension.

### Study guides

Study guides are your own notes, kept outside this repository and never copied into it. Set their directory as `root` in the `[study_guides]` table of the [user config](cli.md#configuration); `references.study_guides` paths are relative to it. The bundled items reference sections of `distributed-systems-study-guide.md`; any guide file you place at that path under your root is linked.

When the root is set, `cstudy start` and `cstudy show` list every referenced guide whose file exists under it, in a final `## Study guides` section of the statement, as a `file://` link that keeps the `#section` anchor; `cstudy start` also prints one `guide` line per link. Without a root, or for a missing file, nothing is shown and nothing fails.

## Pattern taxonomy

The seed is a personal study list, not part of this repository: 73 problems in 15 sections plus Binary Search (704) and Best Time to Buy and Sell Stock (121) from its study order, 75 in total. The taxonomy keeps its 15 patterns, splits Stack into Stack and Monotonic Stack/Deque, splits Graphs into Graphs, Topological Sort and Advanced Graphs, splits DP into 1D and 2D, and adds Union-Find, Prefix Sum, Math and Geometry, and Segment Tree/Fenwick.

The order below is the taxonomy order used for tie-breaks in `cstudy next`. Counts are by primary pattern.

| # | Pattern id | Seed | Phase target | Example additions (LeetCode reference numbers) |
|---|------------|------|--------------|-----------------------------------------------|
| 1 | `arrays-hashing` | 5 | 12 | Contains Duplicate (217), Valid Anagram (242), Encode and Decode Strings (271), Valid Sudoku (36) |
| 2 | `two-pointers` | 4 | 8 | Two Sum II (167), Move Zeroes (283), Sort Colors (75) |
| 3 | `sliding-window` | 5 | 8 | Minimum Size Subarray Sum (209), Fruit Into Baskets (904) |
| 4 | `stack` | 3 | 6 | Generate Parentheses (22), Basic Calculator II (227) |
| 5 | `monotonic-stack` | 2 | 6 | Car Fleet (853), Online Stock Span (901), Sum of Subarray Minimums (907) |
| 6 | `binary-search` | 6 | 10 | Time Based Key-Value Store (981), Split Array Largest Sum (410) |
| 7 | `linked-list` | 5 | 10 | Remove Nth Node From End (19), Copy List with Random Pointer (138), LRU Cache (146) |
| 8 | `trees` | 7 | 16 | Same Tree (100), Subtree of Another Tree (572), Kth Smallest in BST (230), Construct Tree from Traversals (105), Right Side View (199) |
| 9 | `tries` | 3 | 4 | Longest Word in Dictionary (720) |
| 10 | `heap` | 4 | 8 | Last Stone Weight (1046), Design Twitter (355), IPO (502) |
| 11 | `backtracking` | 5 | 10 | Subsets II (90), Combination Sum II (40), Palindrome Partitioning (131), Letter Combinations (17) |
| 12 | `graphs` | 3 | 12 | Max Area of Island (695), Rotting Oranges (994), Surrounded Regions (130), Word Ladder (127) |
| 13 | `topological-sort` | 2 | 4 | Course Schedule II (210), Parallel Courses (1136) |
| 14 | `advanced-graphs` | 1 | 8 | Min Cost to Connect Points (1584), Cheapest Flights Within K Stops (787), Swim in Rising Water (778), Reconstruct Itinerary (332) |
| 15 | `union-find` | 0 | 5 | Number of Connected Components (323), Redundant Connection (684), Accounts Merge (721) |
| 16 | `dp-1d` | 6 | 12 | Decode Ways (91), Word Break (139), Palindromic Substrings (647), House Robber II (213) |
| 17 | `dp-2d` | 2 | 12 | Edit Distance (72), Coin Change II (518), Interleaving String (97), Distinct Subsequences (115), Burst Balloons (312) |
| 18 | `greedy` | 5 | 8 | Jump Game II (45), Maximum Subarray (53), Valid Parenthesis String (678) |
| 19 | `intervals` | 4 | 6 | Meeting Rooms (252), Minimum Interval to Include Each Query (1851) |
| 20 | `prefix-sum` | 0 | 6 | Subarray Sum Equals K (560), Range Sum Query Immutable (303), Continuous Subarray Sum (523) |
| 21 | `math-geometry` | 0 | 6 | Rotate Image (48), Spiral Matrix (54), Pow(x, n) (50), Multiply Strings (43) |
| 22 | `bit-manipulation` | 3 | 5 | Reverse Bits (190), Missing Number (268), Sum of Two Integers (371) |
| 23 | `segment-tree-fenwick` (stretch) | 0 | 3 | Range Sum Query Mutable (307), Count of Smaller Numbers After Self (315) |
| | **Total** | **75** | **185** | |

Problems may list secondary patterns (for example Sliding Window Maximum: `sliding-window`, `monotonic-stack`); `cstudy list --pattern` matches any listed pattern.

### Content batches

Each batch is merged only when all its problems are `ready` and pass `cstudy verify --oracle` (and `--ladder` from Phase 2 on).

| Batch | Phase | Patterns | Problems |
|-------|-------|----------|----------|
| 1 | 1 | arrays-hashing, two-pointers, sliding-window, stack | 34 |
| 2 | 3 | binary-search, linked-list, monotonic-stack, intervals | 32 |
| 3 | 3 | trees, tries, heap | 28 |
| 4 | 3 | backtracking, graphs, topological-sort, union-find | 31 |
| 5 | 3 | dp-1d, dp-2d, greedy | 32 |
| 6 | 3 | advanced-graphs, prefix-sum, math-geometry, bit-manipulation, segment-tree-fenwick | 28 |

## Copyright policy

LeetCode statements, examples, test data, editorials and community solutions are copyrighted. Decision: [ADR 0004](../decisions/0004-original-problem-wording.md).

| Item | Rule |
|------|------|
| Statement | Written from scratch in own words and structure; never pasted or paraphrased sentence by sentence |
| Examples and tests | Own values; never copied from the original problem |
| Title | Common problem names (for example "Two Sum") are allowed |
| Signature and names | May match LeetCode for recognition (function names are not creative expression) |
| Reference | `meta.yaml` `references.leetcode` links to the original |
| Solutions and explanations | Own work; never copied from editorials or discussion posts |
| Personal study guides | Referenced by a path relative to the user's [study-guides root](#study-guides); their content is never copied into the repository |
