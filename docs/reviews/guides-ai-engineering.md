# Review: the facts of the AI engineering guides

The eleven guides of the path "AI engineering: from your first model call to agent harnesses" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about standards, papers, a security ranking and Python. This page lists each one with where it was checked, so that the independent review starts from the sources.

"Quote" means the exact text was read at that source: on the web page, or in the text extracted from the PDF with `pdftotext`. "Run" means an example of the guide, or a one-off program, printed it, on CPython 3.13.12. "Arithmetic" means the number was computed from the stated inputs. A fact that could not be checked was left out of the guides; the last sections list those, and the citation choices made for the owner's rule against naming companies, products, models and post authors.

| Guide | Slug |
|-------|------|
| Tokens, context windows and sampling | `tokens-and-sampling` |
| Prompts and structured outputs | `prompts-and-structured-outputs` |
| Embeddings and vector search | `embeddings-and-vector-search` |
| Retrieval-augmented generation, end to end | `retrieval-augmented-generation` |
| Evaluating LLM applications | `evaluating-llm-applications` |
| Agents and workflows: ReAct and plan-and-execute | `agents-and-workflows` |
| Tools and the Model Context Protocol | `tools-and-mcp` |
| Agent memory | `agent-memory` |
| Harness engineering | `harness-engineering` |
| Cost: caching, routing and output limits | `cost-caching-and-routing` |
| Security of LLM applications | `llm-application-security` |

## Model Context Protocol

The latest revision is 2026-07-28: [modelcontextprotocol.io/specification/latest](https://modelcontextprotocol.io/specification/latest) serves it and links its schema at `schema/2026-07-28/schema.ts`. Used in `tools-and-mcp`, `harness-engineering`, `cost-caching-and-routing` and `prompts-and-structured-outputs`.

| # | Claim | Source |
|---|-------|--------|
| M1 | The current revision is dated 2026-07-28 | Quote: [specification, latest](https://modelcontextprotocol.io/specification/latest) (schema link and "Learn More" links all at 2026-07-28) |
| M2 | Messages are JSON-RPC 2.0; the roles are hosts (LLM applications that initiate connections), clients (connectors within the host) and servers (services that provide context and capabilities) | Quote: [specification](https://modelcontextprotocol.io/specification/2026-07-28) |
| M3 | Servers offer resources, prompts and tools; resources are context and data for the user or the model, prompts templated messages and workflows for users, tools functions for the model to execute | Quote: specification |
| M4 | Client features are elicitation, sampling and roots, requested by a server within its reply (`InputRequiredResult`, multi round-trip requests); sampling and roots, and the server's logging utility, are deprecated in 2026-07-28 under SEP-2577: a deprecated feature remains part of the specification, new implementations SHOULD NOT adopt it, existing ones SHOULD migrate, and its earliest removal is the first revision released on or after 2027-07-28; roots are informational guidance, not an access-control mechanism | Quote: [base protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic) ("Client Features: Elicitation, sampling and root directory lists"), [architecture](https://modelcontextprotocol.io/specification/2026-07-28/architecture) ("Request client input (sampling, elicitation, roots) via `InputRequiredResult` within a reply"), [deprecated features](https://modelcontextprotocol.io/specification/2026-07-28/deprecated), [roots](https://modelcontextprotocol.io/specification/2026-07-28/client/roots) ("informational guidance rather than an access-control mechanism") |
| M5 | Each client communicates with exactly one server; the host creates clients, enforces security policies and consent, and handles authorization decisions | Quote: architecture |
| M6 | MCP is stateless: every request is self-contained and carries its protocol version and capabilities; servers must not rely on prior requests on the same connection; state that spans requests is referenced by an explicit identifier | Quote: architecture; base protocol, "Statelessness" |
| M7 | Required `_meta` fields on every request: `io.modelcontextprotocol/protocolVersion` and `io.modelcontextprotocol/clientCapabilities`; a request missing one is rejected with `-32602` | Quote: base protocol, "Per-request protocol fields"; run: `mcp_exchange.py` builds and refuses such requests |
| M8 | Earlier revisions established a connection-scoped session with an `initialize` handshake | Quote: [transports](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports), "Backward Compatibility" |
| M9 | Standard transports: stdio, newline-delimited messages over the standard streams of a client-launched subprocess; Streamable HTTP, each message a POST to one endpoint, replies as JSON or a request-scoped SSE stream | Quote: transports |
| M10 | HTTP transports should follow the protocol's authorization framework; stdio should take credentials from the environment | Quote: base protocol, "Auth" |
| M11 | Result responses carry `resultType`, `"complete"` for a finished result | Quote: base protocol; run: `mcp_exchange.py` |
| M12 | Notifications carry no id and get no response | Quote: base protocol; [JSON-RPC 2.0](https://www.jsonrpc.org/specification) ("A Notification is a Request object without an "id" member"; "The Server MUST NOT reply to a Notification") |
| M13 | Tools are model-controlled; there should always be a human in the loop with the ability to deny tool invocations; applications should present confirmation prompts | Quote: [tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools), "User Interaction Model" |
| M14 | A tool has `name`, optional `title`, `description`, `inputSchema` (JSON Schema, default 2020-12, an object, not null), optional `outputSchema` and optional `annotations` | Quote: tools, "Tool" |
| M15 | Tool names should be 1 to 128 characters, case-sensitive, from ASCII letters, digits, `_`, `-` and `.`; unique within a server; aggregating clients should disambiguate, for example by prefixing with a server identifier | Quote: tools, "Tool Names" |
| M16 | Clients must consider tool annotations untrusted unless they come from trusted servers | Quote: tools; specification, "Tool Safety" |
| M17 | `ToolAnnotations` are hints: `readOnlyHint` (default false), `destructiveHint` (default true, meaningful only when not read-only), `idempotentHint` (default false), `openWorldHint` (default true; a web search is open, a memory tool is not) | Quote: [schema.ts, 2026-07-28](https://github.com/modelcontextprotocol/specification/blob/main/schema/2026-07-28/schema.ts), `ToolAnnotations` |
| M18 | Two error mechanisms: protocol errors (unknown tool, malformed requests, server errors) as JSON-RPC errors such as `-32602`; tool execution errors (API failures, input validation errors, business logic errors) as results with `isError: true`; clients should give execution errors to the model so it can self-correct | Quote: tools, "Error Handling"; run: `mcp_exchange.py` |
| M19 | Security considerations: servers must validate inputs, implement access controls, rate limit invocations, sanitize outputs; clients should confirm sensitive operations, show tool inputs to the user before calling, validate results before passing them to the model, implement timeouts and log tool usage | Quote: tools, "Security Considerations" |
| M20 | Servers should return tools in a deterministic order, which improves prompt cache hit rates when tools are included in model context | Quote: tools, "Capabilities" |
| M21 | `tools/list` supports pagination | Quote: tools, "Listing Tools" |
| M22 | A tool may return `structuredContent` conforming to its `outputSchema`, which clients should validate; it is server-produced data, unrelated to LLM structured outputs | Quote: tools, "Structured Content", "Output Schema" |
| M23 | Stateful tools return an explicit handle; for authenticated servers a handle is a name, not a capability, and authorization is checked on every call | Quote: tools, "Stateful Tools" |
| M24 | Implementations must not automatically dereference `$ref` values that resolve to a network URI | Quote: base protocol, "`$ref` Resolution" |
| M25 | MCP takes inspiration from the Language Server Protocol | Quote: specification |
| M26 | Design principle: servers should not be able to read the whole conversation, nor see into other servers; the host controls cross-server interactions | Quote: architecture, "Design Principles" |
| M27 | Security principles: users must explicitly consent to and understand data access and operations; hosts must obtain explicit user consent before invoking any tool; tools represent arbitrary code execution | Quote: specification, "Key Principles" |
| M28 | When no `$schema` is given, schemas default to JSON Schema 2020-12 | Quote: base protocol, "Schema Dialect" |

## OWASP Top 10 for LLM Applications 2026

The current edition is the 2026 one, published by the OWASP GenAI Security Project at [genai.owasp.org/resource/owasp-genai-llm-top-10-2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/) (the page's `datePublished` is 2026-08-04T05:50:36+00:00; the PDF it links, [genai.owasp.org/download/56857](https://genai.owasp.org/download/56857/), is dated "August 4th, 2026" under a "[Publication date to be set]" placeholder, and its revision history lists 1.0 in 2023-08, 1.1 in 2023-10, 2025 in 2024-11 and 2026). At the time of writing, the hub page [genai.owasp.org/llm-top-10](https://genai.owasp.org/llm-top-10/) still lists the 2025 edition. The 2026 PDF was downloaded from the resource page and read in full where cited. Used in every guide from `prompts-and-structured-outputs` on, and above all in `llm-application-security`; every ID outside that guide's table is written with `:2026` and its 2025 number.

| # | Claim | Source |
|---|-------|--------|
| O1 | The ten entries and their order: LLM01 Prompt Injection, LLM02 Sensitive Information Disclosure, LLM03 Excessive Agency, LLM04 Supply Chain, LLM05 Data and Model Poisoning, LLM06 Unbounded Consumption, LLM07 Misinformation, LLM08 Hidden Context Exposure, LLM09 Vector and Embedding Weaknesses, LLM10 Improper Output Handling | Quote: 2026 PDF, table of contents and entry headings |
| O2 | The community vote carries three quarters of the weight, the incident data the remaining quarter; System Prompt Leakage is now Hidden Context Exposure; Excessive Agency climbed to third | Quote: "Letter from the Project Leads", "What's New in the 2026 Top 10" |
| O3 | The list covers the model as a component of an application; once the model acts with tools, memory and downstream consequences, the OWASP Top 10 for Agentic Applications applies alongside | Quote: "What's New" |
| O4 | LLM01: input from any source (direct, retrieved, tool output, multimodal, memory) can alter behaviour; LLMs make no architectural distinction between instructions and data; an injection written to long-term memory taints every later session that reads it | Quote: LLM01 Description |
| O5 | LLM01: no reliable prevention exists today; defense is architectural; some controls reduce success and degrade against adaptive attackers, others bound the blast radius | Quote: LLM01 Prevention, introduction |
| O6 | LLM01 #1: system-prompt constraints are a partial control, bypassable by an attacker who infers the prompt | Quote: LLM01 #1 |
| O7 | LLM01 #2: define a strict output schema and validate every response in trusted application code, using structural validation rather than a second LLM call; a schema-valid response can still carry a malicious value | Quote: LLM01 #2 |
| O8 | LLM01 #3: semantic filters are evadable by rephrasing or encoding | Quote: LLM01 #3 |
| O9 | LLM01 #5: strip tag-block (U+E0000 to E007F), variation-selector (U+FE00 to FE0F) and zero-width (U+200B, U+200C, U+200D, U+2060) characters at every ingest and render boundary; stripping does not stop visible payloads | Quote: LLM01 #5; run: `injection_defenses.py` |
| O10 | LLM01 #7: require explicit human confirmation before privileged, irreversible or externally visible actions, showing the exact rendered action; approval fatigue degrades judgement | Quote: LLM01 #7 |
| O11 | LLM01 #8: treat an agent with untrusted input, sensitive data and state change or external communication together as high risk needing per-action approval; [untrusted input + sensitive data] and [untrusted input + state change] need an explicit residual-risk assessment; removing any one leg removes the conditions | Quote: LLM01 #8 and the paragraph before the list |
| O12 | LLM01 #9: treat memory writes as privileged: log the causing prompt, classify writes for instruction content, require approval before instruction-bearing memories persist across sessions | Quote: LLM01 #9 |
| O13 | LLM02: disclosure surfaces include tool-call arguments, reasoning traces, retrieved chunks, logs, telemetry, embeddings and observable properties such as timing, token length, log-probabilities and cache-hit behaviour | Quote: LLM02 Description |
| O14 | LLM02 Tier 1 #3: authorize before retrieval, inside the index query, not at the application layer after retrieval; #2 minimize context | Quote: LLM02 Prevention |
| O15 | LLM03: root causes excessive functionality, permissions, autonomy; mitigations: minimize tools, minimize tool functionality, avoid open-ended tools (shell, URL fetch) with strict input schemas, minimize permissions, execute in the user's context, require user approval, complete mediation with graduated enforcement (audit, warn, block, escalate; reversible actions auto-approved, irreversible ones to a person); monitoring and rate limiting limit damage | Quote: LLM03 Description and Prevention #1 to #9 |
| O16 | LLM04: supply-chain risks in third-party models, datasets, adapters and conversion pipelines; vet suppliers, scan and patch, keep a signed inventory (SBOM extended to models and datasets) | Quote: LLM04 Description and Prevention #1, #2, #4 |
| O17 | LLM05: poisoning in pre-training, fine-tuning, embeddings and retrieval; track lineage, validate incoming data, filter retrieved content and score sources | Quote: LLM05 Description and Prevention #1 to #3 |
| O18 | LLM06: cost asymmetry, denial of wallet, model cloning; mitigations include token-based limits (per minute, per day), pre-flight token estimation, hard spending caps that halt inference rather than alert, and agentic circuit breakers (step limits, recursion depth limits, time limits, per-run cost ceilings, state hashing to detect loops) | Quote: LLM06 Description, Common Examples #2, Prevention #1, #2, #9 |
| O19 | LLM07: incorrect output that appears credible and is trusted and acted upon; ground claims, claim-check-act, validate tool calls | Quote: LLM07 Description and Prevention #1 to #3 |
| O20 | LLM08: hidden context (system prompt, developer instructions, tool schemas) should be assumed discoverable; put no secrets in it; do not rely on it for authorization; enforce authorization independently of the model | Quote: LLM08 Description and Prevention #1 to #3 |
| O21 | LLM09: cross-tenant leakage via shared similarity search, embedding inversion, retrieval-time poisoning (high success with a handful of poisoned documents, even in corpora of millions), retrieval jamming, semantic cache poisoning around a cosine threshold; enforce tenant scoping inside the index query | Quote: LLM09 Common Examples #1 to #4, #6, Prevention #1 |
| O22 | LLM10: unvalidated output can become XSS, CSRF, SSRF, privilege escalation or remote code execution; renderers that auto-fetch Markdown images enable exfiltration; mitigations: treat the model as a user with zero trust, context-aware output encoding, parameterized queries, strict CSP, sanitize control characters, disable auto-rendering of Markdown images and link previews | Quote: LLM10 Description and Prevention #1, #3 to #6, #8, #9 |
| O23 | The 2025 IDs and their 2026 IDs: LLM01 Prompt Injection stays LLM01; LLM02 Sensitive Information Disclosure stays LLM02; LLM03 Supply Chain becomes LLM04; LLM04 Data and Model Poisoning becomes LLM05; LLM05 Improper Output Handling becomes LLM10; LLM06 Excessive Agency becomes LLM03; LLM07 System Prompt Leakage is replaced by LLM08 Hidden Context Exposure; LLM08 Vector and Embedding Weaknesses becomes LLM09; LLM09 Misinformation becomes LLM07; LLM10 Unbounded Consumption becomes LLM06 | 2025: quote, [hub page](https://genai.owasp.org/llm-top-10/) (entry headings `LLM01:2025` to `LLM10:2025`, fetched 2026-11-12); 2026: quote, [the PDF](https://genai.owasp.org/download/56857/), table of contents and "What's New in the 2026 Top 10" ("What used to be System Prompt Leakage is now Hidden Context Exposure") |

## Papers

Abstracts were read on arXiv; claims beyond an abstract were checked in the paper's text, as marked.

| # | Claim | Source |
|---|-------|--------|
| P1 | BPE for subwords: start from characters plus an end-of-word symbol, repeatedly merge the most frequent pair; vocabulary size is initial plus merges, the merges being the only hyperparameter; no merges across word boundaries; BPE began as a compression method replacing frequent byte pairs; one setup used 59,500 merge operations | Quote: [Sennrich, Haddow and Birch](https://arxiv.org/abs/1508.07909), §3.2 (paper text); run: `bpe_merges.py` |
| P2 | The decoder is auto-regressive, "consuming the previously generated symbols as additional input when generating the next"; self-attention costs O(n² · d) per layer | Quote: [Vaswani and others](https://arxiv.org/abs/1706.03762), §3 and Table 1 (paper text) |
| P3 | Temperature re-estimates the softmax as exp(u/t) / Σ exp(u'/t); t in [0, 1) skews toward high-probability events; nucleus sampling keeps the highest-probability tokens whose cumulative mass exceeds p and rescales; top-k keeps the k most probable; maximization-based decoding such as beam search leads to degeneration, output that is "bland, incoherent, or gets stuck in repetitive loops" (the current version's abstract; v1 said "bland and strangely repetitive"); a fixed k is too small for flat and too large for peaked distributions | Quote: [Holtzman and others](https://arxiv.org/abs/1904.09751), abstract and §3.1 to §3.3 (paper text); run: `sampling.py` |
| P4 | Top-k sampling from the k = 10 most likely candidates | Quote: [Fan, Lewis and Dauphin](https://arxiv.org/abs/1805.04833), generation section (paper text) |
| P5 | Performance is highest with relevant information at the start or end of the input, and degrades in the middle, even for long-context models | Quote: [Liu and others](https://arxiv.org/abs/2307.03172), abstract |
| P6 | The KV cache per request is large and grows and shrinks dynamically; the system shares KV cache within and across requests | Quote: [Kwon and others](https://arxiv.org/abs/2309.06180), abstract |
| P7 | Few-shot: tasks and demonstrations specified purely via text, without gradient updates or fine-tuning | Quote: [Brown and others](https://arxiv.org/abs/2005.14165), abstract |
| P8 | Chain of thought: in sufficiently large language models, demonstrations with intermediate reasoning steps improve arithmetic, commonsense and symbolic reasoning | Quote: [Wei and others](https://arxiv.org/abs/2201.11903), abstract |
| P9 | Guided generation as transitions of a finite-state machine with an index over the vocabulary, for regular expressions and context-free grammars, guaranteeing the structure of the output | Quote: [Willard and Louf](https://arxiv.org/abs/2307.09702), abstract |
| P10 | Continuous word vectors from a 1.6-billion-word corpus in under a day, measuring syntactic and semantic similarity | Quote: [Mikolov and others](https://arxiv.org/abs/1301.3781), abstract |
| P11 | A dual encoder for dense retrieval beats Lucene-BM25 by 9% to 19% absolute in top-20 passage retrieval accuracy; TF-IDF and BM25 were the de facto method | Quote: [Karpukhin and others](https://arxiv.org/abs/2004.04906), abstract |
| P12 | *The Probabilistic Relevance Framework: BM25 and Beyond*, Robertson and Zaragoza, Foundations and Trends in Information Retrieval, 2009 | Crossref record for [10.1561/1500000019](https://doi.org/10.1561/1500000019); the BM25 description in the guide matches the formula of problem `forgettable-inverted-index` |
| P13 | HNSW: a multi-layer structure of proximity graphs for nested subsets of the elements, search starting from the upper layer, logarithmic complexity scaling, approximate search | Quote: [Malkov and Yashunin](https://arxiv.org/abs/1603.09320), abstract |
| P14 | Reciprocal rank fusion: RRFscore(d) = Σ over rankings of 1 / (k + r(d)), with k = 60 fixed during a pilot investigation; the title's claim that it outperforms Condorcet and individual rank learning methods | Quote: [Cormack, Clarke and Büttcher, PDF](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) (paper text); Crossref record for [10.1145/1571941.1572114](https://doi.org/10.1145/1571941.1572114); run: `vector_search.py` |
| P15 | RAG combines a pre-trained seq2seq model (parametric memory) with a dense vector index of Wikipedia, called an online encyclopedia in the guide, read by a neural retriever (non-parametric memory); two formulations, same passages for the whole sequence or different passages per token; both jointly fine-tune the query encoder and the generator, keeping the document encoder and index fixed | Quote: [Lewis and others](https://arxiv.org/abs/2005.11401), abstract and §2.4 (paper text) |
| P16 | Graph RAG: plain RAG fails on global questions; an LLM builds an entity knowledge graph and pregenerates community summaries; partial answers are summarized into a final one | Quote: [Edge and others](https://arxiv.org/abs/2404.16130), abstract |
| P17 | Indirect prompt injection: strategically injecting prompts into data likely to be retrieved lets adversaries exploit LLM-integrated applications remotely, up to data theft and control over which APIs are called; applications blur the line between data and instructions | Quote: [Greshake and others](https://arxiv.org/abs/2302.12173), abstract |
| P18 | LLM judges: position, verbosity and self-enhancement biases and limited reasoning ability (limited grading of math); strong judges reach over 80% agreement with humans, the same as human-human agreement; the conservative fix calls the judge twice with positions swapped and declares a win only when both agree, otherwise a tie | Quote: [Zheng and others](https://arxiv.org/abs/2306.05685), abstract, §3.3 and "Addressing limitations" (paper text); run: `release_gate.py` |
| P19 | F-measure F = (β² + 1) P R / (β² P + R), β the relative importance of recall over precision; β = 2 makes recall twice as important; attributed to van Rijsbergen | Quote: [Chinchor, MUC-4 Evaluation Metrics](https://aclanthology.org/M92-1002.pdf) (paper text) |
| P20 | Cumulated gain with graded relevance; a measure relative to the ideal ranking | Abstract of [Järvelin and Kekäläinen](https://trepo.tuni.fi/handle/10024/65718), via search results, and the Crossref record for [10.1145/582415.582418](https://doi.org/10.1145/582415.582418); the full text was not read |
| P21 | ReAct: reasoning traces and actions interleaved; reasoning helps induce, track and update plans and handle exceptions; reduces hallucination and error propagation on HotpotQA and Fever; beats imitation and reinforcement learning by 34 and 10 absolute points on ALFWorld and WebShop with one or two examples | Quote: [Yao and others](https://arxiv.org/abs/2210.03629), abstract |
| P22 | ReAct capped runs at 7 steps on HotpotQA, a question-answering benchmark, and 5 on FEVER, a fact-verification benchmark, finding that more steps did not improve performance | Quote: Yao and others, §3.2 and footnote 3 (paper text) |
| P23 | Plan-and-Solve: devise a plan dividing the task into subtasks, then carry them out; zero-shot CoT pitfalls are calculation, missing-step and semantic misunderstanding errors; PS addresses missing steps | Quote: [Wang and others](https://arxiv.org/abs/2305.04091), abstract |
| P24 | ReWOO: Planner, Worker and Solver; the planner writes interdependent plans with evidence placeholders (#E) before any tool response; 5× token efficiency and 4% accuracy improvement on HotpotQA; robustness under tool failure; a solver told to use evidence "with caution" partially compensates for planner or worker failures | Quote: [Xu and others](https://arxiv.org/abs/2305.18323), abstract, Figure 1 caption and §2 (paper text) |
| P25 | Reflexion: agents verbally reflect on task feedback and keep reflective text in an episodic memory buffer for later trials, without weight updates | Quote: [Shinn and others](https://arxiv.org/abs/2303.11366), abstract |
| P26 | CoALA: short-term working memory and long-term episodic, semantic and procedural memory; working memory is a data structure persisting across LLM calls for the current decision cycle; procedural memory is implicit in weights and explicit in code; writing to procedural memory is significantly riskier | Quote: [Sumers, Yao, Narasimhan and Griffiths](https://arxiv.org/abs/2309.02427), §4.1 (paper text); published in TMLR 02/2024 |
| P27 | Generative agents: a complete record of experiences in natural language, reflections, retrieval to plan; recency as exponential decay with factor 0.995 per sandbox hour since last retrieval, importance rated 1 to 10 by the model at creation, relevance as cosine similarity; each min-max scaled to [0, 1] and weighted 1; top memories that fit the context window are included | Quote: [Park and others](https://arxiv.org/abs/2304.03442), abstract and §4.1 (paper text); run: `long_term.py` |
| P28 | Recursive summarization: memorize small dialogue contexts, then recursively produce new memory from previous memory and following contexts | Quote: [Wang and others](https://arxiv.org/abs/2308.15022), abstract |
| P29 | Virtual context management inspired by OS paging; a memory pressure warning at a warning token count (e.g. 70% of the window); at the flush count (e.g. 100%) evict messages (e.g. 50% of the window) and write a new recursive summary from the old one and the evicted messages | Quote: [Packer and others](https://arxiv.org/abs/2310.08560), abstract and §2.2 (paper text) |
| P30 | LLMs struggle to self-correct reasoning without external feedback, and performance can degrade after self-correction | Quote: [Huang and others](https://arxiv.org/abs/2310.01798), abstract |
| P31 | Two phases of inference: compute-intensive prompt computation and memory-intensive token generation; splitting them across machines | Quote: [Patel and others](https://arxiv.org/abs/2311.18677), abstract |
| P32 | Prompt Cache reuses precomputed attention states of frequent segments (system messages, templates, documents), with positional accuracy; time-to-first-token improves 8× on GPU to 60× on CPU, accuracy maintained | Quote: [Gim and others](https://arxiv.org/abs/2311.04934), abstract |
| P33 | Three cost strategies (prompt adaptation, LLM approximation, LLM cascade); the cascade matches the best individual LLM with up to 98% cost reduction | Quote: [Chen, Zaharia and Zou](https://arxiv.org/abs/2305.05176), abstract |
| P34 | Routers between a stronger and a weaker model trained on human preference data reduce cost by over 2 times in certain cases without compromising quality, and transfer when the models change | Quote: [Ong and others](https://arxiv.org/abs/2406.18665), abstract |

## Other standards

| # | Claim | Source |
|---|-------|--------|
| S1 | Names within a JSON object SHOULD be unique; with repeated names behaviour is unpredictable, and many implementations report the last pair; Infinity and NaN are not permitted | Quote: [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259.html) §4, §6 |
| S2 | The current JSON Schema version is 2020-12, in two documents, Core and Validation | Quote: [json-schema.org/specification](https://json-schema.org/specification) |
| S3 | Server-sent events: MIME type `text/event-stream`; a `data:` line appends to the data buffer; a blank line dispatches the event; a line starting with a colon is ignored | Quote: [HTML Living Standard, server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html) |
| S4 | The Tags block is U+E0000 to U+E007F; U+E0041 is TAG LATIN CAPITAL LETTER A, mirroring ASCII `A` | Quote: [Unicode 18.0 code chart, Tags](https://www.unicode.org/charts/PDF/UE0000.pdf) (chart text); that tag characters are invisible in normal rendering: O9 |
| S5 | JSON-RPC 2.0 error code -32602 is "Invalid params" | Quote: [JSON-RPC 2.0](https://www.jsonrpc.org/specification) |

## Python

| # | Claim | Source |
|---|-------|--------|
| Y1 | `json`: repeated names keep the last value by default; `NaN`, `Infinity` and `-Infinity` are accepted and output by default; `parse_constant` can raise on them; `object_pairs_hook` changes repeated-name handling; `JSONDecodeError` subclasses `ValueError` | Quote: [json](https://docs.python.org/3/library/json.html); run: `structured_output.py` |
| Y2 | `json.dumps`: `sort_keys` sorts keys; `separators=(",", ":")` gives the most compact JSON | Quote: json; run: `caching.py` |
| Y3 | `bool` is a subclass of `int` | Quote: [built-in types, bool](https://docs.python.org/3/library/stdtypes.html#boolean-type-bool) |
| Y4 | `html.escape` converts `&`, `<` and `>`, and with `quote=True`, the default, `"` and `'` | Quote: [html](https://docs.python.org/3/library/html.html); run: `injection_defenses.py` |
| Y5 | `hashlib.sha256` is always present and gives a 32-byte digest | As in [the hashing guides' review](guides-hashing.md), P13; run: `caching.py` |

## The examples and the arithmetic

| # | Claim | Source |
|---|-------|--------|
| E1 | BPE on the toy corpus: `play` after 3 merges, `ing_` after 7; `playing` 2 tokens, `replayed` 5, `zebra` 6 | Run: `bpe_merges.py` |
| E2 | Softmax of the five logits at temperatures 0.5, 1 and 2; top-k 2 and top-p 0.9 sets; the kept top-p mass 0.954 | Run: `sampling.py`; arithmetic: 0.525 + 0.236 + 0.193 |
| E3 | Python's `json.loads` alone keeps priority 1 for `{"priority": 3, "priority": 1}` and accepts `NaN` | Run: `structured_output.py` |
| E4 | `refund payment` against `money back for a purchase`: cosine 0.982, equal to the dot product of the unit vectors | Run: `vector_search.py` |
| E5 | A million 1,024-dimensional vectors of 4-byte floats take 4,096,000,000 bytes, about 4.1 GB | Arithmetic |
| E6 | The vacation question retrieves the carry-over chunk (1.0) above the allowance (0.98); the off-topic question retrieves nothing; 2 model calls for 3 questions | Run: `rag_pipeline.py` |
| E7 | One standard error of a pass rate: about 15 points at 8 cases and 75%, 12 at 87.5%, about 2.5 at 200 cases and 85% | Arithmetic: sqrt(p (1 - p) / n); run: `release_gate.py` |
| E8 | ReAct makes 4 model calls, plan-and-execute 2, the workflow 1; the stuck run stops at 3 steps | Run: `agent_patterns.py` |
| E9 | 0.995 to the 200th power is about 0.37 | Arithmetic: e^(200 ln 0.995) = e^(-1.0025) |
| E10 | Buffer and rolling summary both 31 tokens; only the summary keeps the allergy | Run: `short_term.py` |
| E11 | Permission decisions for nine proposed actions | Run: `permission_gate.py` |
| E12 | The finishing run: a failed completion check at step 4, compaction of 4 entries after step 5, success at step 6 | Run: `harness_loop.py` |
| E13 | Stable prompt layout shares 171 of 178 tokens, unstable 1 of 177; the replacement question scores 0.63 and is a false hit at 0.6 | Run: `caching.py` |
| E14 | The cascade costs 44% of large-only, a perfect router 42%; the large model costs 15× per prompt token and 18.75× per completion token; an output limit of 200 cuts 3 answers and about 15% of the cost; a cascade wins when the escalation rate is below 1 - small / large | Run: `routing.py`; arithmetic |
| E15 | The hidden document is 90 characters and shows 45 | Run: `injection_defenses.py` |

## The harness engineering article

The owner shared *Harness engineering: leveraging Codex in an agent-first world*, published on OpenAI's site ([openai.com/index/harness-engineering](https://openai.com/index/harness-engineering/)), as a source for `harness-engineering`. The article itself could not be read: WebFetch got HTTP 403 for the URL and its `/en/` variant, and the web archive could not be fetched. It is not cited in the guide: after the independent review, its Further reading line was removed, and the guide states the ideas below as its own advice, without attribution. What was checked, against two secondary sources that were read:

- [InfoQ news, *OpenAI Introduces Harness Engineering: Codex Agents Power Large-Scale Software Development*, by Leela Kumili, 21 February 2026](https://www.infoq.com/news/2026/02/openai-harness-engineering-codex): human engineers shift "from implementing code to designing environments, specifying intent, and providing structured feedback"; a structured docs directory of "maps, execution plans, and design specifications" serves as "the single source of truth for agents"; architecture documentation is "mechanically enforced with linters and CI validation" and structural tests check modular layering; agents use telemetry (logs, metrics, spans) to monitor performance and reproduce bugs.
- [*Harness Engineering - first thoughts*, by Birgitta Böckeler, 17 February 2026, in the "Exploring Gen AI" series on martinfowler.com](https://www.martinfowler.com/articles/exploring-gen-ai/harness-engineering-memo.html): names the article and calls it recent; describes the harness as context engineering ("continuously enhanced knowledge base in the codebase"), architectural constraints ("deterministic custom linters and structural tests") and garbage collection ("agents that run periodically to find inconsistencies in documentation or violations of architectural constraints"); quotes the article: "When the agent struggles, we treat it as a signal: identify what is missing — tools, guardrails, documentation"; and its "no manually typed code" for five months.

| # | Claim in the guide | Source |
|---|-------|--------|
| H1 | The people's work around an agent: specifying intent, shaping the environment and giving structured feedback, with rules enforced by tools rather than reminders | InfoQ; the memo |
| H2 | Knowledge kept in the repository as structured documents serving as the agents' source of truth | InfoQ |
| H3 | Architectural rules enforced by linters, structural tests and continuous integration | InfoQ; the memo |
| H4 | Telemetry the agents read to reproduce and diagnose problems | InfoQ |
| H5 | Agents that run periodically to find drifted documentation or broken rules | The memo |
| H6 | When an agent struggles, the gap signals what the environment is missing: a tool, a guardrail or a document | The memo, quoting the article |

Not verified, so not in the guide: the article's exact publication date (secondary coverage gives 2026-02-11 or March 2026; the sources read only show it existed by 17 February 2026), its author, and the idea of a short instructions file used as a map with pointers to deeper documents, which neither source read describes (a search engine's summary did; that was not counted as reading it).

## Citations and the rule against names

The guides name no company, product, vendor, model or post author in their prose. Choices made at the edges:

| Where | Choice |
|-------|--------|
| Paper titles that contain a system or product name | Cited by a shortened title: Packer and others as *Towards LLMs as Operating Systems* (full title *MemGPT: Towards LLMs as Operating Systems*), Zheng and others as *Judging LLM-as-a-Judge* (full title adds *with MT-Bench and Chatbot Arena*), Chen, Zaharia and Zou as *How to Use Large Language Models While Reducing Cost and Improving Performance* (full title starts *FrugalGPT:*), each marked "title shortened" in the guide. Only titles that carry a model or product brand are shortened: Ong and others keep their full title, *RouteLLM: Learning to Route LLMs with Preference Data*, as does *Splitwise* |
| Method names from papers | Kept as the papers name them: ReAct, ReWOO, Reflexion, Prompt Cache, PagedAttention (in a title), HNSW, BM25, Graph RAG |
| Benchmarks | HotpotQA, Fever, ALFWorld and WebShop are named only where a paper's result is reported, in `agents-and-workflows` |
| The harness engineering article | Not cited in the guide, since its title and URL name a product and a company and it was never read; recorded here only |
| Python | Named, as the language of the examples, with its official documentation |

## Practice links to problems not yet merged

At the main session's direction, the guides and the path reference seven problems written on another branch, by the slugs of their folders: `loop-controller` (0323), `tool-permission-gate` (0324), `context-compaction` (0325), `cache-and-router` (0326), `eval-release-gate` (0327), `sql-guard` (0328) and `plan-and-execute` (0329). Their statements were not available, so their practice lines describe them only from their names, and the guides' examples could not be checked against their solutions for spoilers. Both need a look once they are merged, along with each problem's `guides:` list in its `meta.yaml`.

## Independent accuracy review (2026-11-12)

An independent read-only review checked every claim of this page against its source and ran the fifteen examples. It confirmed the headline claims: the Model Context Protocol's current revision, 2026-07-28, with its statelessness, `_meta` on every request and no `initialize` handshake; the numbering of the 2026 OWASP list; and the output of all fifteen examples. These are its findings and what changed.

| # | Finding | Change |
|---|---------|--------|
| 1 | Wrong: sampling and roots are deprecated in 2026-07-28 (SEP-2577), and roots are a hint, not a permission | `tools-and-mcp` names elicitation as the client feature, and says the revision still defines sampling and roots but deprecates both; M4 updated |
| 2 | The harness article's Further reading line names a product and a company, and the article was never read | Line removed; the two sentences that attributed its ideas to "practitioners" and "published accounts" now state them as the guide's own advice; the section above records what was checked |
| 3 | Wrong: both of Lewis and others' formulations fine-tune the query encoder and the generator together | `retrieval-augmented-generation` says so, and describes its own design as the now-common variant with a retriever and a model that is not retrained; P15 updated |
| 4 | Wrong: FEVER is fact verification, not question answering | `agents-and-workflows` and `harness-engineering` say "question-answering and fact-verification benchmarks"; P22 updated |
| 5 | "bland and strangely repetitive" is from the paper's first arXiv version only | `tokens-and-sampling` quotes the current abstract, "bland, incoherent, or gets stuck in repetitive loops"; P3 updated |
| 6 | Constrained decoding cannot guarantee a well-formed reply that the output limit cuts short | `prompts-and-structured-outputs` adds "unless the output limit cuts it short, so still check why generation stopped", twice |
| 7 | Prompt caching may need enabling, and cache writes may be priced above reads | `cost-caching-and-routing` says so, hedged with "depending on the provider" and "may"; this is the reviewer's caution, not a sourced fact |
| 8 | The quadratic term is not the only reason for limits | "one reason long contexts are expensive and windows are limited" |
| 9 | Working memory was described too narrowly | The table's cell reads "State kept for the current decision, from which each call's context is built", and the diagram's node "working memory → this call's context" |
| 10 | Chain of thought helps sufficiently large models | Added in `prompts-and-structured-outputs`, twice; P8 updated |
| 11 | "Most production search uses both" is unsourced | "Many search systems use both and fuse them" |
| 12 | Tokenizing in O(L) with a table is not established | "Roughly linear in `L` in practice" |
| 13 | Embedding models take inputs only up to a limit | "however long, up to the model's input limit" |
| 14 | The hub page shows the 2025 edition | The hub link in `llm-application-security` says so |
| 15 | Spoilers: the tools example validated arguments like the tool-calling problem; the harness example's repeat key; a practice line restating that problem's level 3 rules | `mcp_exchange.py` checks only the required keys and the guide says a real server uses a JSON Schema validator; `harness_loop.py` counts repeats by `(tool, arg)`; the practice line says only that level 3 treats tool output as untrusted data |
| 16 | `injection_defenses.py` held a literal invisible character | Written as the escape `\u200b`, in the file and the guide |
| 17 | The permission gate's path check is lexical | The guide says so, and that a real gate resolves symlinks first |
| 18 | `vector_search.py` dropped every score of 0 or less, not only zero vectors | It now skips zero vectors only and keeps every other score; the output is unchanged |
| 19 | Jargon in guides that start from little background | `tokens-and-sampling` defines transformer, layer, self-attention, key and value where they first appear; `llm-application-security` spells out cross-site scripting and server-side request forgery; `evaluating-llm-applications` defines a standard error before the example prints it, and words precision and recall as shares |
| 20 | The ReAct diagram's text drawing put a "yes" label on the answer box | The step is drawn as a straight sequence of five boxes |
| 21 | Shortened titles were not marked, and RouteLLM's carries no model brand | "title shortened" added to the three shortened titles; RouteLLM's full title restored |

Left for the integrator: `permission_gate.py` and `harness_loop.py` are unchanged apart from fix 15, and should be checked for spoilers against `loop-controller`, `tool-permission-gate` and `context-compaction` once those problems land.
