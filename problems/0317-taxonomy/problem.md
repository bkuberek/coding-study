# Taxonomy

## Statement

Build `Taxonomy`, the core of a product catalog, a tag system or a thesaurus: a set of *concepts* arranged from general to specific, such as `Food`, then `Dairy`, then `Cheese`. People use such a hierarchy to browse ("show me everything under Dairy"), to search ("a search for Food must also find Cheese") and to keep many systems saying the same thing about the same idea. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is a taxonomy?** A taxonomy is a collection of *concepts* together with *broader* and *narrower* links between them. If `Cheese` is narrower than `Dairy`, then `Dairy` is broader than `Cheese`: the two words describe the same link read in two directions. We call the broader concept a *parent* and the narrower one a *child*. A concept with no parent is a *root*.

**Several parents.** In a tree, such as an org chart, everyone has one manager. A taxonomy is looser: a concept may have *several* parents. A `Cheese stick` is both a kind of `Cheese` and a kind of `Snack`. The structure is then a *directed acyclic graph* (a DAG), and people call the idea *polyhierarchy*. There can be more than one path from a concept up to a root, and so questions that have one answer in a tree can have several here.

**The standard behind it.** The W3C standard SKOS (Simple Knowledge Organization System) publishes taxonomies, thesauri and classification schemes as data. This problem borrows its vocabulary and its main rules, and it says where it differs. In SKOS a concept is a `skos:Concept`; `skos:broader` links a concept to a more general one and `skos:narrower` is its inverse. Both links are *direct*: SKOS keeps the transitive versions (`skos:broaderTransitive` and `skos:narrowerTransitive`) apart, and they are what this problem calls ancestors and descendants. SKOS models a concept as an individual, an instance of `skos:Concept`, and not as a class of things, and it defines no subclass reasoning for `broader`. A link such as `Cheese stick` narrower than `Cheese` is a statement about how people organize ideas, and no logical rule follows from it, for example that every cheese stick is a cheese. That is why the only reasoning you do here is following the links.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 35, level 2 by 55, level 3 by 80 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `Taxonomy()`: creates an empty taxonomy.
- A **concept id** is a non-empty string of printable ASCII characters (codes 33 to 126, so no space), at most 20 characters, compared exactly as given and case sensitive. The ids of levels 1 to 3 contain no colon: level 4 gives the text before a colon a meaning.
- A **label** is any text of printable ASCII characters (codes 32 to 126), at most 40 characters, empty included.
- Each level's section describes the methods it adds and their parameters.

## Output

Methods that change the taxonomy return a *status*, a string: `"ok"` when the change was made, or one of the error words the level lists, in which case **nothing has changed**. Questions return a string or a list of ids. A question about an id that is not a concept gets the empty answer: `[]` for a list, `""` for a string.

Lists of ids are in the order the method states. When a method says "sorted", it means sorted by id with texts compared by the numeric value of their characters, so that `B` comes before `a`, and `10` before `9`.

## Level 1: Concepts and parents

- `addConcept(concept, label, parents)`: adds a concept with a preferred label (the name people see) and a list of parents, possibly empty. The `parents` are ids of existing concepts; the same id may appear twice, and is one parent. Statuses: `"duplicate"` when `concept` is already a concept, and then `"unknown-broader"` when any of the parents is not a concept. The label is kept exactly as given.
- `addBroader(narrower, broader)`: adds one more parent to an existing concept. Linking two concepts that are already linked changes nothing and gives `"ok"`. Statuses: `"unknown-concept"` when either id is not a concept. At this level the links never close a loop and never join a concept to itself.
- `prefLabel(concept)`: the label given to `addConcept`, or `""`.
- `broader(concept)`: the direct parents, sorted.
- `narrower(concept)`: the direct children, sorted.
- `ancestors(concept)`: every concept above this one, through any chain of parent links, without the concept itself. The order is *nearest first*: by the **distance**, the fewest links that lead from `concept` up to the ancestor, and ties by id. So all the parents come first (sorted), then the grandparents that are not already listed, and so on. A concept is listed once, however many paths lead to it.
- `descendants(concept)`: the same, going down through children, with the distance counted the same way.
- `roots()`: the concepts that have no parent, sorted.

The shortest distance is the one that counts. If `d` has the parent `c`, `c` has the parent `b`, `b` has the parent `a`, and `d` also has `a` as a parent, then `a` is at distance 1 from `d`, even though a longer path leads to it.

### Example 1

<!-- case: ex1 -->

`stick` has two parents, `cheese` and `snack`. Its ancestors are listed by distance: the parents first (`cheese`, `snack`), then the concepts two links up, `dairy` through `cheese` and `food` through `snack`. `descendants("food")` lists `dairy` and `snack` at distance 1, then `cheese` and `stick`, both at distance 2: `stick` is reached through `snack` in two links. The last call asks about an id that is not a concept.

### Example 2

<!-- case: ex2 -->

The second `addConcept("a", ...)` fails with `"duplicate"`. `"zzz"` is not a concept, so the insert of `b` fails with `"unknown-broader"` and leaves nothing behind: `prefLabel("b")` is `""` and the only root is still `a`. Once `b` is added under `a`, linking it to `a` again is `"ok"` and changes nothing.

## Level 2: No cycles, common ancestors

A **cycle** is a chain of parent links that comes back to where it started: `a` under `b` under `c` under `a`, or a concept under itself. A concept would then be its own ancestor, and the walks of level 1 would never end. SKOS itself does not forbid cycles, but taxonomy tools do, and from this level on the taxonomy never contains one.

- `addBroader(narrower, broader)` gets a new status, `"cycle"`: the link is refused when `broader` is `narrower` or is one of its descendants. The statuses come in this order: `"unknown-concept"`, then `"cycle"`.
- `addConcept(concept, label, parents)` also gets `"cycle"`: when `concept` is in its own `parents`. The statuses come in this order: `"duplicate"`, `"cycle"`, `"unknown-broader"`. A new concept that has not been added yet cannot be the descendant of anything, so this is the only way an insert can close a loop.
- A link that only adds a *shortcut* is not a cycle: `c` under `b` under `a` may also be put directly under `a`.
- `lowestCommonAncestors(first, second)`: the lowest concepts that are above both, as a sorted list. A concept counts as its own ancestor here, as in a tree, so if `first` is above `second` the answer is `[first]`, and for the same id twice it is `[that id]`. The list is `[]` when either id is not a concept and when the two concepts share no ancestor, for example two concepts under different roots.

**Lowest, in a DAG.** Call a concept a *common ancestor* of two concepts when it is above both (or is one of them). A common ancestor is **lowest** when no *other* common ancestor lies below it. In a tree the common ancestors form one chain from the root down, so the lowest one is the last of the chain, and there is exactly one. In a DAG the common ancestors can branch, so there can be several lowest ones: none of them is below another. The answer is the whole set. Choosing the common ancestor with the greatest depth is wrong in a DAG, because depth depends on the path you take, and a lowest ancestor may be shallower than another one.

### Example 1

<!-- case: ex3 -->

Linking `a` under its own descendant `c` would close a loop, and so would `a` under `a`, so both give `"cycle"`. Inserting `d` under `d` also gives `"cycle"`, and `d` is not added. A refusal changes nothing: `a` is still the only root. Putting `c` directly under `a` is only a shortcut, so it is `"ok"`, and `c` then has two parents: its ancestors `a` and `b` are both one link away, listed by id.

### Example 2

<!-- case: ex4 -->

`u` and `v` both have two parents, `x` and `y`, which share the root `r`. The common ancestors of `u` and `v` are `x`, `y` and `r`. `r` is above `x`, so it is not lowest, but neither of `x` and `y` is below the other, so both are. The answer has two concepts. Contrast this with an org chart (problem 0313), where two people always have exactly one lowest common manager. `u` and `w` have the common ancestors `x` and `r`, and only `x` is lowest. `w` and `y` meet only at `r`. A concept above the other one is its own answer: `x` for `u` and `x`, and `u` for `u` and `u`.

## Level 3: Labels and facet expansion

SKOS gives a concept one *preferred label* (`skos:prefLabel`), the name to display, and any number of *alternative labels* (`skos:altLabel`), the other names people use for it: synonyms, abbreviations, old names. A person who types "pooch" should find the concept whose preferred label is "Dog". SKOS requires the two kinds of label of a concept to be different from each other.

**Facet expansion.** A search page often has a filter ("Animal") which should also select everything *below* it ("Dog", "Puppy"). The filter is then *expanded*: a label leads to the concepts that carry it, and from each of them to all its descendants.

**Normalizing labels.** People do not type labels the way they were entered. Two labels are the *same label* when their normalized forms are equal. To normalize a label:

1. remove the spaces at the start and at the end;
2. replace every run of two or more spaces inside by one space;
3. turn each capital letter `A` to `Z` into the small letter `a` to `z`.

Other characters are left as they are, so `é` and `E` are different letters, and `a b` and `ab` are different labels. A label that is empty after step 1 is an *empty label*: it is never matched and never stored as an alternative label.

- `addAltLabel(concept, label)`: adds an alternative label to a concept. The label is kept as given. Statuses, in this order: `"unknown-concept"`; `"empty-label"`; `"duplicate"` when the label is the same label as the preferred label of the concept or as one of its alternative labels. Other concepts may carry the same label.
- `altLabels(concept)`: the alternative labels of the concept as they were given, in the order they were added.
- `findByLabel(label)`: the concepts that have the same label as `label`, whether as preferred label or as alternative label, sorted. It is `[]` for an empty label.
- `expand(labels)`: for each label of the list, the concepts that `findByLabel` finds for it, and all their descendants; the answer is the union, each concept once, sorted. It is `[]` for an empty list.

A label may belong to several concepts: `Mercury` can be a planet and a chemical element. A search finds both, and an expansion covers both subtrees.

### Example 1

<!-- case: ex5 -->

`dog` gets two alternative labels, kept as given (the second one with its spaces and capitals). `canine` and ` HOUND ` find it: they are the same labels after normalizing. Expanding `hound` gives `dog` and its descendant `puppy`; expanding `Animal` gives everything. Adding `dog` as an alternative label of `dog` is refused, because it is its preferred label. An unknown label expands to nothing.

### Example 2

<!-- case: ex6 -->

Two concepts have the preferred label `Mercury`, so a search finds both, and expanding `mercury` adds the crater below the planet. `caloris  Basin` has two spaces in the middle, which normalize to one. A list of labels is a union: `Mercury` and `Sun` together give the sum of their expansions.

## Level 4: Stable ids and two schemes

An id is a promise: other systems store it. A label can change; an id must keep working. This level makes ids stable, and connects two taxonomies.

**Renaming.** `rename` changes the preferred label and leaves the id and all the links alone. The old name is not lost: it becomes an alternative label, so searches that used it still work.

**Replacing.** Sometimes two concepts turn out to be one, or a concept is retired. It is then *deprecated* and *replaced* by another concept: its id is never reused, and every system that still holds the old id is sent to the replacement. SKOS has no property for this; vocabularies usually add `owl:deprecated` and `dcterms:isReplacedBy`, which is the idea used here. Following the replacements of a retired id up to a concept that is not retired is *resolving* it.

**Schemes.** SKOS groups concepts in *concept schemes* (`skos:ConceptScheme`, linked with `skos:inScheme`): one product catalog, one subject list. In this problem the **scheme** of a concept is the text of its id before the first colon, and a concept whose id has no colon is in the scheme `""`. So `"a:dog"` and `"a:x:y"` are in the scheme `"a"`, `"b:perro"` is in `"b"`, and `"dog"` is in `""`. Parent links join concepts of the same scheme only.

**Mappings.** SKOS links concepts of *different* schemes with mapping properties. `skos:exactMatch` says that two concepts mean the same thing and can be used interchangeably; it is symmetric. SKOS also makes it transitive, but this problem follows only the links that were added, one step: otherwise a single mistaken match would merge whole groups of concepts. (`skos:closeMatch`, `skos:broadMatch`, `skos:narrowMatch` and `skos:relatedMatch` say weaker things and are not needed here.)

From this level on, **every method that takes a concept id first resolves it**: an id that was replaced works as its replacement, for all the methods of all the levels. The one exception is the first argument of `deprecate`. In a list of parents, in `expand` results and in all other answers a retired id never appears; its replacement appears in its place. The ids that are still not concepts keep getting the empty answer.

- `rename(concept, label)`: sets the preferred label. The old preferred label becomes the last of the alternative labels, unless it is the same label as the new one or an empty label. An alternative label that is the same label as the new preferred label is removed (it has just been promoted). Statuses: `"unknown-concept"`.
- `removeBroader(narrower, broader)`: removes one parent link. Statuses, in this order: `"unknown-concept"`; `"no-link"` when `broader` is not a parent of `narrower`.
- `deprecate(concept, replacement)`: retires `concept` and sends it to `replacement`, which may itself be retired already, in which case it is resolved first. The retired concept leaves the hierarchy: its parent links are removed, and it is no longer a root, a parent, an ancestor or a descendant. Its labels stay and now find the replacement. Its exact matches move to the replacement. Statuses, in this order: `"unknown-concept"` (either id is not a concept, retired ones included); `"deprecated"` when `concept` is retired already; `"same-concept"` when the resolved replacement is `concept`; `"cross-scheme"` when it is in another scheme; `"has-narrower"` when `concept` still has children, which have to be moved or removed first.
- `resolve(concept)`: the id of the concept that `concept` stands for: the id itself for a concept that is not retired, the end of the chain of replacements for a retired one, and `""` for an id that was never a concept.
- `addExactMatch(first, second)`: records that two concepts are an exact match. Statuses, in this order: `"unknown-concept"`; `"same-scheme"` when both are in the same scheme. Adding the same match again, in either order, is `"ok"`.
- `translate(concepts, scheme)`: translates a set of concepts into `scheme`. The ids are resolved, ids that are not concepts are ignored, and repeats count once. A concept that is already in `scheme` stands for itself. Any other concept is replaced by all the concepts of `scheme` it has an exact match with. The answer is the union, each concept once (so several concepts that map to the same target give it once, and a concept that matches several targets gives all of them), sorted.
- `unmapped(concepts, scheme)`: the resolved concepts of the list that `translate` could not carry over: not in `scheme` and without an exact match in it. Sorted, each once.

`addConcept` and `addBroader` get one more status, `"cross-scheme"`, when a parent is in another scheme than the concept. In `addConcept` it comes after `"unknown-broader"`, and in `addBroader` after `"unknown-concept"` and before `"cycle"`. The parents of `addConcept` are resolved before the check.

### Example 1

<!-- case: ex7 -->

Renaming `sneaker` keeps its id and its links, and `Sneakers` is now an alternative label, so `findByLabel("sneakers")` still finds it. `trainer` has no children, so it can be deprecated in favor of `sneaker`. From then on `resolve("trainer")` is `sneaker`, the ancestors of `trainer` are those of `sneaker`, `narrower("shoes")` lists `sneaker` only, and the label `Trainers` finds `sneaker`.

### Example 2

<!-- case: ex8 -->

Two small schemes, `a` and `b`. Three matches are added: `a:apple` with `b:manzana`, and both `a:pear` and `a:fruit` with `b:fruta`. Translating all four concepts of `a` to `b` gives `b:fruta` once, although two concepts map to it, and `b:manzana`. `a:grocery` has no match, so it is dropped by `translate` and listed by `unmapped`. Two concepts of the same scheme cannot be matched. A concept in the target scheme stands for itself, and the match works in both directions.

## Constraints

- At most 3 * 10^5 calls per test, at most 10^5 concepts, and at most 2 * 10^5 labels in total.
- A list passed to `expand`, `translate` or `unmapped` has at most 10^4 entries.
- A lowest-common-ancestor, expansion or cycle check may be asked on a chain 10^5 concepts deep, so walk with a queue or a stack of your own instead of recursing.
- The answer to a single call has at most 10^5 entries.

## Follow-ups

- A cycle check costs one walk up from the new parent. Can you keep a topological order so that most links are accepted in O(1), and only a link that goes "backwards" needs a walk (the Pearce-Kelly algorithm)?
- `lowestCommonAncestors` visits every ancestor of both concepts. How would you answer it faster for many queries on a fixed taxonomy?
- `expand` copies a whole subtree for every query. How would you cache or precompute descendants, and what must a change of a link invalidate?
- SKOS also has `skos:broadMatch`, `skos:narrowMatch` and `skos:closeMatch`. Which of them could `translate` use for a concept without an exact match, and what does each of them risk?
- Preferred labels in SKOS are per language: a concept may have `Dog` in English and `Perro` in Spanish. How would labels, normalization and the "same label" rule change?

## Hints

### Hint 1

A broader link goes from a child to a parent, but most questions go both ways, so keep two dictionaries: for each concept the set of its parents, and the set of its children. With them, `broader`, `narrower` and `roots` are lookups, and everything else is a walk over these sets.

### Hint 2

To list ancestors nearest first, walk with a queue, one level at a time. Start with the concept. The next level is every parent of the current level that you have not seen. Sort each level by id and append it to the answer. A set of seen concepts keeps a concept from being listed twice when two paths lead to it, and makes the walk end even for a diamond.

### Hint 3

The distance is the level at which the breadth-first walk first meets a concept. A depth-first walk can reach a concept by a long path before a short one, and a sort by id ignores the distance, so neither gives the order the statement asks for.

### Hint 4

For the cycle check ask the opposite question: is `narrower` among `broader` and its ancestors? Walk up from `broader`; if you reach `narrower`, the link would close a loop. Also check `narrower == broader` first.

### Hint 5

Collect the ancestors of each concept, including the concept, as two sets and keep what they share. Now find which of those are *lowest*. A common ancestor is not lowest exactly when one of its children is also a common ancestor, because the common ancestors are closed under going up: if anything below it is common, so is the child on the way.

### Hint 6

Keep a dictionary from a normalized label to the set of concept ids that have it, and normalize both what you store and what you look up. Write the normalization once. For expansion, find the concepts, then run a downward walk from all of them at once with one set of seen concepts.

### Hint 7

Do not rewrite ids when a concept is retired: keep a dictionary `replaced_by` and a `resolve` that follows it. Give every method a first line that resolves its ids. Updating the dictionary so that every retired id points at the final concept (path compression) keeps long chains cheap.

### Hint 8

Store an exact match as two entries, one for each direction, so that the lookup from either scheme is a dictionary access. For `translate`, look at each resolved concept: if its scheme is the target, keep it, otherwise add the partners that are in the target scheme. When you retire a concept, move its partners to the replacement, on both sides.
