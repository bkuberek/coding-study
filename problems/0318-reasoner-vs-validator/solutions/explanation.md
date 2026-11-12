# Reasoner vs Validator: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| fixpoint-closure | optimal | O(J) to saturate, J the rule joins; O(F V) to validate | O(T) for the T triples of the closure | default answer; one closure serves the reasoner and the asserted set serves the validator |

Here `T` is the number of triples in the closure, `J` the number of rule joins performed while building it, `F` the number of focus nodes over all shapes and `V` the number of constraint checks per focus node.

## How the design grows level by level

| Level | Change | What the design adds |
|-------|--------|----------------------|
| 1 | Two rules, `rdfs9` and `rdfs11` | A set of asserted triples, a closure computed from it, and lookups over the closure |
| 2 | `rdfs2` and `rdfs3`, and the answer `unknown` | Two maps from a property to its domains and ranges; `ask` as membership in the closure |
| 3 | Transitive and inverse properties, and clashes | Successor and predecessor maps per predicate; a pass that intersects the instance sets of two disjoint classes |
| 4 | A validator and a comparison | Nothing is added to the closure: the validator is a second, smaller view, built from the asserted triples |

The early choice that matters is to keep the asserted triples and the closure apart. `add` reports on the asserted set, the reasoner reads the closure, and the validator reads the asserted set again. A first version that adds the derived triples to one set answers levels 1 to 3 correctly, and then cannot say what the data contained, which is the one thing level 4 needs.

## Approach: fixpoint-closure (Forward chaining to a fixed point and a check on the asserted graph)

### Intuition

Every rule of the problem has the same shape: if two triples (three for a transitive property: its declaration and two links) are in the closure, so is another. Such rules are applied by *forward chaining*: keep a to-do list of triples, take one, store it, and add every triple that follows from it together with the triples already stored. When the list is empty, nothing more follows, and what is stored is the closure. The rules never create a term, so the closure is finite and the loop ends. A reasoner is this loop and lookups in what it built. A validator is a different thing: it does not complete the data, it holds it against a list of requirements, so it reads the triples as they were given and counts.

### Algorithm

1. Keep `asserted`, a set of triples, and a cached `closure` that `add` clears.
2. To build the closure, put every asserted triple on a to-do list and index nothing yet. Take a triple `t = (s, p, o)`; skip it if it is already known. Otherwise store it, update the indexes (the pairs of each predicate, successors and predecessors per predicate, the members of each class, and the maps of domains, ranges, inverses and superclasses), and then apply every rule in which `t` can be a premise:
   - as a data triple: add `s rdf:type C` for every domain `C` of `p`, add `o rdf:type C` for every range `C`, add `o q s` for every inverse `q` of `p`, and, when `p` is transitive (`rdfs:subClassOf` always is), join `t` with the successors of `o` and the predecessors of `s`;
   - as a class assertion `x rdf:type C`: add `x rdf:type D` for every known superclass `D` of `C`; when `C` is `owl:TransitiveProperty`, `x` becomes transitive and all its pairs are joined;
   - as `C rdfs:subClassOf D`: add `m rdf:type D` for every member `m` of `C`;
   - as `p rdfs:domain C` or `p rdfs:range C`: apply it to every pair already stored for `p`;
   - as `p owl:inverseOf q`: record both directions and mirror every pair already stored for either predicate.
3. `closure`, `types`, `instances` and `superClasses` filter the closure, drop the class itself from the superclasses, and sort.
4. `ask` is `entailed` when the triple is in the closure; for an `rdf:type` triple it is `contradicted` when one type of the subject is disjoint with the asked class or one of its superclasses; otherwise `unknown`.
5. `inconsistencies` normalises each `owl:disjointWith` triple of the closure to a sorted pair, and intersects the instance sets of its two classes.
6. `validate` builds the types of each node from the asserted triples only: its asserted classes and the classes reached through asserted `rdfs:subClassOf` triples. For each shape, each focus node and each constraint, it counts the distinct asserted values and checks the class of each value.
7. `contrast` reports the same rows and, for each, a lookup in the closure: the number of objects for a minimum, the membership of the class triple for a class, nothing for a maximum.

### Correctness

Soundness: every triple the loop adds is the conclusion of a rule whose premises are stored, so the closure holds only consequences. Completeness: take any rule instance with its premises (two, or three for the transitive rule) in the closure. Whichever of them is taken off the to-do list last finds the others already stored, because the indexes are updated before the rules are applied, and then the rule's conclusion is added. A premise that is also the conclusion of another rule (a type that `rdfs3` infers and `rdfs9` climbs) is handled the same way, because every added triple goes through the same loop. A triple that is both data and vocabulary, such as `p rdfs:domain C` with `p` equal to `rdfs:domain`, is indexed first and then applied, so it finds itself.

Termination: the terms of the closure are the terms of the asserted triples, so there are at most `n^3` triples, and each is processed once.

The validator is correct because it follows the table of the statement, and it never looks at the closure. The comparison is correct for the same reason: the two readings share only the data. A minimum that the closure meets but the asserted triples do not is exactly the case where the reasoner finds the value that nobody wrote down.

### Complexity

- Time: O(J) to saturate, J the rule joins; O(F V) to validate — each triple is processed once, and the joins it triggers are bounded by the stored triples that share a term with it (for a transitive chain of `n` nodes, `J` is `O(n^3)` in the worst case, since each of the `n^2` links is joined with up to `n` neighbours); validation looks at each focus node and each constraint once, with a set lookup for the class of each value.
- Space: O(T) for the T triples of the closure — the closure and its indexes; `T` is `O(n^2)` for a transitive property over `n` nodes.

### Trade-offs

- Recomputing the closure after every `add` is simple and fine for a few hundred triples. When triples are only added, the to-do list can be started again from the new triple alone, which costs the new consequences and no more. When triples can be removed, a derived triple may have several reasons, and the usual answers are counting reasons or recomputing the affected part.
- Computing the closure up front trades space for fast queries. The alternative, backward chaining, answers one question at a time by searching for rules that conclude it, and stores nothing; it wins when the closure is huge and the questions are few.
- A validator that reads the closure would let the reasoner "fill in" values and conform more often. That is a legitimate design, and some tools do exactly that, but then a mistake that an inference happens to hide is not reported. This problem separates the two to show the difference.

### Pitfalls and edge cases

- Level 1: `rdfs11` makes a class a subclass of itself only through a cycle, and `superClasses` leaves the class itself out. A class can also be an instance (`Dog rdf:type Species`), which says nothing about its superclasses. `add` reports on the asserted set: adding a triple that is already inferred returns `true`.
- Level 2: a domain or a range is a rule, not a check, and it applies to every triple, including those of the vocabulary (`rdf:type rdfs:range rdfs:Class`). With several domains, the subject gets all of them. The rule fires for triples added before and after the declaration alike. An unknown fact is `"unknown"`, never a "no".
- Level 3: a cycle gives each of its nodes a link to itself, and a node that only leads into the cycle gets none. An inverse works from either side, and a property can be its own inverse. A transitive declaration can itself be inferred. Disjointness is symmetric and rows are listed once, with the two classes sorted; a class disjoint with itself clashes with every instance. `ask` is `contradicted` through a superclass of the asked class, only for `rdf:type`, and never when the triple is already entailed.
- Level 4: the focus nodes are the terms with an asserted type (or one reached through asserted superclasses), not the terms a domain types. A value node is counted once however many times it appears. The values of a path are the asserted ones: a value the closure derives does not fill a minimum. A class violation needs a value, so a missing value is only a minimum violation. A limit of `-1` is no limit, and a limit of `0` forbids every value. Two shapes with the same target report separately, and a node typed through two classes of one chain is one focus node.

### Language notes

- Python: tuples of strings are hashable, so a set of triples needs no key function, and `sorted` on tuples or lists of strings compares by code point, which is the order the statement asks for.
- TypeScript: a `Set` of arrays compares by reference, so triples are stored in a `Map` under a joined string key (a NUL character cannot occur in a term). The default `sort()` of strings compares UTF-16 code units, which agrees with the statement for ASCII; rows need an explicit comparator.

## Further reading

- [RDF Schema 1.1, W3C Recommendation, 2014](https://www.w3.org/TR/rdf-schema/): `rdfs:subClassOf` (transitive), `rdfs:domain` and `rdfs:range`, with the note that the document says what such statements mean and leaves open whether an application infers from them or checks them.
- [RDF 1.1 Semantics, W3C Recommendation, 2014](https://www.w3.org/TR/rdf11-mt/): the RDFS entailment patterns `rdfs2`, `rdfs3`, `rdfs9`, `rdfs10` and `rdfs11` used in the tables (the problem leaves out `rdfs10`, which makes everything typed `rdfs:Class` a subclass of itself).
- [OWL 2 Web Ontology Language Structural Specification, W3C Recommendation](https://www.w3.org/TR/owl2-syntax/): `TransitiveObjectProperty`, `InverseObjectProperties` and `DisjointClasses`, the axioms behind `owl:TransitiveProperty`, `owl:inverseOf` and `owl:disjointWith`.
- [OWL 2 Profiles, W3C Recommendation, section 4.3 (OWL 2 RL/RDF rules)](https://www.w3.org/TR/owl2-profiles/): the rules `prp-trp`, `prp-inv1`, `prp-inv2`, `cax-sco`, `cax-dw`, `scm-sco`, `prp-dom` and `prp-rng`, and the reading of a rule that concludes `false` as an inconsistency.
- [Shapes Constraint Language (SHACL), W3C Recommendation, 2017](https://www.w3.org/TR/shacl/): shapes, `sh:targetClass`, `sh:minCount`, `sh:maxCount` and `sh:class`, the SHACL types of a node, validation results, and the statements that full RDFS inferencing is not required and that a processor may validate a graph that includes entailments.
- [OWL 2 Web Ontology Language Primer, W3C Recommendation](https://www.w3.org/TR/owl2-primer/): the open world assumption (section 2), the absence of a unique name assumption (section 4.7), and a functional property example in which two recorded husbands are inferred to be one individual (section 6.1). It says that domain and range are not constraints but allow a reasoner to infer knowledge, and it does not compare OWL with a validator.
