/**
 * Versions are parsed once into numbers and identifiers; ranges are expanded into comparator sets.
 * Resolving is a depth-first search that picks the smallest open package name and tries its
 * versions from the highest down, undoing a choice when the rest cannot be resolved. Explaining a
 * failure reruns the search with constraints left out, one at a time.
 */
class SemverResolver {
    private data class Version(val major: Int, val minor: Int, val patch: Int, val pre: List<String>) {
        fun text(): String {
            val core = "$major.$minor.$patch"
            return if (pre.isEmpty()) core else core + "-" + pre.joinToString(".")
        }
    }

    private data class Comparison(val operator: String, val bound: Version)

    private class Dependency(val name: String, val text: String, val sets: List<List<Comparison>>, val edge: Int)

    private class Release(val name: String, val text: String, val version: Version, val dependencies: List<Dependency>)

    private class Root(val name: String, val text: String, val sets: List<List<Comparison>>)

    private val releases = HashMap<String, MutableList<Release>>()
    private val published = ArrayList<Release>()
    private var edges = 0

    // Level 1
    fun isValid(version: String): Boolean = parse(version) != null

    fun compare(first: String, second: String): Int = order(parse(first)!!, parse(second)!!)

    fun sortVersions(versions: List<String>): List<String> =
        versions.mapNotNull { text -> parse(text)?.let { it to text } }
            .sortedWith { (a, x), (b, y) -> order(a, b).takeIf { it != 0 } ?: x.compareTo(y).coerceIn(-1, 1) }
            .map { it.second }

    fun changeKind(before: String, after: String): String {
        val old = parse(before) ?: return "invalid"
        val now = parse(after) ?: return "invalid"
        val found = order(now, old)
        return when {
            found < 0 -> "downgrade"
            found == 0 -> "none"
            now.major != old.major -> "major"
            now.minor != old.minor -> "minor"
            now.patch != old.patch -> "patch"
            else -> "pre-release"
        }
    }

    // Level 2
    fun expandRange(versionRange: String): List<String> =
        expand(versionRange)?.map { set -> set.joinToString(" ") { it.operator + it.bound.text() } } ?: emptyList()

    fun satisfies(version: String, versionRange: String): Boolean {
        val parsed = parse(version) ?: return false
        val sets = expand(versionRange) ?: return false
        return inRange(parsed, sets)
    }

    fun maxSatisfying(versions: List<String>, versionRange: String): String {
        val sets = expand(versionRange) ?: return ""
        var best: Pair<Version, String>? = null
        for (text in versions) {
            val parsed = parse(text) ?: continue
            if (!inRange(parsed, sets)) continue
            val current = best
            val found = if (current == null) 1 else order(parsed, current.first)
            if (found > 0 || (found == 0 && current != null && text > current.second)) best = parsed to text
        }
        return best?.second ?: ""
    }

    // Level 3
    fun publish(name: String, version: String, dependencies: List<List<String>>): String {
        val parsed = parse(version) ?: return "invalid-version"
        val list = releases.getOrPut(name) { ArrayList() }
        if (list.any { order(it.version, parsed) == 0 }) return "duplicate"
        val names = dependencies.map { it[0] }
        val expanded = dependencies.map { expand(it[1]) }
        if (names.toSet().size != names.size || name in names || expanded.any { it == null }) {
            return "invalid-dependency"
        }
        val own = dependencies.mapIndexed { i, pair -> Dependency(pair[0], pair[1], expanded[i]!!, edges + i) }
        edges += dependencies.size
        val release = Release(name, version, parsed, own)
        list.add(release)
        list.sortWith { a, b -> order(b.version, a.version) }
        published.add(release)
        return "ok"
    }

    fun candidates(name: String, versionRange: String): List<String> {
        val sets = expand(versionRange) ?: return emptyList()
        return releases[name].orEmpty().filter { inRange(it.version, sets) }.map { it.text }
    }

    fun resolve(requirements: List<List<String>>): List<String> =
        result(search(roots(requirements), emptySet(), emptySet(), emptyMap()))

    // Level 4
    fun explain(requirements: List<List<String>>): List<String> {
        val roots = roots(requirements)
        if (search(roots, emptySet(), emptySet(), emptyMap()) != null) return emptyList()
        val droppedRoots = HashSet<Int>()
        val droppedEdges = HashSet<Int>()
        val kept = ArrayList<String>()
        roots.forEachIndexed { i, root ->
            droppedRoots.add(i)
            if (search(roots, droppedRoots, droppedEdges, emptyMap()) != null) {
                droppedRoots.remove(i)
                kept.add("root requires ${root.name} ${root.text}")
            }
        }
        for (release in published) {
            for (dependency in release.dependencies) {
                droppedEdges.add(dependency.edge)
                if (search(roots, droppedRoots, droppedEdges, emptyMap()) != null) {
                    droppedEdges.remove(dependency.edge)
                    kept.add("${release.name}@${release.text} requires ${dependency.name} ${dependency.text}")
                }
            }
        }
        return kept
    }

    fun lockedResolve(requirements: List<List<String>>, lock: List<String>): List<String> =
        result(search(roots(requirements), emptySet(), emptySet(), lockOf(lock)))

    fun update(requirements: List<List<String>>, lock: List<String>, unlock: List<String>): List<String> {
        val before = lockOf(lock)
        val preferred = before.filterKeys { it !in unlock }
        val chosen = search(roots(requirements), emptySet(), emptySet(), preferred) ?: return listOf("unsatisfiable")
        val changes = ArrayList<String>()
        for (name in (before.keys + chosen.keys).toSortedSet()) {
            val old = before[name]
            val now = chosen[name]?.text
            when {
                old == null -> changes.add("$name: added $now")
                now == null -> changes.add("$name: removed $old")
                old != now -> changes.add("$name: $old -> $now (${changeKind(old, now)})")
            }
        }
        return changes
    }

    // Versions and ranges
    private fun isNumber(text: String) = NUMBER.matches(text)

    private fun parse(text: String): Version? {
        val rest = text.substringBefore('+')
        if ('+' in text && !text.substringAfter('+').split('.').all { IDENTIFIER.matches(it) }) return null
        val numbers = rest.substringBefore('-').split('.')
        if (numbers.size != 3 || !numbers.all { isNumber(it) }) return null
        val pre = if ('-' in rest) rest.substringAfter('-').split('.') else emptyList()
        if (pre.any { !IDENTIFIER.matches(it) || (DIGITS.matches(it) && !isNumber(it)) }) return null
        return Version(numbers[0].toInt(), numbers[1].toInt(), numbers[2].toInt(), pre)
    }

    private fun compareIdentifiers(a: String, b: String): Int {
        val aNumeric = DIGITS.matches(a)
        val bNumeric = DIGITS.matches(b)
        return when {
            aNumeric && bNumeric -> a.toInt().compareTo(b.toInt())
            aNumeric != bNumeric -> if (aNumeric) -1 else 1
            else -> a.compareTo(b).coerceIn(-1, 1)
        }
    }

    private fun order(a: Version, b: Version): Int {
        if (a.major != b.major) return a.major.compareTo(b.major)
        if (a.minor != b.minor) return a.minor.compareTo(b.minor)
        if (a.patch != b.patch) return a.patch.compareTo(b.patch)
        // A release (no pre-release) sorts after every pre-release of its core.
        if (a.pre.isEmpty() || b.pre.isEmpty()) return b.pre.size.compareTo(a.pre.size).coerceIn(-1, 1)
        for (i in 0 until minOf(a.pre.size, b.pre.size)) {
            val found = compareIdentifiers(a.pre[i], b.pre[i])
            if (found != 0) return found
        }
        return a.pre.size.compareTo(b.pre.size).coerceIn(-1, 1)
    }

    private fun below(major: Int, minor: Int, patch: Int) = Comparison("<", Version(major, minor, patch, listOf("0")))

    private fun floorOf(numbers: List<Int>) =
        Version(numbers.getOrElse(0) { 0 }, numbers.getOrElse(1) { 0 }, numbers.getOrElse(2) { 0 }, emptyList())

    /** The leading numbers of a pattern such as `1`, `1.x` or `1.2.*`, or null. */
    private fun partial(pattern: String): List<Int>? {
        val parts = pattern.split('.')
        if (parts.size > 3) return null
        val numbers = ArrayList<Int>()
        for ((i, part) in parts.withIndex()) {
            if (part in WILDCARDS) return if (parts.drop(i).all { it in WILDCARDS }) numbers else null
            if (!isNumber(part)) return null
            numbers.add(part.toInt())
        }
        return if (numbers.size < 3) numbers else null
    }

    private fun wildcardRange(numbers: List<Int>): List<Comparison> = when (numbers.size) {
        0 -> listOf(Comparison(">=", floorOf(numbers)))
        1 -> listOf(Comparison(">=", floorOf(numbers)), below(numbers[0] + 1, 0, 0))
        else -> listOf(Comparison(">=", floorOf(numbers)), below(numbers[0], numbers[1] + 1, 0))
    }

    private fun caretUpper(numbers: List<Int>): Comparison {
        val floor = floorOf(numbers)
        return when {
            floor.major > 0 || numbers.size == 1 -> below(floor.major + 1, 0, 0)
            floor.minor > 0 || numbers.size == 2 -> below(0, floor.minor + 1, 0)
            else -> below(0, 0, floor.patch + 1)
        }
    }

    private fun expandTerm(term: String): List<Comparison>? {
        val operator = OPERATORS.firstOrNull { term.startsWith(it) } ?: ""
        val pattern = term.substring(operator.length)
        val full = parse(pattern)
        if (full != null) {
            return when (operator) {
                "", "=" -> listOf(Comparison("=", full))
                "~" -> listOf(Comparison(">=", full), below(full.major, full.minor + 1, 0))
                "^" -> listOf(Comparison(">=", full), caretUpper(listOf(full.major, full.minor, full.patch)))
                else -> listOf(Comparison(operator, full))
            }
        }
        val numbers = partial(pattern) ?: return null
        if (operator !in listOf("", "=", "^", "~")) return null
        if (operator == "^" && numbers.isNotEmpty()) return listOf(Comparison(">=", floorOf(numbers)), caretUpper(numbers))
        return wildcardRange(numbers)
    }

    private fun expand(text: String): List<List<Comparison>>? {
        val sets = ArrayList<List<Comparison>>()
        for (piece in text.split("||")) {
            val comparisons = ArrayList<Comparison>()
            for (term in piece.split(' ').filter { it.isNotEmpty() }) {
                comparisons.addAll(expandTerm(term) ?: return null)
            }
            if (comparisons.isEmpty()) return null
            sets.add(comparisons)
        }
        return sets
    }

    private fun holds(version: Version, comparison: Comparison): Boolean {
        val found = order(version, comparison.bound)
        return when (comparison.operator) {
            "=" -> found == 0
            ">" -> found > 0
            ">=" -> found >= 0
            "<" -> found < 0
            else -> found <= 0
        }
    }

    private fun inSet(version: Version, comparisons: List<Comparison>): Boolean {
        if (!comparisons.all { holds(version, it) }) return false
        if (version.pre.isEmpty()) return true
        return comparisons.any {
            it.bound.pre.isNotEmpty() && it.bound.major == version.major && it.bound.minor == version.minor &&
                it.bound.patch == version.patch
        }
    }

    private fun inRange(version: Version, sets: List<List<Comparison>>) = sets.any { inSet(version, it) }

    // The search
    private fun roots(requirements: List<List<String>>) = requirements.map { Root(it[0], it[1], expand(it[1])!!) }

    private fun lockOf(lock: List<String>): Map<String, String> =
        lock.associate { it.substringBefore('@') to it.substringAfter('@') }

    private fun result(chosen: Map<String, Release>?): List<String> =
        chosen?.keys?.sorted()?.map { "$it@${chosen.getValue(it).text}" } ?: emptyList()

    /** The chosen release of every needed package, or null when the constraints in force cannot all hold. */
    private fun search(
        roots: List<Root>,
        droppedRoots: Set<Int>,
        droppedEdges: Set<Int>,
        preferred: Map<String, String>,
    ): Map<String, Release>? {
        val rootRanges = roots.filterIndexed { i, _ -> i !in droppedRoots }
        val chosen = LinkedHashMap<String, Release>()

        fun inForce(release: Release) = release.dependencies.filter { it.edge !in droppedEdges }

        fun solve(): Boolean {
            val needed = rootRanges.map { it.name }.toMutableSet()
            for (release in chosen.values) inForce(release).forEach { needed.add(it.name) }
            val name = needed.filter { it !in chosen }.minOrNull() ?: return true
            val ranges = rootRanges.filter { it.name == name }.map { it.sets }.toMutableList()
            for (release in chosen.values) inForce(release).filter { it.name == name }.forEach { ranges.add(it.sets) }
            val all = releases[name].orEmpty()
            val tries = all.filter { it.text == preferred[name] } + all.filter { it.text != preferred[name] }
            for (release in tries) {
                if (!ranges.all { inRange(release.version, it) }) continue
                val clash = inForce(release).any { dependency ->
                    val other = chosen[dependency.name]
                    other != null && !inRange(other.version, dependency.sets)
                }
                if (clash) continue
                chosen[name] = release
                if (solve()) return true
                chosen.remove(name)
            }
            return false
        }

        return if (solve()) HashMap(chosen) else null
    }

    private companion object {
        val NUMBER = Regex("0|[1-9][0-9]*")
        val IDENTIFIER = Regex("[0-9A-Za-z-]+")
        val DIGITS = Regex("[0-9]+")
        val WILDCARDS = setOf("x", "X", "*")
        val OPERATORS = listOf(">=", "<=", ">", "<", "=", "^", "~")
    }
}
