# Reasoner vs Validator

## Statement

Build `KnowledgeBase`, a small store of facts that can be read in two different ways. A **reasoner** works out what must also be true given what you told it, and it never treats a missing fact as false. A **validator** checks the data you gave against a list of requirements, and it treats a missing fact as a mistake. Both read the same facts and often give different answers about them, which is the point of the problem. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**Facts.** A fact is a *triple* of three terms: a subject, a predicate and an object, such as `rex rdf:type Dog` ("rex is a Dog") or `Dog rdfs:subClassOf Animal` ("every Dog is an Animal"). A *class* is a name for a group of things, and "`x` is an instance of `C`" means that `x` is in the group `C`. Triples are as in the companion problem `0319`, a set of facts about terms, but here a few predicates have a fixed meaning.

**Two ways to read a missing fact.** If the store says `rex rdf:type Dog` and says nothing about `rex`'s owner, a closed-world reader concludes "`rex` has no owner". An *open-world* reader concludes only "I do not know": the owner may exist and simply not be written down. Reasoners work in the open world, because a knowledge base is usually a small part of what is true. Validators work in the closed world, because a form with a missing required field has to be rejected, whatever the world looks like.

**Where the words come from.** The vocabulary and the rules follow three W3C recommendations: *RDF Schema 1.1* (`rdfs:subClassOf`, `rdfs:domain`, `rdfs:range`) with the entailment rules of *RDF 1.1 Semantics*, *OWL 2* (`owl:TransitiveProperty`, `owl:inverseOf`, `owl:disjointWith`) with the rules of the *OWL 2 RL* profile, and the *Shapes Constraint Language (SHACL)* (shapes with `sh:targetClass`, `sh:minCount`, `sh:maxCount` and `sh:class`). This problem uses a deliberately small subset of each, and every rule it uses is written out below: a rule that is not written here does not exist. The links are in the explanation.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 50, level 3 by 80 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `KnowledgeBase()`: creates an empty store with no shapes.
- A **term** is a non-empty string of printable ASCII characters (codes 33 to 126, so no space) of at most 30 characters, compared exactly as given: `Dog` and `dog` are different terms. The one term that is never used is `?`, which patterns use as a wildcard.
- The names `rdf:type`, `rdfs:subClassOf`, `rdfs:domain`, `rdfs:range`, `owl:TransitiveProperty`, `owl:inverseOf` and `owl:disjointWith` are ordinary terms with a meaning that a level gives them. Until the level that explains one, tests do not use it.
- Each level's section describes the methods it adds and their parameters.

## Output

Methods that change the store return a `bool`. Questions return a list of terms, a list of rows or a `string`. A triple is a list of three terms, `[subject, predicate, object]`. Where a method says "sorted", texts are compared by the numeric value of their characters, so that `B` comes before `a` and `10` before `9`; lists of terms are sorted by that order and rows by their first entry, then their second, and so on.

## Level 1: Classes and inherited types

- `add(subject, predicate, obj)`: asserts a triple. It returns `true` when the triple was not among the asserted triples and `false` when it already was. (The object is called `obj` because some languages reserve `object`.) A triple that only follows from others is not asserted until someone adds it, so adding it returns `true`.
- `closure(subject, predicate, obj)`: the triples of the **closure** that fit a pattern, sorted. The closure is the asserted triples plus everything the rules below add, repeated until no rule adds anything new. A position of the pattern is a term, which a triple must have there, or the wildcard `"?"`, which any term fits. `closure("?", "?", "?")` is the whole closure.
- `types(resource)`: the classes `C` such that `resource rdf:type C` is in the closure, sorted.
- `instances(className)`: the terms `x` such that `x rdf:type className` is in the closure, sorted.
- `superClasses(className)`: the classes `C` other than `className` itself such that `className rdfs:subClassOf C` is in the closure, sorted.

At this level there are two rules, named as in the RDF 1.1 Semantics entailment patterns:

| Rule | If the closure has | it also has |
|------|--------------------|-------------|
| `rdfs11` | `C rdfs:subClassOf D` and `D rdfs:subClassOf E` | `C rdfs:subClassOf E` |
| `rdfs9` | `C rdfs:subClassOf D` and `x rdf:type C` | `x rdf:type D` |

So `rdfs:subClassOf` is transitive, and an instance of a class is an instance of every class above it. That is all: there is no rule that makes a class a subclass of itself. If `A` and `B` are each a subclass of the other, `rdfs11` gives `A rdfs:subClassOf A`, so the closure holds it, and `superClasses("A")` still leaves `A` out. A triple with any other predicate is stored and appears in the closure, and nothing follows from it.

### Example 1

<!-- case: ex1 -->

`Dog` is below `Mammal`, which is below `Animal`, so `rex`, asserted only as a `Dog`, is also a `Mammal` and an `Animal`. The second add of `rex rdf:type Dog` returns `false`. `closure` with the wildcard in the object position lists the superclasses of `Dog` as triples, and with `rex` as subject it lists the asserted type and the inferred ones, sorted.

### Example 2

<!-- case: ex2 -->

`Cat` and `Pet` are subclasses of each other, which means they hold the same things. `rdfs11` derives `Cat rdfs:subClassOf Cat`, which the closure holds, while `superClasses("Cat")` is only `Pet`. `tom` is a `Cat` and so also a `Pet`. `tom likes milk` is stored and nothing follows from it: `milk` has no types, and the last pattern, a triple that is not there, gives `[]`.

## Level 2: Domain, range and the open world

Two more predicates say what a property is used for. `p rdfs:domain C` says that whatever has a `p` fact as its subject is an instance of `C`, and `p rdfs:range C` says that whatever is the object of a `p` fact is an instance of `C`. They add two rules, again named as in the RDF 1.1 Semantics:

| Rule | If the closure has | it also has |
|------|--------------------|-------------|
| `rdfs2` | `p rdfs:domain C` and `x p y` | `x rdf:type C` |
| `rdfs3` | `p rdfs:range C` and `x p y` | `y rdf:type C` |

A property can have several domains or ranges, and then the subject, or the object, is an instance of all of them. The rules apply to every triple, whatever its predicate, and the rules of both levels keep being applied until nothing new appears: a type that `rdfs3` infers is climbed through `rdfs9`, and a rule can feed another, also through the vocabulary itself (`rdf:type rdfs:range Class` types every class that is the object of an `rdf:type` fact).

**Domain and range infer, they do not check.** This is the idea to keep. `ada worksFor acme` together with `worksFor rdfs:domain Person` does not require `ada` to be a person, and it never reports an error when `ada` is a robot: it *makes* `ada` a person as well. The RDF Schema specification says only what such a statement means, and leaves open whether an application uses it to infer or to check; the entailment rules `rdfs2` and `rdfs3` are the inference. A tool that wants "every subject of `worksFor` must already be declared a `Person`" needs a validator, which level 4 builds.

- `ask(subject, predicate, obj)`: what the closure says about one triple, as a string. It is `"entailed"` when the triple is in the closure and `"unknown"` otherwise. Open-world reasoning has no third answer at this level: a triple that is not in the closure is not false, it is unknown. Terms are given exactly, with no wildcard.

### Example 1

<!-- case: ex3 -->

`worksFor` has the domain `Person` and the range `Organization`, so `ada worksFor acme` makes `ada` a `Person` and `acme` an `Organization`, and through `Organization rdfs:subClassOf Agent` also an `Agent`. `ada` is asserted a `Robot` and is still made a `Person`: nothing is reported. `ask` answers `"unknown"`, not `"no"`, about a `Plant`, about `acme worksFor ada` and about a term that appears nowhere.

### Example 2

<!-- case: ex4 -->

A property with two domains makes `mia` both a `Teacher` and an `Adult`, and the subclass rule adds `Person`. The range makes `leo` a `Student` and so a `Person`. The reasoner does not conclude that `leo` is an `Adult`: it only does not know.

## Level 3: Transitive, inverse and disjoint

Three more ideas from OWL 2 add rules and one kind of error.

| Rule | If the closure has | it also has |
|------|--------------------|-------------|
| `prp-trp` | `p rdf:type owl:TransitiveProperty`, `x p y` and `y p z` | `x p z` |
| `prp-inv1` | `p owl:inverseOf q` and `x p y` | `y q x` |
| `prp-inv2` | `p owl:inverseOf q` and `x q y` | `y p x` |

`ancestorOf` declared transitive turns "Ann is an ancestor of Bea" and "Bea is an ancestor of Cy" into "Ann is an ancestor of Cy". `parentOf owl:inverseOf childOf` turns `ann parentOf bea` into `bea childOf ann`, and it works the same from either side. A property may be its own inverse, which makes it symmetric. All the earlier rules keep applying, so a link that a transitive or an inverse rule adds is seen by `rdfs2` and `rdfs3` and can feed the rules again. A cycle in a transitive property gives every term on it a link to itself, and it ends the derivation.

**Disjoint classes.** `A owl:disjointWith B` says that nothing is an instance of both. The reasoner does not remove anything, and it has no rule that adds a triple here; instead, a term whose types in the closure include both `A` and `B` is a **clash**, which OWL 2 RL calls an inconsistency (rule `cax-dw`: two disjoint classes and an instance of both give `false`). The statement is symmetric: it does not matter which of the two classes was named first, and a pair counts when an `owl:disjointWith` triple is in the closure in either direction (the closure does not add the mirrored triple). A class can be disjoint with itself, and then any instance of it is a clash.

- `inconsistencies()`: one row `[resource, first, second]` for every term and every pair of disjoint classes it is an instance of, where `first` and `second` are the two classes in sorted order (`first` equal to `second` for a class disjoint with itself). A pair stated in both directions gives one row. The rows are sorted. The answer is `[]` when there is no clash. A clash does not stop the reasoner: the closure and all the other answers are computed as before. (In formal OWL an inconsistent ontology entails every statement; this problem just lists the clashes.)
- `ask` has a third answer. For an `rdf:type` triple that is not in the closure, `ask(x, rdf:type, C)` is `"contradicted"` when some class `A` among the types of `x` in the closure is disjoint with `B`, where `B` is `C` or a superclass of `C` in the closure (disjointness is symmetric, as above). Said plainly, adding the triple would create a clash. In every other case where the triple is not in the closure the answer is `"unknown"`, and it is `"entailed"` when it is in the closure. A triple with another predicate is never contradicted.

The open world has one way to say no, and it is this one: a fact is ruled out only when something else you stated is incompatible with it.

### Example 1

<!-- case: ex5 -->

`ann` is an ancestor of `bea` and `cy`, and of `dee` through `cy`, so the closure holds all three links from `ann`. The second pattern reads `bea childOf ann` off the inverse declaration. The last pattern lists everyone who is an ancestor of `dee`, including those whose link is derived.

### Example 2

<!-- case: ex6 -->

`Robot` and `Person` are disjoint, `r2` is a robot and `kim` a person, so there is no clash. After `r2 worksFor acme`, the domain of `worksFor` makes `r2` a `Person`, and the reasoner reports a clash that no single fact states: that is the one error an open-world reasoner can find. `ask` says `"contradicted"` when `kim` is asked to be a `Robot` because `kim` is a `Person`; it says `"unknown"` for a `Plant`, and for a fact with the predicate `likes`.

## Level 4: Shapes and the closed world

A **shape** states what the data about a group of terms must look like. This level adds a small version of SHACL. A shape has a name and a **target class**; its **focus nodes** are the terms that are instances of the target class. For each focus node the shape lists **property constraints**: for one predicate, called the `path`, the number of values the node must have (at least `minCount`, at most `maxCount`) and the class the values must belong to.

- `addShape(shape, targetClass)`: declares a shape. It returns `false` and changes nothing when a shape with that name exists.
- `addProperty(shape, path, minCount, maxCount, valueClass)`: gives the shape a property constraint. `minCount` is 0 or more; `maxCount` is `-1` for no limit or 0 or more; `valueClass` is `""` for no class condition. It returns `false` and changes nothing when the shape does not exist or already has a constraint for that path.
- `validate()`: the violations, as rows `[focusNode, shape, path, component, value]`, sorted, with no row repeated. Zero violations is `[]`.
- `contrast()`: the same violations with what the reasoner says about each, as rows `[focusNode, shape, path, component, value, reasoner]` in the same order.

**What the validator reads.** It reads the **asserted** triples only, never the closure. Following SHACL, the one piece of reasoning it does is the class hierarchy: a term's **types** are the classes it is asserted to have through `rdf:type`, plus every class above them reached through asserted `rdfs:subClassOf` triples (any number of steps, none included). Nothing else is inferred: no domain, no range, no inverse, no transitive link. Having a type only because a domain or a range gives it one does not make a term a focus node. The SHACL specification does not require inference, and says a processor may validate a graph that already contains entailed triples; this problem validates the graph as asserted, which is how to see the difference.

**The constraints.** For a shape with target class `T`, every focus node `n` (a term with `T` among its types, whether asserted or by the hierarchy), and each constraint on a path `p`, let the **value nodes** be the distinct terms `v` with the asserted triple `n p v`.

| Component | A violation when | `value` |
|-----------|------------------|---------|
| `sh:MinCountConstraintComponent` | there are fewer value nodes than `minCount` | `""` |
| `sh:MaxCountConstraintComponent` | `maxCount` is not `-1` and there are more value nodes than `maxCount` | `""` |
| `sh:ClassConstraintComponent` | `valueClass` is not `""`, and for a value node `v` the class `valueClass` is not among the types of `v` | `v` |

A class violation is reported for each such value node. A missing value gives no class violation, because there is nothing to check: only `sh:MinCountConstraintComponent` can complain about it. A shape with no constraints never complains. The three constraints of one path are judged independently of one another, so a constraint can give several rows.

**What the reasoner says.** For each violation, `contrast` adds the answer of the open-world reader to the same question:

- For a `sh:MinCountConstraintComponent` row: `"entailed"` when the closure has at least `minCount` distinct objects `v` with `n p v`, and `"unknown"` otherwise. The validator counted what is written; the reasoner counted what follows, so it may say the values exist.
- For a `sh:ClassConstraintComponent` row: `"entailed"` when `v rdf:type valueClass` is in the closure, and `"unknown"` otherwise.
- For a `sh:MaxCountConstraintComponent` row: `"no-error"`. The reasoner of this problem has no cardinality rule, so too many values is nothing it can detect.

This is the whole contrast. A requirement of the form "must be present" is violated when the fact is not written, and the reasoner can only ever say "unknown" about it, or find it among the consequences.

### Example 1

<!-- case: ex7 -->

`ada` is an `Employee`, and `Employee` is below `Person`, so `ada` and `bob` are focus nodes of `PersonShape`, while `cy`, a `Robot`, is not. `bob` has no `email`: a minimum-count violation, where a reasoner would only say "unknown". `ada` has two `worksFor` values, one too many for the limit, and `beta` is not asserted to be an `Organization`, so it is a class violation, while `acme` is fine. The rows come in sorted order, the class violation before the maximum-count one.

### Example 2

<!-- case: ex8 -->

`ada` and `kim` are persons, `zed` is only the subject of a `worksFor` fact. Validation does not target `zed`, although the reasoner is sure `zed` is a `Person` (the `ask` at the end). `kim` has no asserted `hasParent` value, so the validator complains, and `contrast` says `"entailed"`: `ada hasChild kim` and the inverse declaration give `kim hasParent ada`. `acme` is not asserted to be an `Organization`, so `ada`'s `worksFor` value is a class violation, and the range of `worksFor` makes it `"entailed"`. The missing `worksFor` of `kim` is `"unknown"`, and so is `ada`'s `hasParent`.

## Constraints

- At most 1000 calls per test, and at most 300 distinct terms.
- The closure of a test has at most 100000 triples, and the answer to one call has at most 10000 entries.
- `0 <= minCount <= 100`, and `maxCount` is `-1` or `0 <= maxCount <= 100`.
- A term is never `?`, and a shape name is a term.

## Follow-ups

- `closure` recomputes everything when a triple is added. How would you keep it up to date when triples are only added, and what changes when they can also be removed (hint: a derived triple may have two reasons)?
- SHACL can validate the closure instead of the asserted graph, by running the reasoner first. When does that make a missing value stop being a violation, and when does it hide a real mistake?
- OWL 2 has cardinality restrictions, but without the unique name assumption two distinct names may denote one thing, so "at most one" infers that they are the same instead of reporting an error. Why does that make `sh:maxCount` a validator's constraint?
- A SHACL shape can also say `sh:node`, `sh:or` and `sh:not`. Which of them need the closed-world assumption to mean anything?

## Hints

### Hint 1

Think of the facts as a list of three-word sentences. A reasoner is a program that keeps adding sentences that must be true, until it has nothing new to add. Start with just two rules: if `A` is a kind of `B` and `x` is an `A`, then `x` is a `B`; and if `A` is a kind of `B` and `B` a kind of `C`, then `A` is a kind of `C`. Write a loop that tries them on every pair of sentences and stops when a whole pass adds nothing.

### Hint 2

Keep the sentences in a set, so that adding one twice is harmless, and the loop ends because no rule invents a new word: there are only so many sentences that can be made from the words in the store. Keep the asserted sentences apart from the derived ones: `add` answers about the asserted ones, and the validator will read only those.

### Hint 3

A pass over every pair is slow when a chain is long. Give each new sentence to a to-do list; when you take one off, look it up against what you have already stored (by predicate, and by subject or object) and add what follows. Every rule has two premises, so a pair is found when the later of its two sentences is taken off the list.

### Hint 4

`ask` needs three answers: in the closure, ruled out by a disjoint class, or neither. For "ruled out", first list the types the term has now, then check whether any disjoint pair has one class among them and the other among the asked class and its superclasses.

### Hint 5

For `inconsistencies`, collect for every class the set of its instances, normalise each `owl:disjointWith` triple to a pair in sorted order, and intersect the two sets. Collect the rows in a set, so that a pair stated twice appears once, and sort at the end.

### Hint 6

For the validator, build a second, much simpler view: the asserted `rdf:type` and `rdfs:subClassOf` triples only. A term's types are what you reach by following `rdfs:subClassOf` from its asserted types. A focus node is a term with the target class among those. Count the asserted values of the path as a set. Do not look at the closure here.

### Hint 7

`contrast` is `validate` plus one extra lookup per row, in the closure this time: for a minimum, count the objects of `node path ?`; for a class, test whether `value rdf:type valueClass` is there; for a maximum, the answer never changes.
