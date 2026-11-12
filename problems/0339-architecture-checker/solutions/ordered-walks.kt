/**
 * Modules keep the imports as written. The first question after a change resolves every import
 * to the longest declared module that is the import or a dotted prefix of it, and keeps one
 * sorted list of targets per module, so every walk visits neighbours in name order.
 *
 * A breadth-first walk from a sorted list of starts, over sorted neighbours, reaches each module
 * first along the shortest chain that is smallest in name order, so one walk per source name
 * answers every pair of a contract that starts there. Cycles are the strongly connected
 * components, found with two depth-first passes over the graph and its reverse.
 */
class ArchitectureChecker {
    private class Contract(val pairs: List<Pair<String, String>>) {
        var direct = false
        val ignores = mutableSetOf<Pair<String, String>>()
        val exceptions = mutableMapOf<Pair<String, String>, String>()
    }

    private class Walk(val order: List<String>, val parent: Map<String, String?>)

    private class Violation(val key: List<String>, val chain: List<String>)

    private val imports = mutableMapOf<String, List<String>>()
    private var graph: Map<String, List<String>>? = null
    private val contracts = mutableMapOf<String, Contract>()
    private var version: List<Int> = emptyList()
    private var baseline = mutableSetOf<List<String>>()

    // Level 1
    fun addModule(name: String, imports: List<String>): Boolean {
        val isNew = name !in this.imports
        this.imports[name] = imports.toList()
        graph = null
        return isNew
    }

    fun unknownImports(): List<List<String>> =
        imports.flatMap { (module, list) ->
            list.filter { resolve(it) == null }.map { listOf(module, it) }
        }.distinct().sortedWith(ROWS)

    fun dependencies(name: String): List<String> {
        val edges = edges()
        return members(name)
            .flatMap { edges.getValue(it) }
            .filter { !inside(it, name) }
            .distinct()
            .sorted()
    }

    fun transitiveDependencies(name: String): List<String> {
        val walk = walk(members(name), null)
        val depth = HashMap<String, Int>()
        for (module in walk.order) {
            val above = walk.parent[module]
            depth[module] = if (above == null) 0 else depth.getValue(above) + 1
        }
        return walk.order
            .filter { !inside(it, name) }
            .sortedWith(compareBy<String> { depth.getValue(it) }.thenBy { it })
    }

    // Level 2
    fun cycles(depth: Int): List<List<String>> {
        val adjacency = HashMap<String, MutableSet<String>>()
        for ((module, targets) in edges()) {
            val group = groupOf(module, depth)
            val out = adjacency.getOrPut(group) { sortedSetOf() }
            for (target in targets) {
                val other = groupOf(target, depth)
                if (other != group) out.add(other)
            }
        }
        return components(adjacency)
            .filter { it.size > 1 }
            .map { it.sorted() }
            .sortedWith(ROWS)
    }

    fun cycleChain(name: String): List<String> {
        if (name !in imports) return emptyList()
        val edges = edges()
        val walk = walk(listOf(name), null)
        val last = walk.order.firstOrNull { name in edges.getValue(it) } ?: return emptyList()
        return chainOf(last, walk.parent) + name
    }

    // Level 3
    fun addLayers(contract: String, layers: List<String>): Boolean {
        val pairs = layers.indices.flatMap { low -> (0 until low).map { high -> layers[low] to layers[high] } }
        return addContract(contract, pairs)
    }

    fun addForbidden(contract: String, source: String, target: String): Boolean =
        addContract(contract, listOf(source to target))

    fun addIndependence(contract: String, names: List<String>): Boolean =
        addContract(contract, names.flatMap { first -> names.filter { it != first }.map { first to it } })

    fun check(): List<List<String>> = violations().map { it.key + it.chain }

    // Level 4
    fun ignore(contract: String, importer: String, imported: String): Boolean =
        contracts[contract]?.ignores?.add(importer to imported) ?: false

    fun allow(contract: String, importer: String, imported: String, until: String): Boolean {
        val rules = contracts[contract] ?: return false
        val old = rules.exceptions[importer to imported]
        if (old != null && compareVersions(versionKey(old), versionKey(until)) == 0) return false
        rules.exceptions[importer to imported] = until
        return true
    }

    fun setVersion(version: String): List<List<String>> {
        this.version = versionKey(version)
        return contracts.flatMap { (name, rules) ->
            rules.exceptions
                .filter { (_, until) -> compareVersions(versionKey(until), this.version) <= 0 }
                .map { (pair, until) -> listOf(name, pair.first, pair.second, until) }
        }.sortedWith(ROWS)
    }

    fun setMode(contract: String, mode: String): Boolean {
        val rules = contracts[contract] ?: return false
        val direct = mode == "direct"
        if (rules.direct == direct) return false
        rules.direct = direct
        return true
    }

    fun setBaseline(entries: List<List<String>>): Int {
        baseline = entries.map { it.take(3) }.toMutableSet()
        return baseline.size
    }

    fun ratchet(): List<List<String>> {
        val current = violations()
        val broken = current.map { it.key }.toSet()
        val rows = current.filter { it.key !in baseline }.map { listOf("new") + it.key + it.chain }
        val fixed = baseline.filter { it !in broken }.sortedWith(ROWS)
        baseline.removeAll(fixed.toSet())
        return rows + fixed.map { listOf("fixed") + it }
    }

    // Helpers
    private fun resolve(text: String): String? {
        var name = text
        while (name !in imports) {
            val cut = name.lastIndexOf('.')
            if (cut < 0) return null
            name = name.substring(0, cut)
        }
        return name
    }

    private fun edges(): Map<String, List<String>> =
        graph ?: imports.mapValues { (module, list) ->
            list.mapNotNull { resolve(it) }.filter { it != module }.distinct().sorted()
        }.also { graph = it }

    private fun members(name: String): List<String> = imports.keys.filter { inside(it, name) }.sorted()

    /** Breadth-first from the sorted starts over sorted neighbours. */
    private fun walk(starts: List<String>, rules: Contract?): Walk {
        val edges = edges()
        val parent = HashMap<String, String?>()
        starts.forEach { parent[it] = null }
        val order = starts.toMutableList()
        val queue = ArrayDeque(starts)
        while (queue.isNotEmpty()) {
            val module = queue.removeFirst()
            for (target in edges.getValue(module)) {
                if (target !in parent && !skipped(rules, module, target)) {
                    parent[target] = module
                    order.add(target)
                    queue.addLast(target)
                }
            }
        }
        return Walk(order, parent)
    }

    private fun addContract(contract: String, pairs: List<Pair<String, String>>): Boolean {
        if (contract in contracts) return false
        contracts[contract] = Contract(pairs)
        return true
    }

    private fun skipped(rules: Contract?, importer: String, imported: String): Boolean {
        if (rules == null) return false
        val live = rules.exceptions
            .filter { (_, until) -> compareVersions(version, versionKey(until)) < 0 }
            .keys
        return (rules.ignores + live).any { (first, second) ->
            inside(importer, first) && inside(imported, second)
        }
    }

    private fun violations(): List<Violation> {
        val found = ArrayList<Violation>()
        for (name in contracts.keys.sorted()) {
            val rules = contracts.getValue(name)
            for (source in rules.pairs.map { it.first }.distinct().sorted()) {
                val targets = rules.pairs.filter { it.first == source }.map { it.second }
                for ((target, chain) in chains(rules, source, targets)) {
                    found.add(Violation(listOf(name, source, target), chain))
                }
            }
        }
        return found.sortedWith { a, b -> ROWS.compare(a.key, b.key) }
    }

    private fun chains(
        rules: Contract,
        source: String,
        targets: List<String>,
    ): List<Pair<String, List<String>>> {
        val starts = members(source)
        if (rules.direct) {
            return targets.mapNotNull { target -> firstImport(rules, starts, target)?.let { target to it } }
        }
        val walk = walk(starts, rules)
        return targets.mapNotNull { target ->
            walk.order.firstOrNull { inside(it, target) }?.let { target to chainOf(it, walk.parent) }
        }
    }

    /** The starts and their targets are sorted, so the first import found is the smallest. */
    private fun firstImport(rules: Contract, starts: List<String>, target: String): List<String>? {
        val edges = edges()
        for (module in starts) {
            for (other in edges.getValue(module)) {
                if (inside(other, target) && !skipped(rules, module, other)) return listOf(module, other)
            }
        }
        return null
    }

    private companion object {
        val ROWS = Comparator<List<String>> { a, b ->
            (0 until minOf(a.size, b.size)).map { a[it].compareTo(b[it]) }.firstOrNull { it != 0 }
                ?: a.size.compareTo(b.size)
        }

        fun inside(module: String, name: String): Boolean = module == name || module.startsWith("$name.")

        fun groupOf(module: String, depth: Int): String =
            if (depth == 0) module else module.split('.').take(depth).joinToString(".")

        fun chainOf(module: String, parent: Map<String, String?>): List<String> =
            generateSequence(module) { parent[it] }.toList().reversed()

        fun versionKey(text: String): List<Int> = text.split('.').map { it.toInt() }.dropLastWhile { it == 0 }

        fun compareVersions(a: List<Int>, b: List<Int>): Int =
            (0 until minOf(a.size, b.size)).map { a[it].compareTo(b[it]) }.firstOrNull { it != 0 }
                ?: a.size.compareTo(b.size)

        /** Two depth-first passes: finishing order on the graph, then components on its reverse. */
        fun components(adjacency: Map<String, Set<String>>): List<List<String>> {
            val nodes = adjacency.keys.sorted()
            val forward = nodes.associateWith { adjacency.getValue(it).sorted() }
            val reverse = nodes.associateWith { mutableListOf<String>() }
            for (node in nodes) forward.getValue(node).forEach { reverse.getValue(it).add(node) }
            val finished = ArrayList<String>()
            val seen = HashSet<String>()
            for (root in nodes) {
                if (!seen.add(root)) continue
                val stack = ArrayDeque(listOf(root to 0))
                while (stack.isNotEmpty()) {
                    val (node, index) = stack.removeLast()
                    val targets = forward.getValue(node)
                    if (index < targets.size) {
                        stack.addLast(node to index + 1)
                        val target = targets[index]
                        if (seen.add(target)) stack.addLast(target to 0)
                    } else {
                        finished.add(node)
                    }
                }
            }
            val assigned = HashSet<String>()
            val parts = ArrayList<List<String>>()
            for (root in finished.asReversed()) {
                if (!assigned.add(root)) continue
                val part = ArrayList<String>()
                val stack = ArrayDeque(listOf(root))
                while (stack.isNotEmpty()) {
                    val node = stack.removeLast()
                    part.add(node)
                    for (source in reverse.getValue(node)) {
                        if (assigned.add(source)) stack.addLast(source)
                    }
                }
                parts.add(part)
            }
            return parts
        }
    }
}
