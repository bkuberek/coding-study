# Review: the facts of the infrastructure as code guides

The five guides of the path "Infrastructure as code: from desired state to plans, drift and policy checks" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about a paper on convergence, open specifications (RFC 9110, RFC 6902, RFC 7396, RFC 8259, RFC 6901, JSON Schema draft 2020-12, YAML 1.2.2 and the YAML 1.1 boolean type) and Python's standard library. This page lists each one with where it was checked, so that the independent review starts from the sources.

"Quote" means the exact text was read at that source: in the plain text of the RFC, in the HTML of the page converted to text, or in the text extracted from the PDF with `pdftotext`. "Run" means an example of the guide printed it, on CPython 3.13.12. "Arithmetic" means the number was computed from the stated inputs. Bibliographic data of the paper was checked against its Crossref record. A fact that could not be checked is not in the guides; the last sections list those, the names used, and where a guide comes close to a linked problem.

The guides describe plans, state, drift, references, layered values and policies in their own words, without a source: no open standard defines them, and the guides cite no product's documentation.

| Guide | Slug |
|-------|------|
| Declarative desired state and convergence | `declarative-desired-state` |
| Plan, diff and apply | `plan-and-apply` |
| Resource graphs and dependency order | `resource-dependency-graphs` |
| State, drift and reconciliation | `state-and-drift` |
| Layered values, templates and policy checks | `templates-and-layered-values` |

## Convergence

A. Couch and Y. Sun, *On the Algebraic Structure of Convergence*, Self-Managing Distributed Systems, Lecture Notes in Computer Science, Springer, 2003, pages 28 to 40, [doi:10.1007/978-3-540-39671-0_4](https://doi.org/10.1007/978-3-540-39671-0_4), read from [the author copy](https://www.cs.tufts.edu/~couch/publications/dsom-03.pdf). Used in `declarative-desired-state`.

| # | Claim | Source |
|---|-------|--------|
| C1 | Three approaches to automated configuration: imperative, a series of commands applied to a system in a known initial state, where the order of operations always matters; convergent, a set of known states to assure in an otherwise unknown system; generative, regenerating individual configurations from an overarching rule set rather than making incremental changes | Quote: §1 |
| C2 | An action `p` is idempotent if repeating it has the same effect as doing it once, `p ∘ p ≈ p`; a set of actions each of which is idempotent is weakly convergent (Definition 3); "This is the definition of convergence that controls actions in many common configuration management tools" | Quote: §4 |
| C3 | Proposition 1: there are idempotent actions `p` and `q` whose composition is not idempotent; with `p` "if (x==1) then y=2" and `q` "x=1" from the baseline `x = y = 0`, the composition sets `x` the first time and `y` the second; started from `x = y = 1` it is idempotent; idempotence and convergence are only meaningful relative to a baseline state; the cause is that `p` is stateful | Quote: §4, Proposition 1 and the text after its proof |
| C4 | Stateless: `p ∘ q ∘ p ≈ p ∘ q` for any action `p` and any sequence `q` (Definition 6); convergent: idempotent and stateless (Definition 7); under that equivalence every element of the semigroup of sequences is idempotent (Lemma 3) | Quote: §4 and §5 |

## HTTP

[RFC 9110, *HTTP Semantics*](https://www.rfc-editor.org/rfc/rfc9110), plain text. Used in `declarative-desired-state`.

| # | Claim | Source |
|---|-------|--------|
| H1 | A request method is idempotent if the intended effect on the server of multiple identical requests is the same as the effect of a single one; the property applies only to what the user requested, and a server is free to log each request separately | Quote: §9.2.2 |

## JSON Patch, JSON Merge Patch, JSON and JSON Pointer

The RFCs as plain text from rfc-editor.org. Used in `plan-and-apply`, `state-and-drift` and `templates-and-layered-values`.

| # | Claim | Source |
|---|-------|--------|
| P1 | A JSON Patch operation's `op` is one of `add`, `remove`, `replace`, `move`, `copy` and `test`, and its `path` is a JSON Pointer to the target location; operations are applied sequentially in the order they appear, each to the result of the one before, until all succeed or an error occurs | Quote: [RFC 6902](https://www.rfc-editor.org/rfc/rfc6902), §3 and §4 |
| P2 | `test` checks that the value at the target location equals a given value | Quote: RFC 6902, §4.6 |
| P3 | If an operation is not successful, evaluation should terminate and the entire patch is not deemed successful | Quote: RFC 6902, §5 |
| M1 | MergePatch: if the patch is an object, a target that is not an object becomes `{}`; each member whose value is `null` removes that name from the target, and every other member is merged recursively; a patch that is not an object replaces the whole target; it is not possible to patch only some of the values in an array | Quote: [RFC 7396](https://www.rfc-editor.org/rfc/rfc7396), §2 |
| M2 | Merge patch documents describe changes "by example"; the design suits documents that primarily use objects for their structure and do not make use of explicit null values | Quote: RFC 7396, §1 and §2 |
| M3 | `{"a":["b"]}` patched with `{"a":"c"}` gives `{"a":"c"}`; `{"e":null}` patched with `{"a":1}` gives `{"e":null,"a":1}` | Quote: RFC 7396, Appendix A |
| J1 | An object is an unordered collection of zero or more name/value pairs; an array is an ordered sequence of zero or more values | Quote: [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259), §1 |
| J2 | JSON parsing libraries have been observed to differ as to whether they make the ordering of object members visible to calling software | Quote: RFC 8259, §4 |
| R1 | A JSON Pointer is a sequence of zero or more reference tokens, each prefixed by `/`; `~` is encoded as `~0` and `/` as `~1` in a reference token | Quote: [RFC 6901](https://www.rfc-editor.org/rfc/rfc6901), §3 |

## JSON Schema

[JSON Schema Validation, draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-validation) and [JSON Schema Core, draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-core), as served at json-schema.org. Used in `templates-and-layered-values`.

| # | Claim | Source |
|---|-------|--------|
| S1 | `type` names one of six primitive types, `null`, `boolean`, `object`, `array`, `number` and `string`, or `integer`, which matches any number with a zero fractional part | Quote: Validation, §6.1.1 |
| S2 | An object instance is valid against `required` if every item in the array is the name of a property in the instance | Quote: Validation, §6.5.3 |
| S3 | `minimum` is an inclusive lower limit | Quote: Validation, §6.2.4 |
| S4 | `additionalProperties` applies only to the child values of instance names that do not appear in the annotation results of `properties` and `patternProperties` | Quote: Core, §10.3.2.3 |
| S5 | `default` belongs to the meta-data vocabulary, general-purpose annotation keywords for documentation and user interface display; there are no restrictions on its value, and it is recommended that it be valid against the associated schema | Quote: Validation, §9 and §9.2 |

## YAML

[YAML 1.2.2](https://yaml.org/spec/1.2.2/) and [the YAML 1.1 boolean type](https://yaml.org/type/bool.html), as served at yaml.org. Used in `templates-and-layered-values`.

| # | Claim | Source |
|---|-------|--------|
| Y1 | The YAML 1.2 specification was published in 2009; its primary focus was making YAML a strict superset of JSON, and it removed many of the problematic implicit typing recommendations; YAML 1.2.2 was published in October 2021 | Quote: 1.2.2, the history in its introduction |
| Y2 | The core schema is the recommended default schema; plain scalars are matched against a list of regular expressions, for null, booleans (`true`, `True`, `TRUE`, `false`, `False`, `FALSE`), integers in base 10, 8 (`0o`) and 16 (`0x`) and floats, and resolve to a string when none matches; the table also has rows for infinity and not-a-number | Quote: 1.2.2, §10.3 and §10.3.2, the table copied into `scalars.py` except its infinity and not-a-number rows |
| Y3 | The YAML 1.1 boolean type, a working draft of 2005-01-18, matches `yes`, `no`, `on` and `off` in lower-case, capitalized and upper-case forms, the single letters `y`, `Y`, `n`, `N`, and the true and false forms | Quote: the 1.1 boolean type page, its regular expression copied into `scalars.py` |

## Python

The documentation as served at docs.python.org/3, version 3.15.2 at the time of reading. A version named in a guide is the version the documentation gives for the feature.

| # | Claim | Source |
|---|-------|--------|
| Py1 | `graphlib.TopologicalSorter` (3.9) takes a mapping from each node to its predecessors; `prepare()` marks the graph as finished and raises `CycleError` on a cycle; `get_ready()` returns every node whose predecessors are all processed; `done()` marks nodes as processed; `static_order()` can depend on the order of insertion | Quote: [`graphlib`](https://docs.python.org/3/library/graphlib.html); run: `resource_graph.py` |
| Py2 | When several cycles exist, `CycleError` reports one, an undefined choice, as the second element of `args`: a list in which each node is an immediate predecessor of the next, with the first and last the same | Quote: `graphlib`, `CycleError`; run: `resource_graph.py` |
| Py3 | `collections.ChainMap` (3.3): lookups search the underlying mappings successively until a key is found; writes, updates and deletions operate only on the first mapping | Quote: [`collections`](https://docs.python.org/3/library/collections.html#collections.ChainMap); run: `layers.py` |
| Py4 | `string.Template.substitute` raises `KeyError` for a missing placeholder; `safe_substitute` leaves it intact, and "may be anything other than safe, since it will silently ignore malformed templates" | Quote: [`string`](https://docs.python.org/3/library/string.html#template-strings-strings); run: `layers.py` |
| Py5 | `json.dumps` with `sort_keys=True` outputs dictionaries sorted by key, and `separators=(',', ':')` gives the most compact form | Quote: [`json`](https://docs.python.org/3/library/json.html); run: `plan_apply.py` |
| Py6 | `hashlib.sha256` and `hexdigest` | Quote: [`hashlib`](https://docs.python.org/3/library/hashlib.html); run: `plan_apply.py` |

## The examples and the arithmetic

| # | Claim | Source |
|---|-------|--------|
| E1 | Appending reports `changed` on both runs and leaves the hosts line twice; the checking task reports `changed` then `ok`; `p` and `q` are each idempotent alone, and `p` then `q` changes something on runs 1 and 2 and nothing on run 3 | Run: `converge.py` |
| E2 | The first plan creates the bucket, replaces the disk because of `zone`, deletes `server/old` and updates `server/web`; the plan after the apply is all no-ops; the third plan is refused after the hand-made resize | Run: `plan_apply.py` |
| E3 | Four waves: the bucket and the network; the firewall and both subnets; the server; the DNS record; deletes in reverse; the added reference makes a cycle through `network/main` and `subnet/b`, the only cycle it creates | Run: `resource_graph.py` |
| E4 | Grouped by verdict: `b-12` unmanaged, `volume/cache` (`vol-b`) deleted outside the tool, `vm/build.memory_gb` conflict, `vm/docs.cpus` drift, `vm/docs.image` pending, `vm/build.cpus` stale record | Run: `three_way.py` |
| E5 | `replicas` 3 from production, `port` 8080 from the defaults, `image` reduced to the production tag; `substitute` raises `KeyError` for `repo`, `safe_substitute` leaves `$repo` | Run: `layers.py` |
| E6 | Under the core schema, `no`, `on` and `web-1` are strings, `1.10` and `12e3` floats, `007` and `0x1A` integers, `true` a boolean; under the 1.1 boolean type, `no`, `on` and `true` are booleans | Run: `scalars.py`, checked by hand against the tables of Y2 and Y3 |
| E7 | `1.10` is the number 1.1, `007` is 7, `0x1A` is 26, `12e3` is 12,000 | Arithmetic |
| E8 | The number of waves equals the number of resources on the longest chain of dependencies, network, subnet, server and DNS record: four | Arithmetic: a node's wave is one more than the largest wave of its predecessors |

## Citations and names

The guides name no company and no product. Where they name something, it is a paper cited by its authors, an open specification (an RFC, JSON Schema, YAML), or Python's standard library, the language of the examples.

| Not named in the guides | Where it appears in a source |
|----------|------------------------------|
| The names of the configuration tools given as examples of the imperative, convergent and generative approaches | Couch and Sun, §1 |
| The file permission command given as an example of a convergent action that is not stateless | Couch and Sun, §4 |
| The infrastructure tools, configuration tools and container orchestrator whose documentation the linked problems' explanations cite | The explanations of `iac-plan-engine`, `drift-detection`, `idempotent-converge` and `values-templating` |

## Not verified

- The volume number of the Couch and Sun proceedings is not in its Crossref record, and the publisher's page and dblp refused the request; the guide cites the series, the book title, the year and the pages that Crossref gives.
- No open specification defines a plan, a state file, drift, an import or a reconciliation policy. The guides describe them as concepts in their own words and attribute nothing to a source.
- A. B. Kahn's 1962 paper on topological sorting was not read for this path; the dependency guide links the catalog's guide on topological order instead of citing it.
- The YAML 1.1 integer and float types were not checked, so the second templating example states only what the 1.1 boolean type matches.
- Whether validators fill in a schema's `default` is not stated: the specification read describes it only as an annotation.
- The mapping study of infrastructure as code research by Rahman, Mahdavi-Hezaveh and Williams (2019), which the policy problem's explanation cites, could not be read; no definition of infrastructure as code is attributed to it.

## Practice links and back-links

The path's problems are on main. Their `meta.yaml` gained these `guides:` entries, after `related:`:

| Problem | `guides:` |
|---------|-----------|
| 0342 `idempotent-converge` | `[declarative-desired-state]` |
| 0340 `iac-plan-engine` | `[plan-and-apply, resource-dependency-graphs]` |
| 0341 `drift-detection` | `[state-and-drift]` |
| 0343 `values-templating` | `[templates-and-layered-values]` |
| 0344 `manifest-policy` | `[templates-and-layered-values]` |

The path takes `iac-plan-engine` twice: level 1, the diff, after the plan guide, and all four levels after the guide on dependencies.

## Where a guide comes close to a linked problem

Each linked problem's statement, hints, solutions and follow-ups are compared with the guides. Each guide teaches its idea with examples of its own; these are the places the review should weigh against the rule that a guide never gives away a linked problem's solution:

| Problem | Guide | Overlap the guide states | Not in the guide |
|---------|-------|--------------------------|-----------|
| `idempotent-converge` levels 1 and 2 | declarative-desired-state | Tasks that compare before changing and report `ok` or `changed`; a second run that reports `ok`; a dry run that reports what would change with old and new values, as the statement describes | Files, packages and services and their rules, copies of hosts for a check run, the diff rows |
| `idempotent-converge` level 3 | declarative-desired-state | Running an action only after another task reported a change, such as a restart after a configuration change, which the statement introduces as a handler | Handler order, at most once per host, failures that stop a host and drop its handlers |
| `idempotent-converge` follow-up 4 | declarative-desired-state | Couch and Sun's composition: a conditional step that reads state a later step changes needs a second run; this touches the follow-up in general | Facts, conditions on facts, and what breaks in the problem when a task changes a fact |
| `iac-plan-engine` level 1 | plan-and-apply | The action table, create, delete, no-op and update, and attribute diffs with old and new values, which the statement gives; the example classifies and diffs resources in its own format | The `+`, `-` and `~` rows, deletes last, and the order of steps |
| `iac-plan-engine` level 2 | resource-dependency-graphs | References as dependencies; creates in a topological order and deletes in reverse; a cycle detected with `graphlib`; waves | The reference syntax and chains of references, unknown references, cycle groups, the before-rules, and placing the smallest ready step by rank and address |
| `iac-plan-engine` level 3 | plan-and-apply, resource-dependency-graphs | Replacement when an attribute that cannot change in place changes, naming the attribute; values unknown until a resource exists, treated as differing from every value; a replacement that ripples to what refers to it; delete-first against create-first, and dependents moving to the new object before the old one goes, all as the statement describes | Computed keys and how a reference to one resolves, the `forces-replacement` tag, the mark and how it spreads to dependencies, and rules 3 and 4 |
| `iac-plan-engine` level 4 | plan-and-apply, resource-dependency-graphs | After a partial failure, a tool that records each success can plan again and the new plan holds what is left; a failed step blocks what depends on it while the rest carries on | How outcomes propagate through the before-rules, recorded links, old objects and rule 5 |
| `iac-plan-engine` follow-ups 1 to 3 | state-and-drift, resource-dependency-graphs | Refresh defined as reading every managed resource before planning; waves show what could run side by side; create-first avoids the gap of delete-first | What a refresh adds and can no longer promise; limiting calls in flight and what a failure does to running steps; which resources cannot be replaced create-first, and why |
| `drift-detection` level 1 | state-and-drift | Matching the record to the scan by identifier, never by name; deleted, changed and unmanaged resources, as the statement describes. The example uses resources, identifiers and attributes of its own, adds a third version, the description, to classify each attribute, and prints its findings grouped by verdict, unmanaged first | The report's rows, their order, and `""` for a missing key |
| `drift-detection` level 2 | state-and-drift | False alarms from attributes that change on their own, lists in another order and defaults the provider fills in; a rule that hides a difference also hides real drift, which is the risk follow-up 4 names | Star patterns and how they match, `unordered` and `defaultValue`, which rules can hide a deleted or unmanaged resource |
| `drift-detection` level 3 | state-and-drift | Import defined; an imported resource the description does not mention is deleted by the next plan, as the statement says | The refusals and their order, the plan's rows, and the ignore rules leaving the plan alone |
| `drift-detection` level 4 | state-and-drift | Revert, accept and alert defined; a world that already matches the description needs no change, which the statement's rule for leaving out a row also says | The newest rule wins, and the mapping of drift rows to reconcile rows |
| `values-templating` level 1 | templates-and-layered-values | Layers where the later wins; deep and shallow merges; RFC 7396's rules in prose, which the statement compares itself with; the shallow trap shown with `ChainMap` | The merge itself, the rows and pointers, and document order |
| `values-templating` levels 2 and 3 | templates-and-layered-values | A missing value should fail at render time; a default should fill only missing values, the "classic bug" the statement names | The tag syntax, string literals, error codes and positions, conditions, loops, scoping, truth values and whitespace control |
| `values-templating` level 4 | templates-and-layered-values | JSON Schema keywords in prose (S1 to S5); keeping track of which layer set each value | The validator, its error rows and order, and the provenance rules for objects and lists |
| `values-templating` follow-ups 1 and 2 | templates-and-layered-values | Lists that replace against lists that append, as a trade-off; a value quoted as a JSON string stays a string in YAML 1.2, and a pasted newline, colon or quote can change a document's structure: encoding for the context, which touches follow-up 2 in general | Merging lists by a key field and what a `null` item would mean; what goes wrong inside a quoted string, and the problem's filters |
| `manifest-policy` levels 1 to 4 | templates-and-layered-values | Policy as code; rules such as an owner label, a memory limit and no moving tags, with digests as the fixed alternative; warn before deny; exceptions with an owner, a reason and an end date; pointers to name fields and JSON Patch operations as fixes, as the statement describes | Tag parsing, wildcard expansion, selectors and the port rule, when an exception expires, severity order, and how each fix is built |

## Independent accuracy review (2026-11-14)

The review checks every claim of the five guides against the source this page gives for it, runs every example and compares what it prints with the guide, checks the guides for names, and reads them against the linked problems' statements, hints, solutions and follow-ups. All six examples match their output blocks, and the guides name no company or product. It finds one spoiler, claims to state more precisely, terms a beginner needs explained, and two column headings of this record to change. These are its findings and what changes.

| Finding | Change |
|---------|--------|
| `three_way.py` reuses the data of `drift-detection` level 1, example 1, and prints its rows in the same order; the guide's examples of drift, the identifier `i-100` and a tag written by a billing job echo the statement's | New resources, identifiers and attributes (`vm/build`, `vol-b`, `b-12`), findings grouped by verdict with the unmanaged ones first; in the prose, new examples of drift, the identifier `vm-31`, and a last-modified time and a counter as attributes that change on their own (E4, and the `drift-detection` level 1 row of the table above) |
| The templating guide and `scalars.py` say the patterns are copied from the core schema, which also has rows for infinity and not-a-number | "Copied from the core schema, except the infinity and not-a-number rows" (Y2) |
| The YAML 1.1 boolean type is described as `y`, `yes`, `n`, `no`, `on` and `off` "in their capitalized forms" | `yes`, `no`, `on` and `off` in lower-case, capitalized and upper-case forms, and the single letters `y`, `Y`, `n`, `N` (Y3) |
| The bound on passes until a run is quiet holds only under conditions the guide does not state | It holds when no step undoes another's change, and each step settles once what it reads is final |
| Convergence "from wherever it started" overstates Couch and Sun, for whom convergence is meaningful only relative to a baseline state (C3) | "From any starting state the description allows" |
| The state guide uses "drift" both for any difference between the record and the world and for the case where only the world changed | The guide says that, below, drift means the narrow case, where only the world changed |
| "Provider", "SHA-256 hash" and "image" appear without explanation | A provider is the cloud or other system that creates and runs the resources; a SHA-256 hash is a short fixed-size digest that any change to the state would alter, with a link to the guide on cryptographic hashes; an image is the packaged program a service runs |
| "The user would be left pointing at nothing" names no user | "What depends on it would be left pointing at nothing" |
| This record's headings "Kept back" and "Left out" speak of the writing | "Not in the guide" and "Not named in the guides" |
