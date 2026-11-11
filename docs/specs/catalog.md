# Spec: Catalog

The binding manifest of every catalog item: 198 DSA problems and 133 non-DSA items (117 problems and 16 items in `tracks/`), each with its id, slug, title, patterns, difficulty, kind and [labels](content.md#labels), and for the planned rows their batch and owner stream.

| Track | Problems or items | Where |
|-------|-------------------|-------|
| `dsa` | 198 (185 planned, 13 added) | `problems/` |
| `practical` | 80 (6 planned, 16 added, 6 project problems added, 7 security and AI/LLM problems added, 8 backend TypeScript projects added, 20 service projects added, 11 memory and retrieval problems added, 1 search box problem added, 1 hash-chaining problem added, 3 trees, graphs and terrain problems added, 1 redaction project added) | `problems/` |
| `lld` | 8 | `problems/` |
| `concurrency` | 6 | `problems/` |
| `debugging` | 23 (8 planned, 8 in Go and Rust, 7 JavaScript traps in TypeScript) | `problems/` |
| `system-design` | 10 | `tracks/system-design/` |
| `code-review` | 6 | `tracks/code-review/` |
| **Total** | **331** (315 problems, 16 items) | | Targets, batches and the copyright policy come from [content](content.md); the file layout comes from [problem-format](problem-format.md); how to write an item is in [authoring](authoring.md).

Every row has three [labels](content.md#labels): `domains`, `job_roles` and `scope` ([S24](authoring.md#static), [ADR 0020](../decisions/0020-catalog-labels.md)). Their values repeat across hundreds of rows, so each section below states them once, with its exceptions, instead of in three columns; a table added later carries them as columns, which are binding as `kind` is. The prose column that says what a row covers is `covers`, since `scope` is a label.

## Rules

| Rule | Detail |
|------|--------|
| Binding | `id`, `slug`, `title`, primary pattern, `kind` and `batch` in this file are binding. A stream creates exactly the rows it owns, at `problems/<id>-<slug>/` (or `tracks/<track>/<slug>/`), and touches no other row |
| Slugs | Unique across `problems/` and `tracks/` and immutable once merged, because `progress.db` keys on the slug |
| Ids | Fixed here, not by `cstudy new`. `cstudy new` assigns max + 1, which collides across parallel worktrees, so after scaffolding the author sets `meta.yaml` `id` to the catalog value and renames the directory to match |
| `meta.yaml` | `patterns` is the primary pattern followed by the secondary patterns in the listed order; `difficulty` and `kind` match the row; `domains`, `job_roles` and `scope` are the section's labels, with its exceptions; `references.leetcode.number` is the `lc` column |
| Changes | A stream that cannot build a row as listed stops and reports. The catalog is amended in the main checkout first, never inside a stream worktree |
| Wording | Statements, examples, tests, hints and explanations are original ([ADR 0004](../decisions/0004-original-problem-wording.md)). Common titles are allowed; LeetCode appears only as a link in `references.leetcode` |
| Merge | A batch merges only when all its problems are `ready` and pass `cstudy verify --oracle` (and `--ladder` from Phase 2 on), as [content](content.md#content-batches) states |
| Languages | Every problem has references in all six languages (Python, TypeScript, Java, Kotlin, Go, Rust) and lists no `languages`, except the rows whose `languages` column says otherwise, `0055-linked-list-cycle`, which has no Rust ([S13](authoring.md#static), [ADR 0012](../decisions/0012-go-and-rust.md)), a problem with `security`, `identity` or `ai-llm` among its domains, which may list any subset and states it in the `languages` column ([ADR 0020](../decisions/0020-catalog-labels.md#rule-changes)), and project problems, which list exactly the one language in their `language` column ([ADR 0014](../decisions/0014-project-problems.md)) |

## How streams use this file

1. Find the rows whose `stream` is yours (DSA) or whose section names you as owner (non-DSA).
2. Build them batch by batch; within a pattern, ids run from easy to hard, which is also a sensible `order` for `meta.yaml`.
3. Rows marked `existing` are already in `problems/`. Their stream owns any revision, but they do not count toward its quota.

## Id order

Existing problems keep `0001`–`0003`. New DSA ids run from `0004` to `0185` by batch (1 to 6), then taxonomy order within a batch, then difficulty within a pattern. Non-DSA items in `problems/` continue at `0186`–`0213` in the order practical, lld, concurrency, debugging. Problems added after the plan take the next free ids: `0214`–`0228` practical, `0229`–`0239` DSA, `0240`–`0247` the Go and Rust debugging problems, `0248` practical, `0249`–`0254` the practical project problems, and `0255`–`0261` the first wave of security and AI/LLM problems. Items in `tracks/` have slugs and no ids.

## DSA catalog

Labels: `domains: [algorithms]`, `job_roles: [general]` and `scope: function` on all 198 rows, with no exceptions.

198 problems: 185 planned in six batches, and 13 [added later](#later-dsa-additions). Columns: `id`, `slug`, `title`, `primary` pattern, `secondary` patterns, `difficulty`, `lc` (LeetCode reference number, reference only), `kind`, `batch`, `stream`. Rows marked `existing` are already in `problems/`; their stream owns any revision but they do not count toward its quota.

### Batch 1 (34 problems: `arrays-hashing`, `two-pointers`, `sliding-window`, `stack`)

| id | slug | title | primary | secondary | difficulty | lc | kind | batch | stream |
|----|------|-------|---------|-----------|------------|----|------|-------|--------|
| 0001 | `two-sum` | Two Sum | `arrays-hashing` | - | easy | 1 | function | 1 | D1 (existing) |
| 0004 | `contains-duplicate` | Contains Duplicate | `arrays-hashing` | - | easy | 217 | function | 1 | D1 |
| 0005 | `valid-anagram` | Valid Anagram | `arrays-hashing` | - | easy | 242 | function | 1 | D1 |
| 0006 | `majority-element` | Majority Element | `arrays-hashing` | - | easy | 169 | function | 1 | D1 |
| 0007 | `group-anagrams` | Group Anagrams | `arrays-hashing` | - | medium | 49 | function | 1 | D1 |
| 0008 | `longest-consecutive-sequence` | Longest Consecutive Run | `arrays-hashing` | - | medium | 128 | function | 1 | D1 |
| 0009 | `product-except-self` | Product Except Self | `arrays-hashing` | `prefix-sum` | medium | 238 | function | 1 | D1 |
| 0010 | `top-k-frequent-elements` | Top K Frequent Elements | `arrays-hashing` | `heap` | medium | 347 | function | 1 | D1 |
| 0011 | `encode-decode-strings` | Encode and Decode Strings | `arrays-hashing` | - | medium | 271 | function | 1 | D1 |
| 0012 | `valid-sudoku` | Valid Sudoku | `arrays-hashing` | - | medium | 36 | function | 1 | D1 |
| 0013 | `randomized-set` | Randomized Set | `arrays-hashing` | - | medium | 380 | design | 1 | D1 |
| 0014 | `first-missing-positive` | First Missing Positive | `arrays-hashing` | - | hard | 41 | function | 1 | D1 |
| 0015 | `valid-palindrome` | Valid Palindrome | `two-pointers` | - | easy | 125 | function | 1 | D2 |
| 0016 | `move-zeroes` | Move Zeroes | `two-pointers` | - | easy | 283 | function | 1 | D2 |
| 0017 | `almost-palindrome` | Palindrome With One Deletion | `two-pointers` | `greedy` | easy | 680 | function | 1 | D2 |
| 0018 | `three-sum` | Three Sum | `two-pointers` | `arrays-hashing` | medium | 15 | function | 1 | D2 |
| 0019 | `container-with-most-water` | Container With Most Water | `two-pointers` | `greedy` | medium | 11 | function | 1 | D2 |
| 0020 | `two-sum-sorted` | Two Sum on Sorted Input | `two-pointers` | `binary-search` | medium | 167 | function | 1 | D2 |
| 0021 | `sort-colors` | Sort Colors | `two-pointers` | - | medium | 75 | function | 1 | D2 |
| 0022 | `trapping-rain-water` | Trapping Rain Water | `two-pointers` | `monotonic-stack`, `dp-1d` | hard | 42 | function | 1 | D2 |
| 0023 | `longest-substring-without-repeats` | Longest Substring Without Repeats | `sliding-window` | `arrays-hashing` | medium | 3 | function | 1 | D2 |
| 0024 | `longest-repeating-replacement` | Longest Repeating Replacement | `sliding-window` | `arrays-hashing` | medium | 424 | function | 1 | D2 |
| 0025 | `permutation-in-string` | Permutation in String | `sliding-window` | `arrays-hashing` | medium | 567 | function | 1 | D2 |
| 0026 | `min-size-subarray-sum` | Minimum Size Subarray Sum | `sliding-window` | `prefix-sum`, `binary-search` | medium | 209 | function | 1 | D2 |
| 0027 | `fruit-into-baskets` | Fruit Into Baskets | `sliding-window` | `arrays-hashing` | medium | 904 | function | 1 | D2 |
| 0028 | `max-ones-with-flips` | Max Consecutive Ones With K Flips | `sliding-window` | - | medium | 1004 | function | 1 | D2 |
| 0029 | `minimum-window-substring` | Minimum Window Substring | `sliding-window` | `arrays-hashing` | hard | 76 | function | 1 | D2 |
| 0030 | `sliding-window-maximum` | Sliding Window Maximum | `sliding-window` | `monotonic-stack` | hard | 239 | function | 1 | D2 |
| 0031 | `valid-parentheses` | Valid Parentheses | `stack` | - | easy | 20 | function | 1 | D1 |
| 0032 | `min-stack` | Min Stack | `stack` | - | medium | 155 | design | 1 | D1 |
| 0033 | `evaluate-rpn` | Evaluate Reverse Polish Notation | `stack` | - | medium | 150 | function | 1 | D1 |
| 0034 | `basic-calculator` | Basic Calculator | `stack` | - | medium | 227 | function | 1 | D1 |
| 0035 | `decode-string` | Decode String | `stack` | - | medium | 394 | function | 1 | D1 |
| 0036 | `min-remove-to-balance` | Minimum Removals to Balance Parentheses | `stack` | - | medium | 1249 | function | 1 | D1 |

### Batch 2 (32 problems: `monotonic-stack`, `binary-search`, `linked-list`, `intervals`)

| id | slug | title | primary | secondary | difficulty | lc | kind | batch | stream |
|----|------|-------|---------|-----------|------------|----|------|-------|--------|
| 0037 | `daily-temperatures` | Daily Temperatures | `monotonic-stack` | - | medium | 739 | function | 2 | D9 |
| 0038 | `car-fleet` | Car Fleet | `monotonic-stack` | - | medium | 853 | function | 2 | D9 |
| 0039 | `stock-span` | Stock Span | `monotonic-stack` | - | medium | 901 | design | 2 | D9 |
| 0040 | `sum-of-subarray-minimums` | Sum of Subarray Minimums | `monotonic-stack` | `dp-1d` | medium | 907 | function | 2 | D9 |
| 0041 | `remove-k-digits` | Remove K Digits | `monotonic-stack` | `greedy` | medium | 402 | function | 2 | D9 |
| 0042 | `largest-rectangle-histogram` | Largest Rectangle in Histogram | `monotonic-stack` | - | hard | 84 | function | 2 | D9 |
| 0043 | `binary-search` | Binary Search | `binary-search` | - | easy | 704 | function | 2 | D3 |
| 0044 | `search-rotated-array` | Search in Rotated Sorted Array | `binary-search` | - | medium | 33 | function | 2 | D3 |
| 0045 | `min-in-rotated-array` | Minimum in Rotated Sorted Array | `binary-search` | - | medium | 153 | function | 2 | D3 |
| 0046 | `koko-eating-bananas` | Koko Eating Bananas | `binary-search` | - | medium | 875 | function | 2 | D3 |
| 0047 | `search-2d-matrix` | Search a Sorted Matrix | `binary-search` | - | medium | 74 | function | 2 | D3 |
| 0048 | `time-based-kv-store` | Time-Based Key-Value Store | `binary-search` | `arrays-hashing` | medium | 981 | design | 2 | D3 |
| 0049 | `first-last-position` | First and Last Position | `binary-search` | - | medium | 34 | function | 2 | D3 |
| 0050 | `find-peak-element` | Find a Peak Element | `binary-search` | - | medium | 162 | function | 2 | D3 |
| 0051 | `median-of-two-sorted-arrays` | Median of Two Sorted Arrays | `binary-search` | - | hard | 4 | function | 2 | D3 |
| 0052 | `split-array-largest-sum` | Split Array Largest Sum | `binary-search` | `greedy` | hard | 410 | function | 2 | D3 |
| 0053 | `reverse-linked-list` | Reverse Linked List | `linked-list` | - | easy | 206 | function | 2 | D4 |
| 0054 | `merge-two-sorted-lists` | Merge Two Sorted Lists | `linked-list` | - | easy | 21 | function | 2 | D4 |
| 0055 | `linked-list-cycle` | Linked List Cycle | `linked-list` | `two-pointers` | easy | 141 | function | 2 | D4 |
| 0056 | `reorder-list` | Reorder List | `linked-list` | `two-pointers` | medium | 143 | function | 2 | D4 |
| 0002 | `lru-cache` | LRU Cache | `linked-list` | `arrays-hashing` | medium | 146 | design | 2 | D4 (existing) |
| 0057 | `remove-nth-from-end` | Remove Nth Node From End | `linked-list` | `two-pointers` | medium | 19 | function | 2 | D4 |
| 0058 | `add-two-numbers` | Add Two Numbers | `linked-list` | `math-geometry` | medium | 2 | function | 2 | D4 |
| 0059 | `sort-linked-list` | Sort a Linked List | `linked-list` | `two-pointers` | medium | 148 | function | 2 | D4 |
| 0060 | `merge-k-sorted-lists` | Merge K Sorted Lists | `linked-list` | `heap` | hard | 23 | function | 2 | D4 |
| 0061 | `reverse-nodes-in-k-group` | Reverse Nodes in K-Groups | `linked-list` | - | hard | 25 | function | 2 | D4 |
| 0062 | `merge-intervals` | Merge Intervals | `intervals` | - | medium | 56 | function | 2 | D3 |
| 0063 | `insert-interval` | Insert Interval | `intervals` | - | medium | 57 | function | 2 | D3 |
| 0064 | `non-overlapping-intervals` | Non-Overlapping Intervals | `intervals` | `greedy` | medium | 435 | function | 2 | D3 |
| 0065 | `min-meeting-rooms` | Minimum Meeting Rooms | `intervals` | `heap` | medium | 253 | function | 2 | D3 |
| 0066 | `interval-list-intersections` | Interval List Intersections | `intervals` | `two-pointers` | medium | 986 | function | 2 | D3 |
| 0067 | `min-interval-per-query` | Smallest Interval per Query | `intervals` | `heap` | hard | 1851 | function | 2 | D3 |

### Batch 3 (28 problems: `trees`, `tries`, `heap`)

| id | slug | title | primary | secondary | difficulty | lc | kind | batch | stream |
|----|------|-------|---------|-----------|------------|----|------|-------|--------|
| 0003 | `invert-binary-tree` | Invert Binary Tree | `trees` | - | easy | 226 | function | 3 | D5 (existing) |
| 0068 | `max-depth-binary-tree` | Maximum Depth of a Binary Tree | `trees` | - | easy | 104 | function | 3 | D5 |
| 0069 | `same-tree` | Same Tree | `trees` | - | easy | 100 | function | 3 | D5 |
| 0070 | `subtree-of-another-tree` | Subtree of Another Tree | `trees` | - | easy | 572 | function | 3 | D5 |
| 0071 | `diameter-binary-tree` | Diameter of a Binary Tree | `trees` | - | easy | 543 | function | 3 | D5 |
| 0072 | `balanced-binary-tree` | Balanced Binary Tree | `trees` | - | easy | 110 | function | 3 | D5 |
| 0073 | `level-order-traversal` | Level Order Traversal | `trees` | - | medium | 102 | function | 3 | D5 |
| 0074 | `validate-bst` | Validate a Binary Search Tree | `trees` | - | medium | 98 | function | 3 | D5 |
| 0075 | `lowest-common-ancestor` | Lowest Common Ancestor | `trees` | - | medium | 236 | function | 3 | D5 |
| 0076 | `kth-smallest-in-bst` | Kth Smallest in a BST | `trees` | - | medium | 230 | function | 3 | D5 |
| 0077 | `tree-from-preorder-inorder` | Tree From Preorder and Inorder | `trees` | `arrays-hashing` | medium | 105 | function | 3 | D5 |
| 0078 | `right-side-view` | Right Side View | `trees` | - | medium | 199 | function | 3 | D5 |
| 0079 | `bst-iterator` | BST Iterator | `trees` | `stack` | medium | 173 | design | 3 | D5 |
| 0080 | `vertical-order-traversal` | Vertical Order Traversal | `trees` | `arrays-hashing` | medium | 314 | function | 3 | D5 |
| 0081 | `max-path-sum` | Binary Tree Maximum Path Sum | `trees` | - | hard | 124 | function | 3 | D5 |
| 0082 | `serialize-binary-tree` | Serialize and Deserialize a Binary Tree | `trees` | - | hard | 297 | function | 3 | D5 |
| 0083 | `implement-trie` | Implement a Trie | `tries` | - | medium | 208 | design | 3 | D5 |
| 0084 | `wildcard-word-dictionary` | Word Dictionary With Wildcards | `tries` | `backtracking` | medium | 211 | design | 3 | D5 |
| 0085 | `search-suggestions` | Search Suggestions | `tries` | `binary-search` | medium | 1268 | function | 3 | D5 |
| 0086 | `word-search-ii` | Word Search II | `tries` | `backtracking` | hard | 212 | function | 3 | D5 |
| 0087 | `last-stone-weight` | Last Stone Weight | `heap` | - | easy | 1046 | function | 3 | D4 |
| 0088 | `kth-largest-element` | Kth Largest Element | `heap` | - | medium | 215 | function | 3 | D4 |
| 0089 | `task-scheduler` | Task Scheduler | `heap` | `greedy` | medium | 621 | function | 3 | D4 |
| 0090 | `k-closest-points` | K Closest Points to Origin | `heap` | - | medium | 973 | function | 3 | D4 |
| 0091 | `design-twitter` | Mini Twitter | `heap` | `arrays-hashing` | medium | 355 | design | 3 | D4 |
| 0092 | `single-threaded-cpu` | Single-Threaded CPU | `heap` | - | medium | 1834 | function | 3 | D4 |
| 0093 | `median-data-stream` | Median of a Data Stream | `heap` | - | hard | 295 | design | 3 | D4 |
| 0094 | `maximize-capital` | Maximize Capital | `heap` | `greedy` | hard | 502 | function | 3 | D4 |

### Batch 4 (31 problems: `backtracking`, `graphs`, `topological-sort`, `union-find`)

| id | slug | title | primary | secondary | difficulty | lc | kind | batch | stream |
|----|------|-------|---------|-----------|------------|----|------|-------|--------|
| 0095 | `subsets` | Subsets | `backtracking` | - | medium | 78 | function | 4 | D6 |
| 0096 | `permutations` | Permutations | `backtracking` | - | medium | 46 | function | 4 | D6 |
| 0097 | `combination-sum` | Combination Sum | `backtracking` | - | medium | 39 | function | 4 | D6 |
| 0098 | `word-search` | Word Search | `backtracking` | - | medium | 79 | function | 4 | D6 |
| 0099 | `subsets-with-duplicates` | Subsets With Duplicates | `backtracking` | - | medium | 90 | function | 4 | D6 |
| 0100 | `combination-sum-no-reuse` | Combination Sum Without Reuse | `backtracking` | - | medium | 40 | function | 4 | D6 |
| 0101 | `palindrome-partitioning` | Palindrome Partitioning | `backtracking` | - | medium | 131 | function | 4 | D6 |
| 0102 | `phone-letter-combinations` | Phone Letter Combinations | `backtracking` | - | medium | 17 | function | 4 | D6 |
| 0103 | `generate-parentheses` | Generate Parentheses | `backtracking` | `stack` | medium | 22 | function | 4 | D6 |
| 0104 | `n-queens` | N-Queens | `backtracking` | - | hard | 51 | function | 4 | D6 |
| 0105 | `number-of-islands` | Number of Islands | `graphs` | - | medium | 200 | function | 4 | D7 |
| 0106 | `clone-graph` | Clone Graph | `graphs` | `arrays-hashing` | medium | 133 | function | 4 | D7 |
| 0107 | `pacific-atlantic-water-flow` | Pacific Atlantic Water Flow | `graphs` | - | medium | 417 | function | 4 | D7 |
| 0108 | `max-area-of-island` | Max Area of Island | `graphs` | - | medium | 695 | function | 4 | D7 |
| 0109 | `rotting-oranges` | Rotting Oranges | `graphs` | - | medium | 994 | function | 4 | D7 |
| 0110 | `surrounded-regions` | Surrounded Regions | `graphs` | - | medium | 130 | function | 4 | D7 |
| 0111 | `bipartite-graph` | Is the Graph Bipartite | `graphs` | `union-find` | medium | 785 | function | 4 | D7 |
| 0112 | `evaluate-division` | Evaluate Division | `graphs` | `union-find` | medium | 399 | function | 4 | D7 |
| 0113 | `shortest-path-binary-matrix` | Shortest Path in a Binary Grid | `graphs` | - | medium | 1091 | function | 4 | D7 |
| 0114 | `open-the-lock` | Open the Lock | `graphs` | - | medium | 752 | function | 4 | D7 |
| 0115 | `word-ladder` | Word Ladder | `graphs` | - | hard | 127 | function | 4 | D7 |
| 0116 | `shortest-path-with-removals` | Shortest Path With Obstacle Removals | `graphs` | - | hard | 1293 | function | 4 | D7 |
| 0117 | `course-schedule` | Course Schedule | `topological-sort` | `graphs` | medium | 207 | function | 4 | D6 |
| 0118 | `parallel-courses` | Parallel Courses | `topological-sort` | `graphs` | medium | 1136 | function | 4 | D6 |
| 0119 | `all-possible-recipes` | All Possible Recipes | `topological-sort` | `graphs` | medium | 2115 | function | 4 | D6 |
| 0120 | `alien-dictionary` | Alien Dictionary | `topological-sort` | `graphs` | hard | 269 | function | 4 | D6 |
| 0121 | `count-connected-components` | Count Connected Components | `union-find` | `graphs` | medium | 323 | function | 4 | D6 |
| 0122 | `redundant-connection` | Redundant Connection | `union-find` | `graphs` | medium | 684 | function | 4 | D6 |
| 0123 | `accounts-merge` | Accounts Merge | `union-find` | `graphs` | medium | 721 | function | 4 | D6 |
| 0124 | `smallest-string-with-swaps` | Smallest String With Swaps | `union-find` | `graphs` | medium | 1202 | function | 4 | D6 |
| 0125 | `number-of-islands-ii` | Number of Islands II | `union-find` | `graphs` | hard | 305 | function | 4 | D6 |

### Batch 5 (32 problems: `dp-1d`, `dp-2d`, `greedy`)

| id | slug | title | primary | secondary | difficulty | lc | kind | batch | stream |
|----|------|-------|---------|-----------|------------|----|------|-------|--------|
| 0126 | `climbing-stairs` | Climbing Stairs | `dp-1d` | - | easy | 70 | function | 5 | D8 |
| 0127 | `house-robber` | House Robber | `dp-1d` | - | medium | 198 | function | 5 | D8 |
| 0128 | `coin-change` | Coin Change | `dp-1d` | - | medium | 322 | function | 5 | D8 |
| 0129 | `longest-increasing-subsequence` | Longest Increasing Subsequence | `dp-1d` | `binary-search` | medium | 300 | function | 5 | D8 |
| 0130 | `partition-equal-subset-sum` | Partition Equal Subset Sum | `dp-1d` | - | medium | 416 | function | 5 | D8 |
| 0131 | `max-product-subarray` | Maximum Product Subarray | `dp-1d` | - | medium | 152 | function | 5 | D8 |
| 0132 | `decode-ways` | Decode Ways | `dp-1d` | - | medium | 91 | function | 5 | D8 |
| 0133 | `word-break` | Word Break | `dp-1d` | - | medium | 139 | function | 5 | D8 |
| 0134 | `longest-palindromic-substring` | Longest Palindromic Substring | `dp-1d` | `two-pointers` | medium | 5 | function | 5 | D8 |
| 0135 | `stock-with-cooldown` | Stock Trading With Cooldown | `dp-1d` | - | medium | 309 | function | 5 | D8 |
| 0136 | `min-cost-tickets` | Minimum Cost for Tickets | `dp-1d` | - | medium | 983 | function | 5 | D8 |
| 0137 | `job-scheduling-max-profit` | Job Scheduling for Maximum Profit | `dp-1d` | `binary-search` | hard | 1235 | function | 5 | D8 |
| 0138 | `unique-paths` | Unique Paths | `dp-2d` | - | medium | 62 | function | 5 | D9 |
| 0139 | `longest-common-subsequence` | Longest Common Subsequence | `dp-2d` | - | medium | 1143 | function | 5 | D9 |
| 0140 | `edit-distance` | Edit Distance | `dp-2d` | - | medium | 72 | function | 5 | D9 |
| 0141 | `coin-change-ways` | Coin Change Combinations | `dp-2d` | - | medium | 518 | function | 5 | D9 |
| 0142 | `interleaving-string` | Interleaving String | `dp-2d` | - | medium | 97 | function | 5 | D9 |
| 0143 | `maximal-square` | Maximal Square | `dp-2d` | - | medium | 221 | function | 5 | D9 |
| 0144 | `target-sum` | Target Sum | `dp-2d` | `backtracking` | medium | 494 | function | 5 | D9 |
| 0145 | `distinct-subsequences` | Distinct Subsequences | `dp-2d` | - | hard | 115 | function | 5 | D9 |
| 0146 | `burst-balloons` | Burst Balloons | `dp-2d` | - | hard | 312 | function | 5 | D9 |
| 0147 | `longest-increasing-path-matrix` | Longest Increasing Path in a Matrix | `dp-2d` | `graphs`, `topological-sort` | hard | 329 | function | 5 | D9 |
| 0148 | `regex-matching` | Regular Expression Matching | `dp-2d` | - | hard | 10 | function | 5 | D9 |
| 0149 | `maximal-rectangle` | Maximal Rectangle | `dp-2d` | `monotonic-stack` | hard | 85 | function | 5 | D9 |
| 0150 | `best-time-to-buy-sell-stock` | Best Time to Buy and Sell Stock | `greedy` | `sliding-window` | easy | 121 | function | 5 | D8 |
| 0151 | `jump-game` | Jump Game | `greedy` | - | medium | 55 | function | 5 | D8 |
| 0152 | `gas-station` | Gas Station | `greedy` | - | medium | 134 | function | 5 | D8 |
| 0153 | `partition-labels` | Partition Labels | `greedy` | `two-pointers` | medium | 763 | function | 5 | D8 |
| 0154 | `hand-of-straights` | Hand of Straights | `greedy` | `arrays-hashing` | medium | 846 | function | 5 | D8 |
| 0155 | `maximum-subarray` | Maximum Subarray | `greedy` | `dp-1d` | medium | 53 | function | 5 | D8 |
| 0156 | `valid-parenthesis-string` | Parentheses With Wildcards | `greedy` | `stack` | medium | 678 | function | 5 | D8 |
| 0157 | `candy-distribution` | Candy Distribution | `greedy` | - | hard | 135 | function | 5 | D8 |

### Batch 6 (28 problems: `advanced-graphs`, `prefix-sum`, `math-geometry`, `bit-manipulation`, `segment-tree-fenwick`)

| id | slug | title | primary | secondary | difficulty | lc | kind | batch | stream |
|----|------|-------|---------|-----------|------------|----|------|-------|--------|
| 0158 | `network-delay-time` | Network Delay Time | `advanced-graphs` | `heap` | medium | 743 | function | 6 | D7 |
| 0159 | `min-cost-connect-points` | Minimum Cost to Connect Points | `advanced-graphs` | `union-find` | medium | 1584 | function | 6 | D7 |
| 0160 | `cheapest-flights-k-stops` | Cheapest Flights Within K Stops | `advanced-graphs` | `dp-2d` | medium | 787 | function | 6 | D7 |
| 0161 | `city-fewest-neighbors` | City With Fewest Reachable Neighbors | `advanced-graphs` | - | medium | 1334 | function | 6 | D7 |
| 0162 | `swim-rising-water` | Swim in Rising Water | `advanced-graphs` | `heap`, `binary-search` | hard | 778 | function | 6 | D7 |
| 0163 | `reconstruct-itinerary` | Reconstruct Itinerary | `advanced-graphs` | - | hard | 332 | function | 6 | D7 |
| 0164 | `critical-connections` | Critical Connections | `advanced-graphs` | `graphs` | hard | 1192 | function | 6 | D7 |
| 0165 | `min-obstacle-removal` | Minimum Obstacle Removal | `advanced-graphs` | `graphs` | hard | 2290 | function | 6 | D7 |
| 0166 | `range-sum-immutable` | Range Sum Query | `prefix-sum` | - | easy | 303 | design | 6 | D10 |
| 0167 | `range-sum-2d` | Range Sum Query 2D | `prefix-sum` | - | medium | 304 | design | 6 | D10 |
| 0168 | `subarray-sum-equals-k` | Subarray Sum Equals K | `prefix-sum` | `arrays-hashing` | medium | 560 | function | 6 | D10 |
| 0169 | `continuous-subarray-sum` | Continuous Subarray Sum | `prefix-sum` | `arrays-hashing` | medium | 523 | function | 6 | D10 |
| 0170 | `car-pooling` | Car Pooling | `prefix-sum` | - | medium | 1094 | function | 6 | D10 |
| 0171 | `tree-path-sum-count` | Count Downward Path Sums | `prefix-sum` | `trees` | medium | 437 | function | 6 | D10 |
| 0172 | `rotate-image` | Rotate Image | `math-geometry` | - | medium | 48 | function | 6 | D10 |
| 0173 | `spiral-matrix` | Spiral Matrix | `math-geometry` | - | medium | 54 | function | 6 | D10 |
| 0174 | `set-matrix-zeroes` | Set Matrix Zeroes | `math-geometry` | - | medium | 73 | function | 6 | D10 |
| 0175 | `fast-power` | Fast Power | `math-geometry` | - | medium | 50 | function | 6 | D10 |
| 0176 | `multiply-strings` | Multiply Strings | `math-geometry` | - | medium | 43 | function | 6 | D10 |
| 0177 | `max-points-on-line` | Max Points on a Line | `math-geometry` | `arrays-hashing` | hard | 149 | function | 6 | D10 |
| 0178 | `single-number` | Single Number | `bit-manipulation` | - | easy | 136 | function | 6 | D10 |
| 0179 | `count-set-bits` | Count Set Bits | `bit-manipulation` | - | easy | 191 | function | 6 | D10 |
| 0180 | `counting-bits` | Counting Bits | `bit-manipulation` | `dp-1d` | easy | 338 | function | 6 | D10 |
| 0181 | `missing-number` | Missing Number | `bit-manipulation` | `math-geometry` | easy | 268 | function | 6 | D10 |
| 0182 | `sum-without-plus` | Sum Without Arithmetic Operators | `bit-manipulation` | - | medium | 371 | function | 6 | D10 |
| 0183 | `range-sum-mutable` | Range Sum Query With Updates | `segment-tree-fenwick` | `prefix-sum` | medium | 307 | design | 6 | D10 |
| 0184 | `count-smaller-after-self` | Count Smaller Numbers After Self | `segment-tree-fenwick` | `binary-search` | hard | 315 | function | 6 | D10 |
| 0185 | `range-module` | Range Module | `segment-tree-fenwick` | `intervals` | hard | 715 | design | 6 | D10 |

### Later DSA additions

13 problems added after the six batches, outside the stream plan, with the next free ids. Two of them are examples the original selection [replaced](#departures-from-the-example-additions-in-content): Meeting Rooms (252) as `can-attend-meetings`, and Course Schedule II (210).

| id | slug | title | primary | secondary | difficulty | lc | kind |
|----|------|-------|---------|-----------|------------|----|------|
| 0229 | `can-attend-meetings` | Can Attend All Meetings | `intervals` | - | easy | 252 | function |
| 0230 | `employee-free-time` | Employee Free Time | `intervals` | `heap` | hard | 759 | function |
| 0231 | `remove-covered-intervals` | Remove Covered Intervals | `intervals` | - | medium | 1288 | function |
| 0232 | `snapshot-array` | Snapshot Array | `binary-search` | `arrays-hashing` | medium | 1146 | design |
| 0233 | `employee-importance` | Employee Importance | `graphs` | `arrays-hashing` | medium | 690 | function |
| 0234 | `course-schedule-ii` | Course Schedule II | `topological-sort` | `graphs` | medium | 210 | function |
| 0235 | `time-to-inform-employees` | Time to Inform All Employees | `graphs` | `trees` | medium | 1376 | function |
| 0236 | `search-insert-position` | Search Insert Position | `binary-search` | - | easy | 35 | function |
| 0237 | `tax-brackets` | Tax Owed Under Brackets | `math-geometry` | - | easy | 2303 | function |
| 0238 | `replace-words` | Replace Words with Roots | `tries` | `arrays-hashing` | medium | 648 | function |
| 0239 | `sorted-insertion-cost` | Sorted Insertion Cost | `segment-tree-fenwick` | `binary-search` | hard | 1649 | function |
| 0308 | `all-grid-paths` | All Grid Paths | `backtracking` | - | medium | - | function |
| 0309 | `find-missing-and-duplicates` | Find All Missing and Duplicate Numbers | `arrays-hashing` | - | medium | - | function |

## Stream assignment

| stream | patterns | batches | new problems | ids (new only) |
|--------|----------|---------|--------------|----------------|
| D1 | `arrays-hashing`, `stack` | 1 | 17 | 0004–0014, 0031–0036 |
| D2 | `two-pointers`, `sliding-window` | 1 | 16 | 0015–0030 |
| D3 | `binary-search`, `intervals` | 2 | 16 | 0043–0052, 0062–0067 |
| D4 | `linked-list`, `heap` | 2, 3 | 17 | 0053–0061, 0087–0094 |
| D5 | `trees`, `tries` | 3 | 19 | 0068–0086 |
| D6 | `backtracking`, `topological-sort`, `union-find` | 4 | 19 | 0095–0104, 0117–0125 |
| D7 | `graphs`, `advanced-graphs` | 4, 6 | 20 | 0105–0116, 0158–0165 |
| D8 | `dp-1d`, `greedy` | 5 | 20 | 0126–0137, 0150–0157 |
| D9 | `dp-2d`, `monotonic-stack` | 2, 5 | 18 | 0037–0042, 0138–0149 |
| D10 | `prefix-sum`, `math-geometry`, `bit-manipulation`, `segment-tree-fenwick` | 6 | 20 | 0166–0185 |
| **Total** | 23 patterns | 1–6 | **182** | 0004–0185 |

Each stream owns whole patterns, so one stream holds all problems of a pattern and its `related` links. Batch 1 (Phase 1) is never mixed with later batches. Batches 2 to 6 all belong to Phase 3, and none of them splits into whole-pattern streams of 16 to 20 on its own (for example batch 2 has 31 new problems, which gives 16 and 15 at best), so D4, D7 and D9 each pair patterns from two Phase 3 batches. A stream with two batches finishes the earlier batch's patterns first, so that batch can merge without waiting.

## Non-DSA catalog

### practical (80, `problems/`)

Labels: `0186` to `0191` and `0248` (the 7 `progressive` rows, `domains: [backend]`, `job_roles: [backend]`, `scope: function`); `0214` to `0228` (the 15 insurance rows, `domains: [fintech]`, `job_roles: [backend]`, `scope: function`); `0249` to `0254` (the 6 project problems, `domains: [backend, fintech]`, `job_roles: [backend]`, `scope: project`). Exceptions: `banking-system` and `scheduled-transfers-bank` also have `fintech`, and `api-gateway` also has the role `platform`. `0255` to `0261` carry their labels as columns.

The six planned rows (owner P1) are `progressive`:

| id | slug | title | covers | difficulty |
|----|------|-------|-------|------------|
| 0186 | `in-memory-database` | In-Memory Database | Records with fields; then prefix scans; then per-field TTL; then point-in-time reads over history | hard |
| 0187 | `banking-system` | Banking System | Accounts, deposits and transfers; then top spenders; then scheduled payments with cashback; then account merges with historical balances | hard |
| 0188 | `cloud-file-storage` | Cloud File Storage | Add, read and delete files; then size-ordered listing by prefix; then per-user quotas; then backup and restore | medium |
| 0189 | `job-scheduler` | Rate-Limited Job Scheduler | Submit and run jobs by priority; then per-tenant rate limits; then retries with backoff; then dependencies and cancellation | hard |
| 0190 | `transactional-kv-store` | Transactional Key-Value Store | Set, get and count by value; then begin and rollback; then nested transactions; then commit semantics with snapshots | medium |
| 0191 | `api-gateway` | API Gateway | Route registration and matching; then per-client fixed-window limits; then sliding windows and quotas; then per-upstream circuit breakers | hard |

15 added later are insurance tasks of every kind, many with `decimal` and `date` values:

| id | slug | title | patterns | kind | difficulty |
|----|------|-------|----------|------|------------|
| 0214 | `premium-rating-breakdown` | Premium Rating Breakdown | `binary-search`, `arrays-hashing` | function | medium |
| 0215 | `versioned-rate-table` | Versioned Rate Table | `binary-search` | design | medium |
| 0216 | `pro-rata-unearned-premium` | Pro-Rata Unearned Premium | - | function | easy |
| 0217 | `coverage-gaps` | Coverage Gaps | `intervals` | function | medium |
| 0218 | `contractor-exposure-rollup` | Contractor Exposure Rollup | `graphs` | function | medium |
| 0219 | `installment-schedule` | Installment Schedule | `math-geometry` | function | medium |
| 0220 | `tiered-bond-premium` | Tiered Bond Premium | - | function | easy |
| 0221 | `earned-premium-as-of` | Earned Premium As Of | - | function | easy |
| 0222 | `endorsement-replay` | Endorsement Replay | `binary-search` | design | medium |
| 0223 | `certificate-expiry-alerts` | Certificate Expiry Alerts | `arrays-hashing` | function | easy |
| 0224 | `loss-ratio-by-period` | Loss Ratio by Period | `arrays-hashing` | function | medium |
| 0225 | `rate-change-impact` | Rate Change Impact | `arrays-hashing` | function | medium |
| 0226 | `payroll-report-validation` | Payroll Report Validation | `arrays-hashing` | function | medium |
| 0227 | `duplicate-contractor-records` | Duplicate Contractor Records | `union-find`, `arrays-hashing` | function | medium |
| 0228 | `effective-dated-history` | Effective-Dated History | `binary-search` | progressive | medium |

One more added later is a sibling of `banking-system` whose level 3 replaces the fixed-delay cashback with transfers that each have their own delay and can be cancelled:

| id | slug | title | patterns | kind | difficulty |
|----|------|-------|----------|------|------------|
| 0248 | `scheduled-transfers-bank` | Scheduled Transfers Bank | `heap` | progressive | hard |

Six [project problems](problem-format.md#project-problems) (kind `project`, one language each) carry `0248`'s behavior and statement wording into a seeded folder. Each is built from scratch, with its own starter, `tests.json` (at least 2 visible and 2 hidden cases per level, covering the rules `0248`'s cases pin down), reference and explanation; each lists the others and `scheduled-transfers-bank` in `related`. `0249` is the Python pilot (roadmap Phase 8a), `0250` the TypeScript one (Phase 8b), `0251` the Java one, `0252` the Kotlin one, `0253` the Go one and `0254` the Rust one; all six exist in `problems/`.

| id | slug | title | language | patterns | kind | difficulty |
|----|------|-------|----------|----------|------|------------|
| 0249 | `bank-project-python` | Bank Project (Python) | `python` | - | project | hard |
| 0250 | `bank-project-typescript` | Bank Project (TypeScript) | `typescript` | - | project | hard |
| 0251 | `bank-project-java` | Bank Project (Java) | `java` | - | project | hard |
| 0252 | `bank-project-kotlin` | Bank Project (Kotlin) | `kotlin` | - | project | hard |
| 0253 | `bank-project-go` | Bank Project (Go) | `go` | - | project | hard |
| 0254 | `bank-project-rust` | Bank Project (Rust) | `rust` | - | project | hard |

The first wave of security and AI/LLM problems ([ADR 0020](../decisions/0020-catalog-labels.md#the-first-wave)) is original, function-size and needs no service. Each lists Python and TypeScript, under the [Languages rule](#rules). The labels are columns here and binding, as `kind` is:

| id | slug | title | patterns | kind | difficulty | languages | domains | job_roles | scope |
|----|------|-------|----------|------|------------|-----------|---------|-----------|-------|
| 0255 | `token-claim-validator` | Token Claim Validator | `arrays-hashing` | function | medium | `python`, `typescript` | `security`, `identity` | `security-engineer`, `backend` | function |
| 0256 | `refresh-token-rotation` | Refresh Token Rotation | `arrays-hashing` | design | medium | `python`, `typescript` | `security`, `identity` | `security-engineer`, `backend` | function |
| 0257 | `authorization-policy-engine` | Authorization Policy Engine | `graphs` | design | medium | `python`, `typescript` | `security` | `security-engineer`, `backend` | function |
| 0258 | `calibration-metrics` | Calibration Metrics | `arrays-hashing` | function | easy | `python`, `typescript` | `ai-llm` | `ml-engineer`, `ai-engineer` | function |
| 0259 | `token-cost-reconciler` | Token Cost Reconciler | `arrays-hashing` | function | medium | `python`, `typescript` | `ai-llm` | `ai-engineer` | function |
| 0260 | `bm25-hybrid-ranker` | BM25 Hybrid Ranker | `arrays-hashing` | function | medium | `python`, `typescript` | `ai-llm` | `ai-engineer`, `ml-engineer` | function |
| 0261 | `stream-reassembler` | Stream Reassembler | `arrays-hashing` | design | medium | `python`, `typescript` | `ai-llm` | `ai-engineer` | function |

Three more TypeScript project problems train work on code you did not write, on the engine as it is. `0262` and `0263` are small working services, laid out differently on purpose, by type and by feature, and each level changes one. There is no HTTP server, since a project has no dependencies: an entry class takes what a request would carry and answers `[status, json]`, with the keys of the JSON sorted in one place. `0267` is a debugging exercise in all but its track: `await` only finishes in a project on the virtual clock ([ADR 0017](../decisions/0017-async-project-problems.md)), so its starter holds the bug instead of a `buggy/` file.

| id | slug | title | kind | difficulty | languages | domains | job_roles | scope |
|----|------|-------|------|------------|-----------|---------|-----------|-------|
| 0262 | `loan-pipeline-service-typescript` | Loan Pipeline Service (TypeScript) | project | hard | `typescript` | `backend`, `fintech` | `backend` | project |
| 0263 | `warehouse-work-orders-typescript` | Warehouse Work Orders (TypeScript) | project | hard | `typescript` | `backend` | `backend` | project |
| 0267 | `debug-async-batch-typescript` | Debug: Async Batch (TypeScript) | project | medium | `typescript` | `backend` | `backend` | project |

Five more TypeScript projects go deep on backend reliability, on the engine as it is. Each is laid out differently, each level removes one assumption, and each explanation says what to say out loud and what to do next in production. Their wrong approaches are not stored as broken overlays, since these logic bugs fail sequential cases ([authoring](authoring.md#practical-and-low-level-design-problems)): each explanation names them under its pitfalls with the cases that catch them. `0274` runs on the virtual clock, and `0276` has no model in it: the model's output arrives as data.

| id | slug | title | kind | difficulty | languages | domains | job_roles | scope |
|----|------|-------|------|------------|-----------|---------|-----------|-------|
| 0272 | `idempotent-document-consumer-typescript` | Idempotent Document Consumer (TypeScript) | project | hard | `typescript` | `backend` | `backend`, `platform` | project |
| 0273 | `transactional-outbox-typescript` | Transactional Outbox (TypeScript) | project | hard | `typescript` | `backend` | `backend`, `platform` | project |
| 0274 | `vendor-retry-client-typescript` | Vendor Retry Client (TypeScript) | project | hard | `typescript` | `backend` | `backend`, `platform` | project |
| 0275 | `supplier-records-locking-typescript` | Supplier Records with Optimistic Locking (TypeScript) | project | hard | `typescript` | `backend` | `backend` | project |
| 0276 | `loan-extraction-review-typescript` | Loan Extraction Review (TypeScript) | project | hard | `typescript` | `ai-llm`, `fintech` | `ai-engineer`, `backend` | project |

The first [service projects](service-projects.md#the-first-problem) run a real app in a Docker sandbox against mock vendors and are graded over HTTP. They are one problem in two languages: the same `tests.json`, mock servers and seeded desks grade both, each built from scratch in its language, and each lists the other in `related`.

| id | slug | title | kind | difficulty | languages | domains | job_roles | scope |
|----|------|-------|------|------------|-----------|---------|-----------|-------|
| 0277 | `coworking-availability-typescript` | Coworking Availability (TypeScript) | project | hard | `typescript` | `backend` | `backend`, `platform` | project |
| 0278 | `coworking-availability-python` | Coworking Availability (Python) | project | hard | `python` | `backend` | `backend`, `platform` | project |

Four more service projects, in TypeScript. `0279` receives a payment provider's signed webhooks, and `0281` delivers a customer's webhooks without reaching your own network. `0280` signs users in with OpenID Connect against a real Keycloak, and `0282` takes many checkouts at once on Postgres. Each has its own `tests.json`; `0279` and `0281` use mock servers, `0280` mocks the identity provider with a pass-through to Keycloak, and `0282` has no mock.

| id | slug | title | kind | difficulty | languages | domains | job_roles | scope |
|----|------|-------|------|------------|-----------|---------|-----------|-------|
| 0279 | `payment-webhook-receiver-typescript` | Payment Webhook Receiver (TypeScript) | project | medium | `typescript` | `fintech`, `security` | `backend`, `security-engineer` | project |
| 0280 | `oauth-pkce-client-typescript` | OAuth Client with PKCE (TypeScript) | project | hard | `typescript` | `identity`, `security` | `backend`, `security-engineer` | project |
| 0281 | `ssrf-safe-webhook-dispatcher-typescript` | SSRF-Safe Webhook Dispatcher (TypeScript) | project | hard | `typescript` | `security` | `security-engineer`, `backend` | project |
| 0282 | `inventory-reservations-typescript` | Inventory Reservations (TypeScript) | project | hard | `typescript` | `backend` | `backend` | project |

Five more service projects, in TypeScript, on the backing services. `0283` builds a job queue on Postgres, and `0284` loads CSV uploads from S3 and SQS on Moto into Postgres. `0285` caches prices and limits request rates on Valkey, the BSD-licensed fork of Redis, behind a mock pricing vendor. `0286` keeps tenants apart with row-level security, and `0287` keeps a ledger as append-only events with projections. Each has its own `tests.json`; only `0285` has a mock server.

| id | slug | title | kind | difficulty | languages | domains | job_roles | scope |
|----|------|-------|------|------------|-----------|---------|-----------|-------|
| 0283 | `postgres-job-queue-typescript` | Postgres Job Queue (TypeScript) | project | hard | `typescript` | `backend` | `backend`, `platform` | project |
| 0284 | `csv-upload-ingestion-typescript` | CSV Upload Ingestion (TypeScript) | project | hard | `typescript` | `backend` | `backend`, `platform` | project |
| 0285 | `price-cache-rate-limits-typescript` | Price Cache and Rate Limits (TypeScript) | project | medium | `typescript` | `backend` | `backend`, `platform` | project |
| 0286 | `multi-tenant-api-typescript` | Multi-Tenant API (TypeScript) | project | hard | `typescript` | `backend`, `security` | `backend`, `security-engineer` | project |
| 0287 | `event-sourced-ledger-typescript` | Event-Sourced Ledger (TypeScript) | project | hard | `typescript` | `fintech`, `backend` | `backend` | project |

Four service projects in TypeScript on P11's mock server extensions, the first project-size AI/LLM problems among them. `0289` stores uploads behind a mock malware scanner that fails, and `0290` is an LLM gateway that streams answers from two mock providers, waits out rate limits, falls back and keeps budgets. `0291` answers from documents with citations, through mock embeddings and chat APIs and vector search on pgvector, and `0292` runs a tool-calling agent loop against a mock model and the shop's tool APIs. Each has its own `tests.json` and mock servers; only `0291` has a backing service.

| id | slug | title | kind | difficulty | languages | domains | job_roles | scope |
|----|------|-------|------|------------|-----------|---------|-----------|-------|
| 0289 | `secure-file-upload-typescript` | Secure File Upload (TypeScript) | project | medium | `typescript` | `security`, `backend` | `backend`, `security-engineer` | project |
| 0290 | `llm-gateway-typescript` | LLM Gateway (TypeScript) | project | hard | `typescript` | `ai-llm`, `backend` | `backend`, `ai-engineer` | project |
| 0291 | `rag-citations-typescript` | RAG Service with Citations (TypeScript) | project | hard | `typescript` | `ai-llm` | `ai-engineer` | project |
| 0292 | `tool-calling-agent-loop-typescript` | Tool-Calling Agent Loop (TypeScript) | project | hard | `typescript` | `ai-llm`, `security` | `ai-engineer`, `security-engineer` | project |

Eleven function-size memory and retrieval problems, original and needing no service, each in Python and TypeScript under the [Languages rule](#rules). `0293` to `0296` are four-level progressive stores: memories per user, a chat history index, a context packer under a token budget, and versioned facts that two stores merge. `0297` keeps BM25 current over an index that forgets, and `0298` cleans text before it is stored as a memory. `0299` to `0303` are retrieval blocks: cosine top k with a bounded heap, chunking with overlap, recall, MRR and nDCG, a freshness reranker, and a memory store with compare-and-set writes. The labels are columns here and binding, as `kind` is:

| id | slug | title | patterns | kind | difficulty | languages | domains | job_roles | scope |
|----|------|-------|----------|------|------------|-----------|---------|-----------|-------|
| 0293 | `memory-store` | Memory Store | - | progressive | hard | `python`, `typescript` | `ai-llm`, `backend` | `backend`, `ai-engineer` | function |
| 0294 | `chat-history-index` | Chat History Index | - | progressive | hard | `python`, `typescript` | `ai-llm`, `backend` | `backend`, `ai-engineer` | function |
| 0295 | `context-packer` | Context Packer | `greedy` | progressive | medium | `python`, `typescript` | `ai-llm`, `backend` | `backend`, `ai-engineer` | function |
| 0296 | `memory-facts-with-merge` | Memory Facts with Merge | - | progressive | hard | `python`, `typescript` | `ai-llm`, `backend` | `backend`, `ai-engineer` | function |
| 0297 | `forgettable-inverted-index` | Forgettable Inverted Index | - | design | medium | `python`, `typescript` | `ai-llm` | `ai-engineer`, `backend` | function |
| 0298 | `memory-write-sanitizer` | Memory Write Sanitizer | - | function | medium | `python`, `typescript` | `ai-llm`, `security` | `ai-engineer`, `security-engineer` | function |
| 0299 | `cosine-top-k` | Cosine Top K | `heap` | function | medium | `python`, `typescript` | `ai-llm` | `ai-engineer`, `backend` | function |
| 0300 | `chunking-with-overlap` | Chunking With Overlap | `sliding-window` | function | medium | `python`, `typescript` | `ai-llm` | `ai-engineer`, `backend` | function |
| 0301 | `retrieval-metrics` | Retrieval Metrics | `arrays-hashing` | function | medium | `python`, `typescript` | `ai-llm` | `ai-engineer`, `backend` | function |
| 0302 | `freshness-reranker` | Freshness Reranker | `arrays-hashing` | function | easy | `python`, `typescript` | `ai-llm` | `ai-engineer`, `backend` | function |
| 0303 | `versioned-memory-store` | Versioned Memory Store | `arrays-hashing` | design | easy | `python`, `typescript` | `ai-llm`, `backend` | `ai-engineer`, `backend` | function |

One function-size, four-level progressive problem in all six languages: `0304` is the logic behind a search input with a list under it. It handles key presses, name matching, typing with stale responses, and selection with Enter. It runs as a plain class, not in a browser. A version graded in a headless browser waits for Phase 16 ([roadmap](../roadmap.md)). The labels are columns here and binding, as `kind` is:

| id | slug | title | patterns | kind | difficulty | languages | domains | job_roles | scope |
|----|------|-------|----------|------|------------|-----------|---------|-----------|-------|
| 0304 | `search-box-navigation` | Search Box with Keyboard Navigation | - | progressive | medium | all six | `backend` | `general` | function |

Two service projects in Java and Kotlin, from P12 ([roadmap](../roadmap.md)): `0305` and `0306` are the Java and Kotlin versions of `0277`. They are graded by the same cases and mock servers as `0277`, each is built from scratch in its language on one Gradle image, and each lists the other versions in `related`.

| id | slug | title | kind | difficulty | languages | domains | job_roles | scope |
|----|------|-------|------|------------|-----------|---------|-----------|-------|
| 0305 | `coworking-availability-java` | Coworking Availability (Java) | project | hard | `java` | `backend` | `backend`, `platform` | project |
| 0306 | `coworking-availability-kotlin` | Coworking Availability (Kotlin) | project | hard | `kotlin` | `backend` | `backend`, `platform` | project |

One service project in Go, from P13 ([roadmap](../roadmap.md)): `0310` is the Go version of `0277`, graded by the same cases and mock servers, built from scratch on Go's standard library, and lists the other versions in `related`.

| id | slug | title | kind | difficulty | languages | domains | job_roles | scope |
|----|------|-------|------|------------|-----------|---------|-----------|-------|
| 0310 | `coworking-availability-go` | Coworking Availability (Go) | project | hard | `go` | `backend` | `backend`, `platform` | project |

One security service project in TypeScript, the built form of PP14 ([roadmap](../roadmap.md)): `0307` hands over a working service with four levels of flaw (notes that belong to someone else, names and fields taken from the request, text that becomes a query, and logs and errors), and grades the fix with attack cases that must fail and normal cases that must keep passing.

| id | slug | title | kind | difficulty | languages | domains | job_roles | scope |
|----|------|-------|------|------------|-----------|---------|-----------|-------|
| 0307 | `fix-the-flaws-typescript` | Fix the Flaws (TypeScript) | project | hard | `typescript` | `security` | `security-engineer`, `backend` | project |

One function-size, four-level progressive problem on hash chaining: `0311` is an audit log that fingerprints batches of records with SHA-256 (with an exact byte encoding, so every language gets the same digests), chains the batches so that one digest stands for a whole history, finds where two histories part by bisecting the chain digests, and proves that a record is in a batch with Merkle inclusion proofs. It lists Python, TypeScript, Java, Kotlin and Go: the security domain lets a problem list a subset ([S13](authoring.md#static)), and Rust's vendored crates hold no SHA-256, so a Rust solution would have to write the hash function first. Its pattern is the nearest of the closed list, `arrays-hashing`, with `binary-search` for level 3.

| id | slug | title | patterns | kind | difficulty | languages | domains | job_roles | scope |
|----|------|-------|----------|------|------------|-----------|---------|-----------|-------|
| 0311 | `tamper-evident-ledger` | Tamper-Evident Ledger | `arrays-hashing`, `binary-search` | progressive | medium | `python`, `typescript`, `java`, `kotlin`, `go` | `security`, `backend` | `security-engineer`, `backend` | function |

One service project in Python on Postgres, from P13 ([roadmap](../roadmap.md)): `0312` is a loyalty program that gets a file of purchases from its shops each day. It loads the file into Postgres once however often it is sent, reports the rows it refuses, works out points in whole cents, and asks a flaky bonus partner (a mock server) for bonuses without failing. Its labels are columns here.

| id | slug | title | kind | difficulty | languages | domains | job_roles | scope |
|----|------|-------|------|------------|-----------|---------|-----------|-------|
| 0312 | `feed-ingest-python` | Feed Ingest (Python) | project | hard | `python` | `backend`, `fintech` | `backend`, `platform` | project |

Three function-size, four-level progressive problems in all six languages, on trees, graphs and a picture of terrain: `0313` builds an org chart from flat (id, parent, name) rows, in any order and with orphans and cycles, and prints an outline of 10^5 rows; `0314` pays a bonus once per referred person, counts direct and indirect referrals and ranks the top referrers, up to a million people; `0316` draws a height profile as text and pours water on it unit by unit, with exact rules for left, right, flat stretches and edges. `0313` and `0314` have a performance ladder. The labels are columns here and binding, as `kind` is:

| id | slug | title | patterns | kind | difficulty | languages | domains | job_roles | scope |
|----|------|-------|----------|------|------------|-----------|---------|-----------|-------|
| 0313 | `org-chart-outline` | Org Chart Outline | `trees`, `arrays-hashing` | progressive | medium | all six | `algorithms`, `backend` | `general`, `backend` | function |
| 0314 | `referral-rewards` | Referral Rewards | `graphs`, `union-find` | progressive | hard | all six | `algorithms`, `backend` | `general`, `backend` | function |
| 0316 | `water-on-terrain` | Water on Terrain | - | progressive | medium | all six | `algorithms` | `general` | function |

One project in Python on AI/LLM and security: `0315` hides the emails, phone numbers and names that a model found in text, and the model is not always right. It checks the model's spans against the text, adds a regex safety net for what the model missed, and scores the result with a recall-weighted F2. It is a project in a plain Python package, not a service. It lists Python only, since the security and AI/LLM domains let a problem list a subset ([S13](authoring.md#static)).

| id | slug | title | kind | difficulty | languages | domains | job_roles | scope |
|----|------|-------|------|------------|-----------|---------|-----------|-------|
| 0315 | `safe-redaction-python` | Safe Redaction (Python) | project | hard | `python` | `ai-llm`, `security` | `ai-engineer`, `security-engineer` | project |

### lld (8, owner L1, kind `design` plus `rubric.md`, `problems/`)

Labels: `domains: [backend]`, `job_roles: [backend]` and `scope: function` on all 8 rows, with no exceptions.

| id | slug | title | covers | difficulty |
|----|------|-------|-------|------------|
| 0192 | `parking-lot` | Parking Lot | Levels, spot sizes, vehicle types, tickets and fees; pricing as an extension point | medium |
| 0193 | `elevator-system` | Elevator System | Multiple cars, request dispatching, direction state machine; dispatch strategy as an extension point | hard |
| 0194 | `cache-service` | Cache Service | LRU-backed cache with TTL, pluggable eviction policy, hit and miss statistics | medium |
| 0195 | `event-bus` | Event Bus | Topic subscriptions, ordered delivery, wildcard topics, unsubscribe and dead-letter handling | medium |
| 0196 | `vending-machine` | Vending Machine | Inventory, coin handling and change making, explicit state machine, refunds | medium |
| 0197 | `library-management` | Library Management | Catalog, members, checkout, holds queue, due dates and fines with explicit timestamps | medium |
| 0198 | `chess-move-validator` | Chess Move Validator | Board model, per-piece move rules, check detection, castling and en passant | hard |
| 0199 | `notification-service` | Notification Service | Channels behind one interface, user preferences, templating, retry and rate limits per channel | medium |

### concurrency (6, owner K1, kind `concurrent`, `problems/`)

Labels: `domains: [backend]`, `job_roles: [backend, platform]` and `scope: function`. Exception: `bank-transfers` also has `fintech`.

| id | slug | title | covers | difficulty | languages |
|----|------|-------|-------|------------|-----------|
| 0200 | `thread-safe-lru-cache` | Thread-Safe LRU Cache | Make a compound structure atomic under concurrent get and put; lock granularity trade-offs | hard | java, kotlin, python, go, rust |
| 0201 | `bounded-blocking-queue` | Bounded Blocking Queue | Fixed-capacity queue with blocking put and take; condition waits with `while` re-checks, no lost wakeups | medium | all |
| 0202 | `bank-transfers` | Bank Transfers | Concurrent transfers between accounts; deadlock avoidance by lock ordering, conservation invariant | medium | java, kotlin, python, go, rust |
| 0203 | `token-bucket-limiter` | Token Bucket Limiter | Thread-safe token bucket with explicit timestamps; atomic check-then-act, exact grant counts | medium | java, kotlin, python, go, rust |
| 0204 | `read-write-lock` | Read-Write Lock | Many readers or one writer; writer preference to avoid starvation | hard | all |
| 0205 | `concurrency-limiter` | Concurrency Limiter | Counting semaphore with at most k holders and FIFO fairness | medium | all |

### debugging (23, kind `function` or `design` with `stub: buggy`, `problems/`)

Labels: `domains: [algorithms]`, `job_roles: [general]` and `scope: function` on the first 16 rows, with no exceptions. `0264` to `0271` carry theirs in their own table.

The eight planned rows (owner B1) port one bug to the languages it exists in; 0240 to 0247 are bugs native to Go and Rust ([ADR 0012](../decisions/0012-go-and-rust.md)).

| id | slug | title | covers | difficulty | languages |
|----|------|-------|-------|------------|-----------|
| 0206 | `debug-binary-search-bounds` | Debug: Binary Search Bounds | Off-by-one loop condition and midpoint update that skip the last element or loop forever | easy | python, typescript, java, kotlin |
| 0207 | `debug-grid-aliasing` | Debug: Grid Aliasing | Rows that share one list and a shallow copy of BFS state, so one write changes many cells | medium | python, typescript, java, kotlin |
| 0208 | `debug-running-total-overflow` | Debug: Running Total Overflow | 32-bit accumulator overflow in a sum of products; the fix is a wider type, not a cast at the end | medium | java, kotlin |
| 0209 | `debug-sort-comparator` | Debug: Leaderboard Comparator | Subtraction comparator that overflows and a tie-break that breaks transitivity | medium | python, typescript, java, kotlin |
| 0210 | `debug-mutable-default-argument` | Debug: Mutable Default Argument | Accumulator default argument that leaks state across calls | easy | python |
| 0211 | `debug-boxed-equality` | Debug: Boxed Integer Equality | Reference comparison of boxed integers that passes small tests and fails above the cache range | medium | java, kotlin |
| 0212 | `debug-recursion-base-case` | Debug: Recursion Base Case | Tree path-sum recursion whose base case treats a null child as a leaf | medium | python, typescript, java, kotlin |
| 0213 | `debug-window-shrink` | Debug: Window Shrink | Sliding window that decrements counts without removing zero entries, so the distinct count is wrong | medium | python, typescript, java, kotlin |
| 0240 | `debug-append-aliasing` | Debug: Append Aliasing | Combinations built with `append` share one backing array, so a later bundle overwrites one already stored | medium | go |
| 0241 | `debug-nil-map-write` | Debug: Nil Map Write | A nested map whose inner map is never made, so the first write to it panics | easy | go |
| 0242 | `debug-shadowed-variable` | Debug: Shadowed Variable | `:=` in an inner block declares a new variable, so the outer discount stays zero | easy | go |
| 0243 | `debug-range-value-copy` | Debug: Range Value Copy | A `range` loop that caps a copy of each struct, so the slice never changes | easy | go |
| 0244 | `debug-unsigned-underflow` | Debug: Unsigned Underflow | A binary search ported from Java whose `usize` bound goes below zero and panics | easy | rust |
| 0245 | `debug-float-ordering` | Debug: Float Ordering | A never-shown creative's rate of `0 / 0` is NaN, and the `partial_cmp(...).unwrap()` sort panics on it | medium | rust |
| 0246 | `debug-char-boundary` | Debug: Char Boundary | Truncation by byte index, which panics inside a multi-byte character | medium | rust |
| 0247 | `debug-clone-mutation` | Debug: Clone Mutation | A clone added to satisfy the borrow checker takes the credit, so transfers credit nobody | medium | rust |

`0264` to `0271`, without `0267`, which is a project under [practical](#practical-80-problems), drill JavaScript traps in small backend code. Each lists TypeScript only, because the bug exists in JavaScript. The labels are columns here.

| id | slug | title | covers | difficulty | languages | domains | job_roles | scope |
|----|------|-------|-------|------------|-----------|---------|-----------|-------|
| 0264 | `debug-sorted-report-rows` | Debug: Sorted Report Rows | `.sort()` compares as strings and sorts in place, and `indexOf` then pairs totals with the wrong regions | medium | typescript | `backend` | `backend` | function |
| 0265 | `debug-pagination-query-strings` | Debug: Pagination Query Strings | Query values are strings, so `+` joins them and `>` compares them as text, while the numeric defaults hide it | medium | typescript | `backend` | `backend` | function |
| 0266 | `debug-invoice-total-cents` | Debug: Invoice Total Cents | Binary floats for money: `19.99 * 100` is not 1999, and rounding the total misses exact half cents | medium | typescript | `backend`, `fintech` | `backend` | function |
| 0268 | `debug-stale-closure-callbacks` | Debug: Stale Closure Callbacks | After-commit callbacks capture variables, not values: a `var` in a loop and `let`s outside it | medium | typescript | `backend` | `backend` | function |
| 0269 | `debug-local-day-boundaries` | Debug: Local Day Boundaries | `new Date("2026-11-05")` is midnight UTC, so a shop's local day opens at the wrong instant | medium | typescript | `backend` | `backend` | function |
| 0270 | `debug-shared-default-config` | Debug: Shared Default Config | A spread is a shallow copy, so one tenant's change reaches the module-level defaults | medium | typescript | `backend` | `backend` | function |
| 0271 | `debug-falsy-plan-update` | Debug: Falsy Plan Update | `\|\|` and a bare `if` eat `0`, `""` and `false`; `??` and an explicit check do not | easy | typescript | `backend` | `backend` | function |

### system-design (10, owner S1, `tracks/system-design/`)

Labels: `domains: [backend]`, `job_roles: [backend, platform]` and `scope: system`. Exception: `payments-ledger` also has `fintech`.

| slug | title | covers | difficulty |
|------|-------|-------|------------|
| `url-shortener` | URL Shortener | Key generation, redirects at read-heavy scale, custom aliases, expiry, analytics | medium |
| `news-feed` | News Feed | Fan-out on write versus read, celebrity accounts, ranking, pagination, cache tiers | hard |
| `chat-system` | Chat System | One-to-one and group messaging, connection gateways, ordering, delivery receipts, offline sync | hard |
| `distributed-rate-limiter` | Distributed Rate Limiter | Token bucket versus sliding window, shared counters, consistency versus latency, failure modes | medium |
| `distributed-kv-store` | Distributed Key-Value Store | Partitioning, replication, quorums, conflict resolution, membership and repair | hard |
| `search-autocomplete` | Search Autocomplete | Prefix index, top-k per prefix, freshness pipeline, latency budget, personalization | medium |
| `video-streaming` | Video Streaming | Upload and transcoding pipeline, adaptive bitrate, CDN strategy, metadata and view counts | hard |
| `payments-ledger` | Payments Ledger | Double-entry model, idempotency keys, exactly-once effects, reconciliation, auditability | hard |
| `metrics-monitoring` | Metrics and Monitoring | Ingestion at high cardinality, time-series storage, downsampling, alert evaluation | hard |
| `ride-hailing` | Ride Hailing | Driver location updates, geospatial matching, trip state machine, surge pricing, consistency | hard |

### code-review (6, owner S1, `tracks/code-review/`)

Labels: `domains: [backend]`, `job_roles: [backend]` and `scope: function`. Exceptions: `review-auth-endpoint` also has `security` and `identity` and the role `security-engineer`, and `review-payment-retry` also has `fintech`.

| slug | title | covers | difficulty |
|------|-------|-------|------------|
| `review-concurrent-counter` | Review: Concurrent Counter Service | Check-then-act race, unsynchronized map, lock held across I/O | medium |
| `review-auth-endpoint` | Review: Login Endpoint | SQL built by concatenation, non-constant-time comparison, secrets in logs, missing rate limit | medium |
| `review-pagination-api` | Review: Pagination API | Offset pagination on a mutating set, breaking response change, inconsistent error shapes | medium |
| `review-payment-retry` | Review: Payment Retry | Swallowed exceptions, non-idempotent retries, unbounded retry loop, missing timeouts | hard |
| `review-report-query` | Review: Report Query | N+1 queries, whole-table load into memory, missing index, quadratic merge | medium |
| `review-flaky-tests` | Review: Flaky Test Suite | Wall-clock and ordering dependence, shared fixtures, mocks that assert nothing | medium |

## Selection notes

The 75 seed problems and the 3 existing problems are all present. The rest were chosen for frequency in senior and staff loops, with one problem per underlying technique where variants exist.

### Departures from the example additions in content

| Example (lc) | Pattern | Replaced by (lc) | Reason |
|--------------|---------|------------------|--------|
| Copy List with Random Pointer (138) | `linked-list` | Sort a Linked List (148) | The type DSL has no random-pointer node, so the problem cannot be expressed in v1 |
| Generate Parentheses (22) | `stack` | moved to `backtracking`; `stack` adds Decode String (394) and Minimum Removals to Balance Parentheses (1249) | It is a backtracking problem; `stack` keeps it as a secondary pattern |
| Longest Word in Dictionary (720) | `tries` | Search Suggestions (1268) | Asked more often; exercises prefix lookup under a typing loop |
| Course Schedule II (210) | `topological-sort` | All Possible Recipes (2115) | Same algorithm as the seed Course Schedule (207); 2115 adds dependency resolution |
| Palindromic Substrings (647), House Robber II (213) | `dp-1d` | Longest Palindromic Substring (5), Stock Trading With Cooldown (309), Minimum Cost for Tickets (983), Job Scheduling for Maximum Profit (1235) | 647 and 5 share one technique, 213 is a wrapper over the seed 198; the additions cover state-machine, calendar and weighted-interval DP |
| Jump Game II (45) | `greedy` | Candy Distribution (135) | 45 repeats the reach argument of the seed 55; 135 adds two-pass greedy |
| Meeting Rooms (252) | `intervals` | Interval List Intersections (986) | 252 is a sub-question of the seed 253 |
| Reverse Bits (190) | `bit-manipulation` | Missing Number (268), Sum Without Arithmetic Operators (371) | 190 repeats the seed 191's bit walk |

### Authoring constraints settled here

| Row | Constraint |
|-----|------------|
| `encode-decode-strings`, `serialize-binary-tree` | `kind: function`. An encoding is implementation-defined and a case cannot feed one op's output into a later op's arguments, so each is one round-trip function (`encodeDecode`, `serializeDeserialize`) that the statement requires to go through a single intermediate string built by separate encode and decode helpers |
| `randomized-set` | Cases call `getRandom` only when the set holds exactly one element, so expected outputs stay deterministic; uniformity is argued in the explanation, not tested |
| Problems with several valid answers (for example `alien-dictionary`, `accounts-merge`) | Use a `checker` comparator, per [problem-format](problem-format.md#comparators) |
| concurrency rows | The `concurrent` schema is deferred to the Phase 5 spec amendment (PRD Q6); rows follow the settled list in [content](content.md) (Phase 5 amendment, ADR 0006) |
