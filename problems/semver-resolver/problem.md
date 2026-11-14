# Semver Resolver

## Statement

Build `SemverResolver`, the part of a build tool that decides which version of each library a project gets. A project says what it needs ("any 1.x of `lib`, at least 1.2"), every library says what *it* needs, and the resolver has to find one version of each library that keeps everybody happy, or explain why no such choice exists. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working.

**What a version number promises.** Semantic Versioning (SemVer), an open specification, gives each part of a version such as `2.7.1` a meaning. The first number is the *major* version, the second the *minor* version and the third the *patch* version. When the authors of a library release a change, they raise:

- the patch number for bug fixes that change nothing else (`2.7.1` to `2.7.2`);
- the minor number for new features that keep old code working (`2.7.2` to `2.8.0`, the patch back to 0);
- the major number for a change that can break code written for the old version (`2.8.0` to `3.0.0`, minor and patch back to 0).

So a project that works with `2.7.1` should also work with `2.9.4`, but maybe not with `3.0.0`. Major version 0 (`0.4.2`) is special: it marks a library still in early development, where anything may change at any time.

**Why ranges exist.** If every project pinned exact versions, two libraries that pin different patch releases of the same third library could never be used together, and no one would get bug fixes without editing every pin. So a project names a *range*, such as "1.2.0 or newer, but below 2.0.0", and trusts the promise above. The resolver's job is to pick, within all the ranges at once, the newest versions it can.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 55, level 3 by 85 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `SemverResolver()`: creates a resolver with an empty registry.
- A **version** is a string such as `"1.4.2"` or `"2.0.0-rc.1+linux"`; level 1 says exactly which strings are valid. A method that takes a version or a list of versions may receive invalid strings unless its text says otherwise.
- A **range** is a string such as `"^1.2.0"` or `">=1.0.0 <2.0.0 || 3.x"`; level 2 gives its grammar.
- A **package name** is 1 to 20 characters: small letters `a` to `z`, digits and `-`.
- Each level's section describes the methods it adds and their parameters.

## Output

Methods return a boolean, a number, a string or a list of strings, as each method states. Lists are in the order the method states. "Sorted by text" and "smallest name" compare strings by the numeric codes of their characters, so `B` comes before `a` and `10` before `9`.

## Level 1: Versions and precedence

**Valid versions.** A valid version, as SemVer 2.0.0 defines it, has three parts in this order, with no spaces anywhere and nothing before or after:

1. The *core*: three numbers separated by dots, `MAJOR.MINOR.PATCH`. Each number is `0` or a run of digits that does not start with `0`: `1.02.0` and `01.0.0` are invalid.
2. Optionally, a *pre-release*: a `-` followed by one or more identifiers separated by dots, as in `1.0.0-alpha.1`. An identifier is a non-empty run of the characters `0`-`9`, `A`-`Z`, `a`-`z` and `-`. An identifier made of digits only is *numeric*, and must not start with `0` unless it is `0` itself (`1.0.0-01` is invalid). Any other identifier is *alphanumeric*, and may start with `0` (`1.0.0-01a` is valid).
3. Optionally, *build metadata*: a `+` followed by one or more identifiers separated by dots, made of the same characters. Here a digits-only identifier may start with `0` (`1.0.0+001` is valid).

The first `-` after the core starts the pre-release, so `1.0.0-x-y` has the single pre-release identifier `x-y`. A pre-release marks a version that comes *before* its release: `2.0.0-rc.1` is a candidate for `2.0.0`. Build metadata only describes how a version was built.

**Precedence** is the order of versions. To compare two valid versions:

1. Compare major, then minor, then patch, as numbers. The first difference decides: `1.9.0 < 1.10.0`.
2. With an equal core, a version with a pre-release is lower than one without: `1.0.0-alpha < 1.0.0`.
3. With an equal core and two pre-releases, compare the identifiers from left to right; the first difference decides. Two numeric identifiers compare as numbers (`2 < 11`), two alphanumeric ones by their character codes (`Beta < alpha`, since capitals come first), and a numeric identifier is lower than an alphanumeric one (`1.0.0-9 < 1.0.0-a`). When one list of identifiers runs out first and all the identifiers so far are equal, the shorter list is lower: `1.0.0-alpha < 1.0.0-alpha.1`.
4. Build metadata is ignored: `1.0.0+a` and `1.0.0+b` have the *same* precedence.

So `1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-alpha.beta < 1.0.0-beta < 1.0.0-beta.2 < 1.0.0-beta.11 < 1.0.0-rc.1 < 1.0.0`.

Methods:

- `isValid(version)`: whether `version` is valid.
- `compare(first, second)`: `-1` when `first` has lower precedence than `second`, `0` when they have the same precedence, `1` when it is higher. Both arguments are valid.
- `sortVersions(versions)`: the valid versions of the list, from lowest to highest precedence. Versions of equal precedence are sorted by text. Invalid entries are left out; a version that appears twice is listed twice.
- `changeKind(before, after)`: what kind of change it is to go from `before` to `after`, as one word, checked in this order: `"invalid"` when either version is invalid; `"downgrade"` when `after` has lower precedence; `"none"` when they have the same precedence; otherwise `"major"`, `"minor"` or `"patch"` for the first of the three core numbers that differs, and `"pre-release"` when the cores are equal (only the pre-release changed, or it was dropped).

### Example 1

<!-- case: ex1 -->

`1.0.0-alpha+001` has a pre-release and build metadata and is valid; `1.02.0` has a leading zero. `1.9.0` is lower than `1.10.0` because 9 < 10 as numbers, even though `"1.9.0"` sorts after `"1.10.0"` as text. A pre-release is lower than its release, and two versions that differ only in build metadata compare as equal. The sort puts `beta.2` before `beta.11` (2 < 11) and leaves out `latest`, which is not a version.

### Example 2

<!-- case: ex2 -->

Each pair shows one kind of change. Going from `2.0.0-rc.1` to `2.0.0` keeps the core and drops the pre-release: a `"pre-release"` change. Adding build metadata changes nothing in the order, so it is `"none"`. `1.5.0` to `1.4.9` goes down. `1.4` has only two numbers, so it is not a version at all.

## Level 2: Ranges

A **range** is a list of *comparator sets* separated by `||`; a version is in the range when it is in *at least one* set. A set is a list of *terms* separated by one or more spaces; a version is in the set when it meets *every* comparator the terms expand to (and the pre-release rule below). To split a range, cut its text at every `||`; each piece, with the spaces at both ends removed, is a set. The only separator is the space character; any other character outside the grammar makes the range invalid, and so does a set with no term (`""`, `"1.0.0 ||"`).

A **term** is an optional operator followed by a *pattern*, with no space between them (`">= 1.0.0"` is invalid). The operators are `>=`, `<=`, `>`, `<`, `=`, `^` and `~`. A pattern is either a full valid version (pre-release and build metadata allowed) or a *partial* version: one to three parts separated by dots, where each part is a number (written as in level 1) or a *wildcard*, `x`, `X` or `*`, and once a part is a wildcard all the parts after it are wildcards too (`1.x.3` is invalid). So `1`, `1.2`, `1.x`, `1.2.*` and `*` are partial versions. The operators `>=`, `<=`, `>` and `<` take only full versions; no operator, `=`, `^` and `~` take both kinds.

Each term **expands** to one or two *comparators*. A comparator is an operator from `>=`, `<=`, `>`, `<`, `=` and a version, written without spaces and without build metadata. Below, `X`, `Y`, `Z` are numbers, `-PRE` an optional pre-release, `+1` adds one, and a comparator such as `<2.0.0-0` means "below every version of 2.0.0, its pre-releases included": `0` is the lowest pre-release identifier there is.

| Term | Expands to |
|------|------------|
| a full version `V` with no operator or `=` | `=V` |
| `>V`, `>=V`, `<V`, `<=V` | the same, without build metadata |
| `*`, `x`, `X`, `x.x.x` and other all-wildcard patterns, with or without `=`, `^`, `~` | `>=0.0.0` |
| `X`, `X.x`, `X.x.x` (no operator or `=`) | `>=X.0.0 <X+1.0.0-0` |
| `X.Y`, `X.Y.x` (no operator or `=`) | `>=X.Y.0 <X.Y+1.0-0` |
| `~X.Y.Z-PRE` | `>=X.Y.Z-PRE <X.Y+1.0-0` |
| `~X.Y`, `~X` (and with wildcards) | the same as `X.Y` and `X` |
| `^X.Y.Z-PRE` | `>=X.Y.Z-PRE`, then `<X+1.0.0-0` if X > 0, else `<0.Y+1.0-0` if Y > 0, else `<0.0.Z+1-0` |
| `^X.Y` (and `^X.Y.x`) | `>=X.Y.0`, then `<X+1.0.0-0` if X > 0, else `<0.Y+1.0-0` |
| `^X` (and `^X.x`) | `>=X.0.0 <X+1.0.0-0` |

The caret `^` allows every change that keeps the first non-zero number of the core: `^1.2.3` allows new minor and patch releases of 1, but `^0.2.3` allows only patches of 0.2, because in major version 0 a minor release may break things, and `^0.0.3` allows only `0.0.3` itself. The tilde `~` allows patch releases when the minor number is given (`~1.2.3`) and minor releases when it is not (`~1`).

A version meets a comparator when its precedence compares with the comparator's version as the operator says: `=` means the same precedence, so `1.0.0+linux` meets `=1.0.0`.

**Pre-releases need an invitation.** A pre-release is unstable, so a range lets one in only when the range names a pre-release of the same core. A version that has a pre-release is in a set only if it meets every comparator of the set *and* at least one comparator of the set has a version with a pre-release and the same major, minor and patch. So `1.3.0-beta.1` is not in `^1.2.0` even though its precedence lies between the bounds, while it is in `>=1.3.0-beta.0 <1.4.0`. A version without a pre-release only has to meet the comparators. (The expanded bounds such as `<2.0.0-0` carry a pre-release too, but no version of 2.0.0 is below `2.0.0-0`, so they let nothing extra in.)

Methods:

- `expandRange(versionRange)`: one string per comparator set, in order, holding the comparators that the set's terms expand to, in term order, separated by one space. It is `[]` for an invalid range.
- `satisfies(version, versionRange)`: whether the version is in the range; `false` when either one is invalid.
- `maxSatisfying(versions, versionRange)`: the valid version of the list with the highest precedence that is in the range, or `""` when there is none or the range is invalid. Among versions of equal precedence, the one whose text sorts last wins.

### Example 1

<!-- case: ex3 -->

`^1.2.3` allows everything from 1.2.3 up to, but not including, 2.0.0 and its pre-releases; `~1.2.3` stops before 1.3.0, and `^0.2.3` before 0.3.0. A range with `||` has one string per set. `1.9.0` is in `^1.2.3`, `2.0.0` is not, `1.3.0` is not in `~1.2.3`, and `0.3.0` is not in `^0.2.3`. The highest version in `^1.2.3` is `1.9.9`.

### Example 2

<!-- case: ex4 -->

`1.3.0-beta.1` is not in `^1.2.0`: no comparator of that range has a pre-release. It is in `>=1.3.0-beta.0 <1.4.0`, whose first comparator invites pre-releases of 1.3.0, but `1.3.1-beta.1` is not, because its core is 1.3.1. `^0.0.3` allows only 0.0.3. `1.2.3 - 2.0.0` is not in this grammar: the lone `-` is not a valid term. Build metadata never matters for precedence, so `1.0.0+linux` is `=1.0.0`.

## Level 3: Resolving a dependency graph

The resolver now keeps a **registry**: the *releases* of each package (a package name and a version) and, for each release, its *dependencies*: the packages it needs and a range for each. A **requirement** is a pair `[name, range]`; the list a project gives is its *root requirements*.

- `publish(name, version, dependencies)`: adds a release. `dependencies` is a list of pairs `[package, range]`. Statuses, in this order: `"invalid-version"` when the version is invalid; `"duplicate"` when the package already has a release of the same precedence (so `1.0.0+b` is a duplicate of `1.0.0+a`); `"invalid-dependency"` when a range is invalid, a package is listed twice, or a release depends on its own package; otherwise `"ok"`. A refused release is not added. A dependency may name a package that has no release yet.
- `candidates(name, versionRange)`: the published versions of the package that are in the range, from the highest precedence down, as they were published. `[]` for an unknown package or an invalid range.
- `resolve(requirements)`: the chosen releases as `"name@version"` strings (with the version as it was published), sorted by name; `[]` when no choice works. The requirements are pairs `[name, range]` with valid ranges; a name may appear in several of them, and then all of its ranges apply.

**What a resolution is.** At any moment of the search some packages have a *chosen* release. The *requirements on* a package are the root requirements that name it plus the dependencies of the chosen releases that name it, and a package is *needed* when there is at least one requirement on it. A resolution is a choice of one release for every needed package, and for no other, such that every chosen release is in every range required of its package.

**The search.** Many choices may work, so the answer is defined by this search:

1. If every needed package has a chosen release, stop: that is the answer.
2. Otherwise take the needed package without a chosen release whose name is smallest.
3. Go through its releases from the highest precedence down. A release is *acceptable* when it is in every range of the current requirements on the package, and each of its own dependencies on a package that already has a chosen release is met by that release.
4. Choose the first acceptable release and continue at step 1. If that continued search fails, undo the choice (and with it the requirements its dependencies added) and try the next acceptable release.
5. When no release is left, this step fails, and the search goes back to the choice before it. If the very first step fails, there is no resolution.

Going back to an earlier choice when a later one fails is called *backtracking*. Without it, the newest release of the first package could lead into a corner that a slightly older one avoids.

### Example 1

<!-- case: ex5 -->

`lib` has the releases 1.0.0, 1.2.5 and 2.0.0. `1.2.5+rebuild` has the precedence of 1.2.5, so it is a duplicate, and `1.3` is no version. The candidates for `^1.0.0` are listed newest first. To resolve `app ^1.0.0`, the search chooses `app` 1.1.0, the newest, which needs `lib ^1.2.0` and `log ~0.3.0`. The next package by name is `lib`, whose newest acceptable release is 1.2.5 (2.0.0 is not in `^1.2.0`), and then `log` 0.3.1, since 0.4.0 is not in `~0.3.0`.

### Example 2

<!-- case: ex6 -->

Alone, `app` resolves to its newest release, 2.0.0, with `core` 2.1.0. With `theme` as well, the search first chooses `app` 2.0.0 (the smallest name), then `core` 2.1.0 for `^2.0.0`. `theme` 1.0.0 needs `core ^1.0.0`, which the chosen `core` does not meet, so `theme` has no acceptable release. The search goes back: `core` has no other release in `^2.0.0`, so it goes back to `app` and tries 1.0.0, which leads to `core` 1.4.0 and `theme` 1.0.0. When the project insists on `app ^2.0.0`, there is no way out, and the answer is `[]`.

## Level 4: Conflicts and lockfiles

**Explaining a failure.** "No resolution" is not helpful on its own. A useful message names the few requirements that clash, such as "you need `app ^1.0.0` and `lib ^1.0.0`, but every 1.x of `app` needs `lib` 2". This level finds such a set of *constraints*.

The **constraints** of a resolution are the root requirements, written `"root requires <name> <range>"`, followed by the dependencies of every published release, written `"<name>@<version> requires <package> <range>"`. Their order is: the root requirements in the order given, then the releases in the order they were published, each with its dependencies in the order given. Ranges are written as given. Leaving a constraint out means: a root requirement that is left out does not apply, and a dependency that is left out is ignored whenever its release is chosen. Whether a set of constraints can be resolved does not depend on the order of the search.

**Lockfiles.** Once a project has a working resolution, it saves it as a *lockfile*, the list of chosen `"name@version"` strings, so that every later build gets exactly the same versions until someone decides to update. A **lock** is such a list; each package appears in it at most once and every version in it is valid.

Methods:

- `explain(requirements)`: `[]` when `resolve(requirements)` finds a resolution. Otherwise, go through the constraints in order and leave each one out for good if the constraints still in force, without it, still cannot be resolved; keep it otherwise. Return the kept constraints, in order. Every kept constraint is then needed for the conflict: leave any one of them out, and the rest can be resolved.
- `lockedResolve(requirements, lock)`: the same as `resolve`, except in step 3: for a package that has an entry in the lock naming one of its published versions (same text), that release is tried first, and the other releases follow from the highest down. Lock entries for other packages, or for versions that were never published, change nothing. So a locked version is kept whenever it still works.
- `update(requirements, lock, unlock)`: resolve as `lockedResolve` does, but with the lock entries of the packages named in `unlock` left out, so that those packages move to their newest acceptable release. Then report the differences between the old lock and the new resolution, one line per package that differs, sorted by name: `"<name>: added <version>"` for a package that is not in the lock, `"<name>: removed <version>"` for a lock entry whose package is no longer needed, and `"<name>: <old> -> <new> (<kind>)"` for a package whose version text changed, with `<kind>` given by `changeKind(old, new)`. When nothing can be resolved, the answer is `["unsatisfiable"]`.

### Example 1

<!-- case: ex7 -->

`app ^1.0.0` together with `lib ^1.0.0` has no resolution: both releases of `app` need a 2.x of `lib`. All four constraints survive the pass, and together they read as the reason: the root needs `app` 1.x and `lib` 1.x, and every 1.x of `app` needs `lib` 2. Without either root requirement, or either `app` dependency, a resolution exists. `app ^1.0.0` alone can be resolved, so there is nothing to explain. A package that has no release at all explains itself in one line.

### Example 2

<!-- case: ex8 -->

The lock keeps `app` 1.0.0, `lib` 1.2.0 and `log` 0.3.1 although newer releases exist. Unlocking `lib` moves it to 1.3.0, a minor change, and leaves the rest alone. Unlocking everything moves `app` to 1.1.0, which needs `lib ^1.3.0` and no longer needs `log`, so `log` is reported as removed.

## Constraints

- Versions, ranges and lock entries are at most 100 characters of printable ASCII (codes 32 to 126).
- Every major, minor and patch number and every numeric pre-release identifier in the tests has at most 9 digits, so it fits a 32-bit integer even after adding one. Build metadata can be longer; it is never compared.
- At most 100 releases are published per test, each with at most 10 dependencies; a list argument has at most 100 entries.
- The registries of the tests are small, and every `resolve`, `lockedResolve` or `update` call tries at most 2,000 releases; `explain` runs one search per constraint.

## Follow-ups

- The search can try the same failing combination many times. Suppose it learned from each conflict a new rule, such as "no 1.x of `app` together with a 1.x of `lib`", and never tried a combination that breaks a learned rule again. How would that shorten the search, and could the learned rules themselves become the explanation?
- `explain` runs one full search per constraint. How could you skip the constraints that no needed package can ever reach, or remove half of the remaining ones at a time?
- This grammar leaves out hyphen ranges such as `1.2.3 - 2.3.4` (every version from the first to the second, both included) and comparators on partial versions such as `>1.2`. What should each of them expand to?
- A resolver could choose the *lowest* version that satisfies every range instead of the highest. What would that make simpler, and what would it give up?

## Hints

### Hint 1

Parse each valid version once into its parts: three numbers, a list of pre-release identifiers, and the build metadata, which you can then ignore. Most of level 1 is careful parsing: write one small check for "a number with no leading zero" and one for "an identifier", and use them for each part.

### Hint 2

Precedence is a comparison of keys. Compare the three numbers first. For the pre-release, decide what "no pre-release" turns into so that it sorts after every pre-release, and turn each identifier into something that compares numbers as numbers, words as text, and puts numbers first. Many languages compare lists of such keys element by element, shorter list first when one is a prefix of the other.

### Hint 3

Parse a range in two steps: split at `||` and at spaces, then expand each term by its operator and how many numbers it has before the first wildcard. Keep each comparator as an operator plus a parsed version, and write the expansion text from those, so that `expandRange` and `satisfies` share one parser.

### Hint 4

For the caret, find the first non-zero number of the core, counting only the numbers that are given: the upper bound adds one to it and sets the numbers after it to zero, with the `-0` pre-release. When all the given numbers are zero, the last given number is the one that moves.

### Hint 5

The search of level 3 is a recursive function that receives the choices made so far. It computes the requirements from the root and from the chosen releases each time, so undoing a choice is just removing it from the map before trying the next release. Do not keep the requirements in a list that only grows.

### Hint 6

Do not forget the second half of "acceptable": a release whose dependency names a package that is already chosen must agree with that choice now, because nothing will check it later.

### Hint 7

Write the search once, with three extra inputs: the root requirements left out, the dependencies left out, and the preferred version of each package. `resolve`, `explain`, `lockedResolve` and `update` are then a few lines each. For `explain`, number every constraint, keep a set of the ones left out, and grow it as the statement describes, calling the search again for each constraint.
