# Review: the facts of the knowledge representation guides

The five guides of the path "Knowledge representation: from taxonomies to triples, reasoning and entity resolution" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about W3C Recommendations (SKOS, RDF 1.1 Concepts, N-Triples, Turtle, SPARQL 1.1 Query, RDF 1.1 Semantics, RDF Schema 1.1 and SHACL), the RDF 1.2 draft, and three papers on record linkage. This page lists each one with where it was checked, so that the independent review starts from the sources.

"Quote" means the exact text was read at that source: in the HTML of the W3C page converted to text, or in the text extracted from a PDF with `pdftotext`. "Run" means an example of the guide printed it, on CPython 3.13.12. "Arithmetic" means the number was computed from the stated inputs. Bibliographic data of every paper was checked against its Crossref record. A fact that could not be checked is not in the guides; the last sections list those, the names used, and where a guide comes close to a linked problem.

| Guide | Slug |
|-------|------|
| Taxonomies and SKOS | `taxonomies-and-skos` |
| Triples and RDF graphs | `rdf-triples` |
| Querying graphs: basic graph patterns and SPARQL | `graph-patterns-and-sparql` |
| Reasoning and validation: open and closed worlds | `reasoning-and-validation` |
| Entity resolution and record linkage | `record-linkage` |

## SKOS

[*SKOS Simple Knowledge Organization System Reference*, W3C Recommendation, 18 August 2009](https://www.w3.org/TR/skos-reference/). Used in `taxonomies-and-skos`.

| # | Claim | Source |
|---|-------|--------|
| K1 | Knowledge organization systems such as thesauri, taxonomies, classification schemes and subject heading systems share a similar structure, which SKOS provides a data model for | Quote: abstract and §1 |
| K2 | A SKOS concept "can be viewed as an idea or notion; a unit of thought" | Quote: §3.1 |
| K3 | `<A> skos:broader <B>` asserts that B is a broader concept than A; a hierarchical link says one concept is "in some way more general"; by convention `skos:broader` and `skos:narrower` assert only direct links, and `skos:broaderTransitive` and `skos:narrowerTransitive` are not used to make assertions but to infer the transitive closure; `skos:related` is an associative link | Quote: §8.1 |
| K4 | SKOS is not a formal knowledge representation language; a thesaurus or classification scheme "does not assert any axioms or facts"; its structures "do not have any formal semantics" | Quote: §1.3 |
| K5 | `skos:broader` is a sub-property of `skos:broaderTransitive` (S22), which is transitive (S24); `skos:narrower` is the inverse of `skos:broader` (S25); `skos:broader` is not transitive, so `A broader B` and `B broader C` do not entail `A broader C` (Example 34), only `A broaderTransitive C` (Example 35); a sub-property of a transitive property is not necessarily transitive | Quote: §8.3 and §8.6.6 |
| K6 | The reference makes no statement on whether `skos:broader` is reflexive or irreflexive; a cycle in the hierarchical relation is consistent with the data model and a potential problem for many applications, whose handling is left to them; two alternative paths are consistent, a pattern that arises naturally in poly-hierarchical systems | Quote: §8.6.7, §8.6.8 and §8.6.9 |
| K7 | `skos:prefLabel`, `skos:altLabel` and `skos:hiddenLabel` are pairwise disjoint (S13); a resource has at most one `skos:prefLabel` per language tag (S14); hidden labels serve text search, for example matching a misspelled query, without being visible to the user | Quote: §5.1 and §5.4 |
| K8 | A concept scheme, `skos:ConceptScheme`, can be viewed as an aggregation of one or more SKOS concepts | Quote: §4.1 |
| K9 | `skos:exactMatch` is a sub-property of `skos:closeMatch` (S42); both are symmetric (S44); `skos:exactMatch` is transitive (S45); `skos:closeMatch` is not declared transitive, to avoid "compound errors" when combining mappings across more than two schemes; exact match: "a high degree of confidence" that the concepts can be used interchangeably across a wide range of information retrieval applications; close match: "sufficiently similar" to be used interchangeably in some; `skos:exactMatch` is disjoint with `skos:broadMatch` and `skos:relatedMatch` (S46) | Quote: §10.1, §10.3 and §10.4 |
| K10 | `skos:related` is symmetric (S23) and disjoint with `skos:broaderTransitive` (S27) | Quote: §8.3 and §8.4 |
| K11 | The only statement about OWL classes is that `skos:Concept` is an instance of `owl:Class`, deliberately, so a resource can be both; the namespace is `http://www.w3.org/2004/02/skos/core#` | Quote: §3.5.1 and §2 |

## RDF 1.1 Concepts, N-Triples and Turtle

[*RDF 1.1 Concepts and Abstract Syntax*](https://www.w3.org/TR/rdf11-concepts/), [*RDF 1.1 N-Triples*](https://www.w3.org/TR/n-triples/) and [*RDF 1.1 Turtle*](https://www.w3.org/TR/turtle/), W3C Recommendations of 25 February 2014, and the draft [*RDF 1.2 Concepts and Abstract Syntax*](https://www.w3.org/TR/rdf12-concepts/). Used in `rdf-triples`, and where noted in other guides.

| # | Claim | Source |
|---|-------|--------|
| D1 | An RDF graph is a set of RDF triples; the subject is an IRI or a blank node, the predicate an IRI, the object an IRI, a literal or a blank node; the nodes of a graph are its subjects and objects | Quote: Concepts, §3 and §3.1 |
| D2 | IRIs have global scope: two appearances of an IRI denote the same resource; IRIs are a generalization of URIs that permits a wider range of Unicode characters, and every absolute URI and URL is an IRI | Quote: Concepts, §1.3 and §3.2 |
| D3 | A literal has a lexical form, which should be in Normal Form C, a datatype IRI, and a language tag if and only if the datatype is `rdf:langString`; language tags may be converted to lower case; simple literals are syntactic sugar for `xsd:string` | Quote: Concepts, §3.3 |
| D4 | `"1"^^xs:integer` and `"01"^^xs:integer` denote the same value but are not the same term, since literal term equality compares the lexical forms, datatypes and language tags character by character | Quote: Concepts, §3.3 |
| D5 | Blank nodes do not identify specific resources; statements with them say that something with the given relationships exists; blank node identifiers are local to a file or store and not part of the abstract syntax; systems may replace some or all blank nodes with IRIs | Quote: Concepts, §1.2, §3.4 and §3.5 |
| D6 | Two graphs are isomorphic when a bijection between their nodes maps blank nodes to blank nodes and leaves IRIs and literals alone | Quote: Concepts, §3.6 |
| D7 | A dataset has exactly one default graph, which has no name and may be empty, and zero or more named graphs, each a pair of an IRI or blank node and a graph; graph names are unique within a dataset; blank nodes can be shared between its graphs; the name is not required to denote the graph; some implementations do not track empty named graphs | Quote: Concepts, §4 |
| D8 | Anything can be a resource, including physical things, documents, abstract concepts, numbers and strings; a predicate denotes a property, a resource that can be thought of as a binary relation; relations involving more than two entities can only be expressed indirectly | Quote: Concepts, §1.2 |
| D9 | Generalized triples, in which each position can be an IRI, a blank node or a literal, are described in a non-normative section; they make, for example, the completeness of the RDFS entailment rules easier to show | Quote: Concepts, §7 |
| D10 | RDF 1.2 was a Candidate Recommendation Draft dated 13 November 2026; compared to RDF 1.1 it introduces triple terms in the object position of another triple, and directional language-tagged strings | Quote: RDF 1.2 Concepts, status line and abstract |
| T1 | N-Triples is a line-based, plain text format and an easy-to-parse subset of Turtle; a triple is a subject, a predicate and an object separated by white space and terminated by a `.` and a new line | Quote: N-Triples, §1 and §2 |
| T2 | In Turtle, `@prefix` and prefixed names abbreviate IRIs, a `;` repeats the subject (predicate lists), a `,` repeats the subject and predicate (object lists), and the token `a` in the predicate position is `rdf:type` | Quote: Turtle, §2, §2.2, §2.3 and §2.4 (IRIs) |

## SPARQL 1.1

[*SPARQL 1.1 Query Language*, W3C Recommendation, 21 March 2013](https://www.w3.org/TR/sparql11-query/). Used in `graph-patterns-and-sparql`.

| # | Claim | Source |
|---|-------|--------|
| Q1 | A triple pattern is a member of (RDF-T ∪ V) × (I ∪ V) × (RDF-T ∪ V), which includes literal subjects; such a pattern fails to match on any RDF graph; a basic graph pattern is a set of triple patterns | Quote: §18.1.5 and §18.1.6 |
| Q2 | A solution mapping is a partial function from variables to RDF terms; two mappings are compatible if they agree on every variable in both domains; `Join(Ω₁, Ω₂)` merges every compatible pair | Quote: §18.1.8, §18.3 (Compatible Mappings) and §18.5 (Join) |
| Q3 | μ is a solution of a basic graph pattern when an instance of the pattern is a subgraph of the graph; the empty basic graph pattern has the solution Ω₀, the multiset holding exactly the empty mapping | Quote: §18.3 and §18.3.1 |
| Q4 | Query patterns generate an unordered collection of solutions, then treated as a sequence initially in no specific order; `ORDER BY` establishes an order; `DISTINCT` eliminates duplicate solutions, returning only one solution that binds the same variables to the same terms | Quote: §15, §15.1 and §15.3 |
| Q5 | Blank nodes in graph patterns act as variables, not as references to specific blank nodes in the data | Quote: §4.1.4 |
| Q6 | Property path forms: an IRI, `^elt` (inverse), `elt1/elt2` (sequence), `elt1\|elt2` (alternative), `elt*` (zero or more), `elt+` (one or more), `elt?` (zero or one), and negated property sets | Quote: §9.1 |
| Q7 | Connectivity matching does not introduce duplicates (it does not count the ways a connection can be made), and is defined so that cycles do not lead to undefined or infinite results; `ZeroOrMorePath` and `OneOrMorePath` match distinct nodes; the specifying algorithm detects nodes already visited on a path, and an implementation may use any method with the same results | Quote: §9.4 and §18.4, the function ALP |
| Q8 | A property path is a sequence of triples where the object of each is the subject of the next; it starts at the subject of the first and ends at the object of the last; it does not span multiple graphs in a dataset | Quote: §18.1.7 |
| Q9 | `ZeroOrMorePath` with both ends variables pairs every node of the graph (every subject or object) with itself, since ALP adds its start node to the result | Quote: §18.4, the evaluation of `ZeroOrMorePath`, the function ALP and the definition of `nodes(G)` |

## RDF 1.1 Semantics and RDF Schema 1.1

[*RDF 1.1 Semantics*](https://www.w3.org/TR/rdf11-mt/) and [*RDF Schema 1.1*](https://www.w3.org/TR/rdf11-schema/), W3C Recommendations of 25 February 2014. Used in `reasoning-and-validation`.

| # | Claim | Source |
|---|-------|--------|
| E1 | The RDFS entailment patterns rdfs1 to rdfs13 are informative; rdfs2 (domain), rdfs3 (range), rdfs5 (sub-property of a sub-property), rdfs7 (a triple holds with the super-property), rdfs9 (an instance of a subclass is an instance of the class) and rdfs11 (subclass of a subclass) read as in the guide's table; rdfs4a and rdfs4b make subjects and objects `rdfs:Resource`, rdfs6 and rdfs10 make each property a sub-property of itself and each class a subclass of itself, and rdfs8 makes each class a subclass of `rdfs:Resource` | Quote: Semantics, §9.2.1, the table |
| E2 | Even the empty graph has many RDFS entailments, such as `aaa rdf:type rdfs:Resource` for every IRI `aaa` | Quote: Semantics, §9.2 |
| E3 | If S is a subgraph of S' and S simply entails E, then S' simply entails E; all entailment regimes must be monotonic extensions of simple entailment, and a semantic extension cannot cancel an entailment made by a weaker regime, though it can treat the result as a syntax error | Quote: Semantics, §5.3 and §3 |
| E4 | A graph with a property whose domain is `xsd:boolean`, a resource typed `xsd:integer`, and a triple using the property on that resource is RDFS unsatisfiable when `xsd:integer` and `xsd:boolean` are recognized | Quote: Semantics, §9.2.1, after the table |
| F1 | `rdfs:subClassOf` states that all instances of one class are instances of another, and `rdfs:subPropertyOf` that all resources related by one property are also related by another; both are transitive; `rdf:type` states that a resource is an instance of a class | Quote: Schema, §3.3, §3.4 and §3.5 |
| F2 | `rdfs:domain` and `rdfs:range` state that the subjects, or the objects, of a property's triples are instances of a class; with several domains or ranges, they are instances of all of them | Quote: Schema, §3.1 and §3.2 |
| F3 | RDF Schema "does not say whether or how an application should use" this information; data checking tools might use it to discover errors, an interactive editor to suggest values, a reasoning application to infer information | Quote: Schema, §4 |

## SHACL

[*Shapes Constraint Language (SHACL)*, W3C Recommendation, 20 July 2017](https://www.w3.org/TR/shacl/). Used in `reasoning-and-validation`.

| # | Claim | Source |
|---|-------|--------|
| H1 | SHACL is a language for validating RDF graphs against a set of conditions, given as shapes in a shapes graph; the validated graphs are data graphs | Quote: abstract |
| H2 | `sh:targetClass` targets the SHACL instances of a class; the targeted terms become focus nodes; a property shape's value nodes are the nodes reached from the focus node by its path | Quote: §1.4, §2.1.2, §2.1.3.2 and §3.7 |
| H3 | The SHACL types of a term are its `rdf:type` values plus their SHACL superclasses, reached by sequences of `rdfs:subClassOf` triples in the graph | Quote: §1.1, SHACL Subclass and SHACL Type |
| H4 | SHACL uses the RDF and RDFS vocabularies but full RDFS inferencing is not required; processors may operate on graphs that include entailments; `sh:entailment` names the inference a shapes graph requires, and a processor that does not support it must signal a failure | Quote: §1.5 |
| H5 | `sh:minCount` is the minimum number of value nodes, always satisfied at 0; `sh:maxCount` the maximum; `sh:class` requires each value node to be a SHACL instance of a given type | Quote: §4.2.1, §4.2.2 and §4.1.1 |
| H6 | `sh:conforms` is true if and only if validation produced no results; the severities are `sh:Info`, `sh:Warning` and `sh:Violation` | Quote: §3.6.1.1 and §2.1.4 |

## Record linkage

The papers, read from the copies linked; bibliographic data from Crossref, except for Winkler's proceedings paper, which has no DOI and is cited from its own pages. Used in `record-linkage`.

| # | Claim | Source |
|---|-------|--------|
| L1 | The comparison vector records the coded agreements and disagreements on each characteristic; m(γ) and u(γ) are the probabilities of γ for matched and unmatched pairs | Quote: I. P. Fellegi and A. B. Sunter, *A Theory for Record Linkage*, Journal of the American Statistical Association 64(328), 1969, pages 1183 to 1210, [doi:10.1080/01621459.1969.10501049](https://doi.org/10.1080/01621459.1969.10501049), abstract and §2; read from [a reprint](https://cs.cornell.edu/~shmat/courses/cs6434/fellegi-sunter.pdf) |
| L2 | Three decisions: positive link, possible link, positive non-link; a linkage rule assigns a probability to each decision for each comparison vector; the optimal rule minimizes the probability of a possible link at fixed error levels, since possible links "will require expensive manual linkage operations" | Quote: Fellegi and Sunter, abstract and §2 |
| L3 | The rule orders the comparison vectors by decreasing m(γ)/u(γ) and decides by comparing the ratio with two thresholds; it is equivalent to the likelihood ratio test, "the uniformly most powerful test for either hypothesis" | Quote: Fellegi and Sunter, §2.1 and §3.1 (d) |
| L4 | Simplifying assumption: the components are conditionally independent under each of the two distributions, so errors in names are independent of errors in addresses for matched pairs, and accidental agreements are independent for unmatched pairs; nothing is assumed about the unconditional distribution; weights `log m − log u` then add, and only one weight per configuration of each component is needed | Quote: Fellegi and Sunter, §3.2 |
| L5 | With frequency-based weights, agreement on name gives a positive weight, larger the rarer the name; disagreement a negative weight; a name missing on either record a weight of zero | Quote: Fellegi and Sunter, §3.3.1 |
| L6 | For medium-sized files of 10^5 records each, the comparisons would number 10^10; files are blocked, for example on a phonetic code of the surname, and pairs in different blocks are implicit non-links; blocking lowers the level of wrong links by the u-probabilities of pairs that would have been links, and raises the level of missed links by the m-probabilities of pairs that would have been links or possible links | Quote: Fellegi and Sunter, §3.1 (c) and §3.4 |
| L7 | Their rule is quite similar to the intuitively appealing approach of Newcombe, whose papers include *Automatic Linkage of Vital Records*, Science 130 (1959) | Quote: Fellegi and Sunter, §1 and references [4] to [6]; Crossref for the Science paper: volume 130, issue 3381, pages 954 to 959, authors Newcombe, Kennedy, Axford and James |
| W1 | A string comparator maps a pair of strings to the interval [0, 1] and is not necessarily a metric | Quote: W. E. Winkler, *String Comparator Metrics and Enhanced Decision Rules in the Fellegi-Sunter Model of Record Linkage*, Proceedings of the Section on Survey Research Methods, American Statistical Association, 1990, pages 354 to 359, [PDF](http://www.asasrms.org/Proceedings/papers/1990_056.pdf), §1 |
| W2 | Jaro introduced the comparator; it accounts for the lengths of the strings and partially for typical human errors; two characters are in common only if no further apart than half the longer length minus one; transpositions are counted among the assigned characters | Quote: Winkler, §2.4 |
| W3 | The new comparator modifies the basic one according to whether the first few characters agree, for up to four characters | Quote: Winkler, §2.4 |
| W4 | Table 1: "abroms" and "abrams" 0.9333, "lampley" and "campley" 0.9048, showing a higher value for a single difference further from the first position | Quote: Winkler, §2.4 and Table 1 |
| W5 | The string comparators are used in production computer matching software during the Post Enumeration Survey for the 1990 Census | Quote: Winkler, abstract |

The guide gives the initials of Newcombe's co-authors from Fellegi and Sunter's reference list, since the Crossref record lists their family names only.

## The examples and the arithmetic

| # | Claim | Source |
|---|-------|--------|
| X1 | Direct broader concepts of `amphibious-car` are `boat` and `car`; the transitive rule adds `land-vehicle`, `watercraft` and `vehicle` and stops in the third round; `narrower(vehicle)` comes from inverting the links; `amphibious-car` has two paths of 3, `hovercraft` paths of 1 and 2; searches find the alternative and hidden labels | Run: `hierarchy.py` |
| X2 | The stated match of `zoo:crane` is `encyclopedia:crane`; following transitivity adds `machines:crane`; `zoo:heron` stays with `encyclopedia:heron` | Run: `mappings.py` |
| X3 | Six lines, five triples; the two `pages` literals are two terms with the value 412; the naive union gives one blank node two names, renaming apart gives two | Run: `ntriples.py` |
| X4 | Solutions after each join: 2, 2, 2 in the written order and 3, 4, 2 reversed; the cities are Oslo and Paris; three people work for an organization in Paris; only Cy knows themselves | Run: `bgp.py` |
| X5 | 8 asserted triples and 12 in the closure after 3 passes; `:talk42` entailed a book; `kim hasRelative bob` unknown; `:atlas` violates the title shape while the reasoner says unknown; `:talk42` is not a focus node of the asserted graph | Run: `open_and_closed.py` |
| X6 | Agreement weights: smith 6.57, nakamura 10.89, okafor 12.21, lindqvist 13.21 bits; 6 of 25 pairs compared; three links, three possible links; `c4` and `r4` never compared | Run: `fellegi_sunter.py` |
| X7 | log2(0.95 / 0.01) = 6.57 and log2(0.95 / 0.0001) = 13.21, a factor of 100 in u; 5 · 5 = 25 pairs | Arithmetic |

## Citations and names

The guides name no company and no product. Where they name something, it is a W3C Recommendation or draft, a paper cited by its authors, or a census named by a paper. Papers are cited by their authors; Jaro is named as the author of the comparator, through Winkler's paper.

| Left out | Where it appears in a source |
|----------|------------------------------|
| The phonetic code of Fellegi and Sunter's blocking example, named by its proper name | Fellegi and Sunter, §3.3.1 and §3.4 |
| The edit distance named by its authors as a second example of a string comparator | Winkler, §1 |
| The government agency the census paper's author worked for, and the towns of its test data | Winkler, title block and §2.3 |
| The thesauri and subject heading lists that SKOS names as examples | SKOS, §1 |
| The social-network library that the GraphRAG problem's statement names | `graphrag-context`, level 1 |

## Not verified

- Jaro's 1989 paper was not read; the guide describes his comparator only through Winkler's 1990 paper, and gives no formula.
- Winkler's Table 1 gives 0.9667 for "martha" and "marhta", while the value usually quoted for the Jaro-Winkler definition, which the entity resolution problem uses, is 0.9611; the guide quotes neither, only the two pairs W4 compares.
- Newcombe and others' 1959 paper was not read; the guide cites it only for its title and bibliographic data, and for what Fellegi and Sunter say of it.
- The OWL 2 profiles, which the reasoner problem uses for transitive and inverse properties and disjoint classes, were not read for this path; the reasoning guide covers RDFS and SHACL only, and says nothing about OWL beyond K11's note on SKOS concepts.
- B-cubed scoring, the evaluation of the entity resolution problem's last level, was not checked against its primary source and is not in the guide.
- RDF 1.2 is cited only for its status on the day it was read and the two additions its abstract lists.

## Practice links and back-links

The path's problems are on main. Their `meta.yaml` gained these `guides:` entries, after `related:` where the problem had none, or at the end of its existing list:

| Problem | `guides:` |
|---------|-----------|
| 0317 `taxonomy` | `[taxonomies-and-skos]` |
| 0319 `triple-store` | `[rdf-triples, graph-patterns-and-sparql]` |
| 0321 `graphrag-context` | `[retrieval-augmented-generation, agent-memory, graph-patterns-and-sparql]` |
| 0318 `reasoner-vs-validator` | `[reasoning-and-validation]` |
| 0320 `entity-resolution` | `[record-linkage]` |

The path takes `triple-store` twice: level 1, the store and its indexes, after the RDF guide, and all four levels after the guide on queries.

## Where a guide comes close to a linked problem

Each linked problem's statement, hints, solutions and follow-ups are compared with the guides. Each guide teaches its idea with examples of its own; these are the places the review should weigh against the rule that a guide never gives away a linked problem's solution:

| Problem | Guide | Overlap the guide states | Kept back |
|---------|-------|--------------------------|-----------|
| `taxonomy` level 1 | taxonomies-and-skos | Broader and narrower links, several parents, ancestors as the transitive closure computed as a set, and paths of different lengths, which the statement's rule on distance also shows | Ancestors nearest first, levels of a breadth-first walk, ties by id |
| `taxonomy` level 2 | taxonomies-and-skos | SKOS calls a cycle consistent and many applications refuse one, as the statement says; code that assumes one parent gives wrong answers for "the closest common ancestor" | Which way the cycle check walks, and how to find the lowest common ancestors in a DAG |
| `taxonomy` level 3 | taxonomies-and-skos | Preferred, alternative and hidden labels; a case-insensitive search with `casefold`; one label on several concepts; search expansion to narrower concepts | The problem's normalization steps, its duplicate-label refusals, and `expand` |
| `taxonomy` level 4 | taxonomies-and-skos | A renamed concept keeps its identifier and its old name as an alternative label, as the statement describes; `skos:exactMatch` symmetric and transitive, with an example of a compound error; following mappings one step, which the statement also chooses | Retired concepts and resolving them, path compression, schemes from ids, `translate` and `unmapped` |
| `taxonomy` follow-ups 4 and 5 | taxonomies-and-skos | SKOS's descriptions of exact and close matches, and one preferred label per language tag (S14) | Which mapping `translate` could use and what each risks; how the problem's label rules would change per language |
| `triple-store` level 1 | rdf-triples | A graph as a set of triples; an index per position and per pair, or three sorted orders, as the statement describes | Numbering triples, which indexes to keep, removal and sorting |
| `triple-store` level 2 | graph-patterns-and-sparql | Basic graph patterns by the SPARQL definitions: the solutions of each pattern by scanning, the join of compatible mappings, `DISTINCT` projection, a variable twice in a pattern, a fixed term as a filter, and the effect of join order on intermediate results, which the statement also explains; engines start with the most selective pattern. The example would answer the level's queries on a small store, by another route than the problem's hints | Index lookups for the bound positions, binding one pattern at a time with undo, choosing the pattern with the fewest candidates under the current bindings, the bare `?` wildcard |
| `triple-store` level 3 | graph-patterns-and-sparql | `+` over distinct nodes, cycles that cannot make the answer infinite, a visited set, as the statement and SPARQL say | Walking from the known end, backward walks, starts when both ends are open |
| `triple-store` level 4 and follow-up 3 | rdf-triples, graph-patterns-and-sparql | Named graphs as the usual way to record where facts came from, as the statement notes; the list of SPARQL path forms | Spans, answers as of a time, sources per row; which path forms need only another starting set |
| `graphrag-context` | graph-patterns-and-sparql | Fetching the facts within a few hops of an entity, with the path to each, as the graph variant of retrieval-augmented generation | Hops, scores, the greedy fill, parent steps and their ties, rendering |
| `reasoner-vs-validator` levels 1 and 2 | reasoning-and-validation | The RDFS patterns rdfs2, 3, 9 and 11 in the spec's words, which the statement also writes out; a naive loop to a fixed point with rdfs2, 5 and 7; domain infers and does not check; unknown is not false | Code for the class rules, a to-do list of new triples looked up by predicate, subject and object, and `ask` |
| `reasoner-vs-validator` level 3 | reasoning-and-validation | None: transitive and inverse properties and disjoint classes are not covered | All of it |
| `reasoner-vs-validator` level 4 and follow-up 2 | reasoning-and-validation | SHACL targets, focus nodes and the three constraints; SHACL types through `rdfs:subClassOf` only; a check of the asserted triples next to the reasoner's "unknown"; a term typed only by a domain is not a focus node, and would be in the closure, which touches follow-up 2 with one instance | `contrast` and its three answers, the violation rows, and when validating the closure hides a mistake or removes a violation in general |
| `entity-resolution` levels 1 and 2 | record-linkage | The steps; normalization in general (case, punctuation, the order of the name, titles, spaces); blocking keys; Jaro's and Winkler's comparators in words, from Winkler's paper | The problem's normalization rules and their order, its blocking keys, the Jaro-Winkler formula with unrounded transpositions, token overlap, the score's weights and threshold |
| `entity-resolution` level 3 | record-linkage | Matches are not transitive and union-find merges chains, as the statement says; check a group as a whole before merging | The guard's floor and order of merges, canonical records, aliases |
| `entity-resolution` follow-ups 2 to 4 | record-linkage | Fellegi and Sunter's frequency-based weights and placeholder values; several blocking keys from different fields; thresholds chosen from a labelled sample by counting wrong and missed links: each touches its follow-up in general | How to weigh or count a shared key in the problem, which keys to add and what each costs, and the use of the level 4 scores |

## Independent accuracy review

Pending: the owner runs it.
