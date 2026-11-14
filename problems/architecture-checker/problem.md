# Architecture Checker

## Statement

Build `ArchitectureChecker`, a tool that reads how the parts of a program use one another and checks rules about that structure. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**Modules and imports.** A large program is split into *modules*, usually one file each, and each with a job: showing a web page, computing prices, talking to a database. When the code of one module needs something defined in another, it says so with an *import*. If `app.services.orders` imports `app.db.session`, the orders code uses code written in the session module. Module names are *dotted*, and the parts work like folders: `app.db.session` is the module `session` in the *package* `app.db`, which is itself in the package `app`. A package groups the modules below it, the way a folder groups its files.

**The dependency graph.** When module A imports module B, A *depends on* B: a change to B may force a change to A, and A cannot be tested or reused without B. Draw every module as a dot and every import as an arrow from the importing module to the imported one, and you get the *dependency graph*, a directed graph. Following its arrows answers useful questions. What does this module use directly? What does it use through other modules (its *transitive* dependencies)? Where do the arrows run in a circle?

**Why rules about structure matter.** Without rules, any module may import any other, and over time the graph becomes a tangle in which every change ripples everywhere. A common rule is *layering*: sort the modules into layers, such as the user-facing code on top, the business rules in the middle and storage at the bottom, and let the arrows point down only. Then the business rules can be tested without a web server, and the storage can be replaced without touching the pages. Rules like this are easy to state and easy to break by accident, one import at a time, often far from the place where the damage shows. This checker finds such breaks and shows the chain of imports behind each one.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 35, level 2 by 60, level 3 by 85 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `ArchitectureChecker()`: creates an empty checker.
- A **module name** is one or more *parts* joined by single dots, such as `app`, `app.db` or `app.db.session`. A part is 1 to 20 letters, digits and underscores, and a name has at most 8 parts. Names are compared exactly as given: `App` and `app` are different names.
- An **import** is written like a module name. It may name a declared module, something defined inside a module (such as a class), or something outside the program.
- Each level's section describes the methods it adds and their parameters.

## Output

Most methods that change the checker return a `bool` or an `int`. Questions return a list of module names, a list of rows (each row a list of strings), or a single row. Where a method says "sorted", strings are compared by the numeric codes of their characters: `.` comes before the digits, the digits before capital letters, capital letters before `_`, and `_` before small letters, so `app.db` < `app.db.models` < `app.db_x` < `app.dbx`. Two lists of strings are compared element by element, and the first element that differs decides; a list that is the start of a longer one comes first.

## Level 1: Modules and imports

- `addModule(name, imports)`: declares the module `name` with its imports, as they are written in its source. It returns `true` when the module is new. When `name` is already declared, the new list replaces the old one (the file changed) and the call returns `false`. An import that appears twice in the list counts once.

**Resolving an import.** Imports are written by people, so the checker has to work out which module each one means. An import *resolves* to the **longest declared module name that equals the import, or that the import starts with, followed by a dot**:

- `app.db.session` resolves to the module `app.db.session` when it is declared.
- `app.db.models.Order` names something defined inside a module, here a class: when `app.db.models` is declared and `app.db.models.Order` is not, it resolves to `app.db.models`. If `app.db` were declared too, the longer name `app.db.models` would still win.
- In the import, the module name must be followed by a dot: `app.dbx` never resolves to `app.db`.
- An import that resolves to no declared module is **unknown**: a library from outside the program such as `json`, a typo, or a package that has no module of its own. With only `shop.catalog.items` declared, the import `shop.catalog` is unknown: there is a folder, but no file to depend on.
- An import that resolves to the importing module itself, such as `shop.pricing.Rule` written in `shop.pricing`, is neither a dependency nor unknown: a module does not depend on itself.

Imports are resolved against all the modules declared so far, every time a question is asked, so the order of the `addModule` calls never matters: an import of a module that is declared later starts to count when that module is declared.

**A name covers a package.** A `name` given to a question stands for the module of that name, if one is declared, *and every declared module inside it*: the modules whose names start with `name` followed by a dot. So `app.db` covers `app.db`, `app.db.models` and `app.db.session`, but not `app.dbx`. A name that covers no declared module covers nothing. An import between two modules that a name covers stays inside the package, and is not a dependency of it.

- `unknownImports()`: every unknown import, as rows `[module, import]` with the import as written, sorted by module, then by import, each row once.
- `dependencies(name)`: the modules that the modules covered by `name` import directly (their resolved imports), leaving out the modules that `name` covers, sorted.
- `transitiveDependencies(name)`: every module reached from the modules covered by `name` by following one or more imports, leaving out the modules that `name` covers. The list is **nearest first**: the *distance* of a module is the smallest number of imports on a chain to it from any covered module, and the modules are listed by distance, then by name (sorted). A chain that leads back to a covered module adds nothing.

**Walking the graph.** A transitive question is a walk: start from the covered modules, follow their imports, then the imports of what you reached, and so on. Keep a set of the modules already reached, or a cycle sends the walk round forever. Walking breadth-first, one distance at a time, gives the distances for free.

### Example 1

<!-- case: ex1 -->

`json` and `os` resolve to no declared module, so they are unknown. `app.db.models.Order` names the class `Order` inside `app.db.models`, and resolves to that module. `app.web` covers `app.web.views`. From `app.web.views`, `app.services.orders` is at distance 1, and the two database modules at distance 2, in name order. `app.db` covers both database modules, and their only import goes from one to the other, so the package has no dependencies. `app.services` reaches both database modules at distance 1.

### Example 2

<!-- case: ex2 -->

When `shop.cart` is declared, neither of its imports names a declared module: both are unknown, and it has no dependencies. Declaring `shop.pricing` makes `shop.pricing.Discount` resolve to it, and `shop.pricing.Rule`, written inside `shop.pricing`, resolves to `shop.pricing` itself and is left out. Once `shop.catalog.items` exists, `shop.catalog` is still unknown: it is a package with no module of its own. Declaring `shop.cart` again returns `false` and replaces its imports.

## Level 2: Import cycles

A **cycle** is a chain of imports that comes back to where it started: `orders.service` imports `orders.repo`, which imports `orders.service`. Cycles are a common way for a structure to decay, and they hurt in several ways:

- The modules on a cycle can only be understood, tested, built and released together, because each needs all the others. A cycle of two tends to grow.
- Loading can break. In a language that runs a module's top-level code when it is first imported, one module of a cycle starts running while the other is only half set up. Python's Programming FAQ shows two modules that import names from each other and fail in this way. Go refuses cycles outright: its specification makes it illegal for a package to import itself, directly or indirectly.
- Layers stop meaning anything. When a lower module reaches a higher one and the higher one reaches the lower, neither is below the other.

The Acyclic Dependencies Principle turns this into a design rule: the dependency graph of components should have no cycles.

Graph theory has the right tool. Two modules are *strongly connected* when each one reaches the other by following imports. A **strongly connected component** is a largest group of modules that are all strongly connected to each other. Every cycle lies inside one component, and every module of a component with two or more members lies on a cycle. Reporting the components reports each tangle once, however many cycles overlap in it. Since an import of a module by itself is left out at level 1, a single module is never a cycle here.

- `cycles(depth)`: every strongly connected component with at least two members, each as the sorted list of its members, the components sorted by their first member. With `depth` 0 the members are modules. With `depth` 1 or more, each module is first replaced by its **group**, the name made of its first `depth` parts (`app.web.views` at depth 2 is `app.web`; a module with at most `depth` parts is its own group), and the components are those of the graph of groups: an arrow from group G to group H when a module of G imports a module of H and G differs from H. `depth` is from 0 to 8.
- `cycleChain(name)`: one cycle through the module `name`, to explain it: the modules from `name` along imports back to `name`, with `name` first and last. It is the **shortest** such cycle (the fewest imports), and among the shortest ones the smallest, comparing the lists element by element. When `name` is not a declared module, or no cycle passes through it, the answer is `[]`.

**Grouping.** Modules can be free of cycles while their packages are not. If `app.web.views` imports `app.core.rules`, and `app.core.audit` imports `app.web.format`, no module is on a cycle, but the package `app.web` needs `app.core` and `app.core` needs `app.web`: the two packages cannot be separated. Depth 2 shows it.

### Example 1

<!-- case: ex3 -->

There are two cycles: `orders.service` and `orders.repo` import each other, and the three billing modules form a ring. Each component is listed once with its modules sorted, and the billing component comes first because its first module sorts first. `cycleChain("billing.tax")` follows the ring from `billing.tax` back to itself. `orders.api` imports a module on a cycle without being on one.

### Example 2

<!-- case: ex4 -->

No module is on a cycle. At depth 2 the modules become `app.web` and `app.core`: `app.web` imports `app.core` (views imports rules) and `app.core` imports `app.web` (audit imports format), so the two packages form a cycle. At depth 1 every module is in the group `app`, and an import inside a group is not an arrow.

## Level 3: Contracts and chains

A team writes its rules down as **contracts**, data that the checker reads. Each contract has a name, unique among all contracts: the `add` methods return `false` and change nothing when the name is taken, and `true` otherwise. The names inside a contract cover packages as at level 1.

- `addLayers(contract, layers)`: the names in `layers` are layers, highest first. A module covered by a higher layer may import modules of the lower layers; a module covered by a lower layer must not depend on any module of a higher layer.
- `addForbidden(contract, source, target)`: the modules covered by `source` must not depend on the modules covered by `target`. The rule goes one way only: `target` may depend on `source`.
- `addIndependence(contract, names)`: no module covered by one of the names may depend on a module covered by another of the names, in either direction.

To **depend on** means *directly or through other modules*. If `app.data.orders` imports `app.helpers.format`, which imports `app.web.routes`, then the data layer depends on the web layer, although no data module imports a web module. The modules on the chain in between can be any modules, including modules of other names of the same contract.

A contract is a list of **pairs** `(from, to)` of names, where `from` must not depend on `to`: for layers, every lower layer with every higher layer, not only with its neighbour; for a forbidden import, the one pair `(source, target)`; for independence, every ordered pair of two different names. A pair is **broken** when some module covered by `from` reaches some module covered by `to` through one or more imports.

- `check()`: one row for every broken pair of every contract, `[contract, from, to, m1, m2, ..., mk]`, where `m1, ..., mk` is the **chain**: modules along imports, each importing the next, from a module covered by `from` (`m1`) to a module covered by `to` (`mk`). The chain is the shortest one (the fewest imports) from any module of `from` to any module of `to`, and among the shortest ones the smallest, comparing element by element. The rows are sorted by contract name, then `from`, then `to`. When nothing is broken the answer is `[]`.

Contracts are checked against the modules as they are when `check` is called, so a contract can be added before the modules it names.

**Why the shortest chain.** A broken rule only helps if you can find the import to fix. The chain is the evidence: some import on it should not be there, and the shortest chain has the fewest suspects. One bad import often breaks several pairs at once, and removing it fixes them all.

Limits: at most 20 contracts. A layers contract has 2 to 10 layers and an independence contract 2 to 10 names. The names of one contract are distinct and none covers another (no name starts with another followed by a dot), and the `source` and `target` of a forbidden import do not cover each other either. Contract names are 1 to 30 letters, digits, `-` and `_`.

### Example 1

<!-- case: ex5 -->

`app.helpers.format` imports `app.web.routes`, in the top layer. No data module imports a web module, but `app.data.orders` reaches `app.web.routes` through `app.helpers.format`, so data depends on web. Through the web module it also reaches `app.service.checkout`, so data depends on service, and `app.service.checkout` reaches web through the data module. One import breaks three pairs, and when `app.helpers.format` is declared again without it, all three are fixed.

### Example 2

<!-- case: ex6 -->

`shipping.core` imports `billing.core.Invoice`, which resolves to `billing.core`, so the two areas are not independent, in one direction. The name `bounded` is taken, so the second contract of that name is refused. At first, nothing in `shared` reaches billing; once `shared.ids` imports `billing.api`, the forbidden rule breaks. Shipping now also reaches billing through `shared.ids`, but its direct import is shorter, so its chain stays the same.

## Level 4: Exceptions, modes and a ratchet

A real codebase rarely meets its rules on the first day. This level adds the tools that let a team adopt rules step by step.

**Ignores and exceptions.**

- `ignore(contract, importer, imported)`: from now on the contract skips every import from a module covered by `importer` to a module covered by `imported`, as if it were not there. Other contracts still see it. It returns `false` when the contract does not exist or already has this ignore, and `true` otherwise, even when it covers no import yet.
- `allow(contract, importer, imported, until)`: an **exception** that skips the same imports as an ignore, but only while the current version is *before* `until`; from version `until` on, the imports count again. It returns `false` when the contract does not exist. When the contract already has an exception for the same `importer` and `imported`, the new version replaces the old one and the call returns `true`, unless the two versions are equal, in which case it returns `false` and nothing changes.
- `setVersion(version)`: sets the current version, which starts at `0`. The version may go up or down. It returns every exception of every contract that is expired at the new version, because its `until` is equal to it or before it, as rows `[contract, importer, imported, until]` with `until` as it was given, sorted by contract, then importer, then imported. The list says which exceptions protect nothing at this version and can be removed from the contract. An expired exception stays in the checker, and applies again if the version goes back below its `until`.

A **version** is one to four numbers joined by dots, such as `2`, `1.10` or `3.0.1`, each from 0 to 999999 and written without leading zeros. Versions compare part by part *as numbers*, from the left: `1.9` is before `1.10`, because 9 is less than 10. A missing part counts as 0, so `2`, `2.0` and `2.0.0` are equal. Semantic Versioning 2.0.0 compares its major, minor and patch numbers in the same way; this problem allows one to four parts and has no pre-release labels.

Skipping an import is not the same as forgiving a pair. When an import on the chain of a broken pair is skipped, the checker looks for the next shortest chain, and the pair stays broken if there is one.

**Direct and transitive checking.**

- `setMode(contract, mode)`: `mode` is `"transitive"`, the default, which checks chains as at level 3, or `"direct"`, which checks single imports only. In direct mode a pair is broken when a module covered by `from` itself imports a module covered by `to`, and its chain is that one import, `[importer, imported]`: the smallest such pair, by importer, then by imported. It returns `false` when the contract does not exist or already has that mode.

Direct checking is cheaper and its reports are short, and it misses exactly the far-away chains of level 3. Ignores and exceptions apply in both modes.

**A ratchet.** On a codebase with a hundred old breaks, a rule that fails until every one is fixed gets switched off within a week. A *ratchet* records the breaks that exist today, the **baseline**, fails only on new ones, and tightens whenever an old one is fixed, so the number of breaks can only go down.

- `setBaseline(entries)`: replaces the baseline with `entries`, a list of rows `[contract, from, to]`, the way an earlier `check` identified its broken pairs. It returns the number of distinct entries. At most 200 entries per call.
- `ratchet()`: compares the broken pairs that `check()` would report with the baseline. A broken pair is identified by `[contract, from, to]`: its chain may change without making it new. Every broken pair that is not in the baseline is **new**, a row `["new", contract, from, to, m1, ..., mk]` with its chain. Every baseline entry that is not broken any more is **fixed**, a row `["fixed", contract, from, to]`, and it leaves the baseline, so that it counts as new if it ever breaks again. New breaks never join the baseline. The answer lists the new rows first, sorted by contract, then `from`, then `to`, and then the fixed rows in the same order. Before the first `setBaseline` the baseline is empty.

`check()` keeps reporting every broken pair; the baseline only changes what `ratchet()` says.

### Example 1

<!-- case: ex7 -->

The domain layer breaks the rule twice, as `app.domain.legacy` imports `app.web.page` and `app.domain.price` imports `app.web.format`. Both chains are one import long, and the first is smaller. Ignoring the imports from legacy to the web layer reveals the second chain: the pair is still broken. The exception for price hides it until version 2.0. At 1.10 the exception still holds, since 1.10 is before 2.0. At version 2, which equals 2.0, it expires: `setVersion` lists it, and the break is back. A new exception until 2.1 replaces the old one. A contract that does not exist cannot get an ignore.

### Example 2

<!-- case: ex8 -->

The core reaches the database module through `core.util` and `infra.log`. In direct mode only single imports count, and no core module imports `infra.db` itself; setting the same mode again returns `false`. The baseline holds the break of `core-pure` and one of a rule that no longer exists: the ratchet reports the second as fixed and drops it. Then `core.model` imports `infra.db` directly. The chain of the known break changes, but it is the same pair, so nothing is new. The independence contract added last breaks a pair that is not in the baseline, which the ratchet reports as new.

## Constraints

- At most 2,000 calls per test, at most 300 declared modules, and at most 30 imports in one `addModule` call.
- Every argument is in the form its level describes.

## Follow-ups

- A real checker reads the imports from source files. What makes that hard: imports inside functions, imports that run only on some platforms, modules loaded by a name built at run time?
- Some teams also forbid a layer to skip the layer below it. How would you add a contract for that, and what chain would explain a break?
- The ratchet identifies a break by its pair. What would change if it counted the imports behind each pair instead, so that adding a second bad import to a known pair also fails?
- `check` walks the graph once per name a contract starts from. With many contracts on one large graph, which walks could be shared, and what could be kept between two checks when only one module changed?
- How would you find the one import whose removal fixes the most broken pairs?

## Hints

### Hint 1

Think of the graph as a dictionary: for each module, the list of modules it imports. Before you can fill it, turn each written import into a module. Try the whole import first; if no module has that name, cut off the last part at a dot and try again, until you find a declared module or run out of parts.

### Hint 2

Write one small function that says whether a module is covered by a name: the module equals the name, or starts with the name followed by a dot. Use it everywhere a name appears: in dependencies, in contracts and in ignores. Leaving out the dot is the most common mistake.

### Hint 3

A breadth-first search takes modules from a queue in order of distance. When a name covers several modules, what should be in the queue, and marked as reached, before the first step?

### Hint 4

Look up strongly connected components. Two classic methods find all of them in time proportional to the size of the graph: one depth-first search that tracks, for each module, the earliest module still on its stack that it can reach, or two depth-first searches, the second over the reversed graph. For grouping, build the graph of groups first and run the same search on it.

### Hint 5

Start a breadth-first search with the starting modules sorted, and visit each module's imports in sorted order. In what order do the modules come out of the queue, compared with the order of their chains? What does that say about the first chain along which a module is reached?

### Hint 6

A pair is broken whatever chain shows it, so one walk from the modules of a `from` name can answer every pair that starts at that name. A skipped import should be left out during the walk, not after it: otherwise a second chain stays hidden.

### Hint 7

Versions: compare lists of numbers, after removing the zeros at the end. The ratchet only moves one way: when an entry is fixed, what must happen to the baseline so that the same break counts as new later?

### Hint 8

Resolve every import once after each change, and keep for each module its sorted list of resolved imports. For a walk, put the sorted starting modules in the queue and remember, for every module, the module it was first reached from: the queue holds modules in the order of their chains, so this first chain is the shortest and, among those, the smallest, and following the links back rebuilds it. `transitiveDependencies` sorts the reached modules by distance, then name. `cycleChain(name)` walks from `name` alone, and the first module taken from the queue that imports `name` closes the cycle. For a contract, walk once from each `from` name with the skipped imports left out, and for each `to` name take the first module it covers in the order the walk reached them (direct mode: the smallest single import). The ratchet compares a map from `(contract, from, to)` to chain with the baseline set, and removes the fixed entries from that set.
