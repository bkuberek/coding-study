private val USAGES = setOf("identity", "transform", "aggregate", "filter")
private val MASKABLE = setOf("transform", "aggregate")

private class Edge(val source: String, val target: String, val usage: String, val masking: Boolean) {
    fun carriesValue(): Boolean = usage != "filter" && !masking
}

private val ROWS = Comparator<List<String>> { a, b ->
    for (at in 0 until minOf(a.size, b.size)) {
        val order = a[at].compareTo(b[at])
        if (order != 0) {
            return@Comparator order
        }
    }
    a.size.compareTo(b.size)
}

private fun isColumnRef(text: String): Boolean {
    val parts = text.split(".")
    return parts.size == 2 && parts.all { it.isNotEmpty() }
}

private fun datasetOf(column: String): String = column.substringBefore('.')

/**
 * Columns are nodes named dataset.column, and each lineage edge points from an input column to the
 * column computed from it. Two adjacency maps, forward and backward, answer every walk: a
 * breadth-first search gives distances for the ordered queries, a filter on the edge's usage
 * restricts a walk to the edges a change or a label travels along, and Kosaraju's two passes group
 * the columns that sit on a cycle.
 */
class LineageGraph {
    private val columns = HashMap<String, List<String>>()
    private val edges = mutableListOf<Edge>()
    private val forward = HashMap<String, MutableList<Edge>>()
    private val backward = HashMap<String, MutableList<Edge>>()
    private val labels = HashMap<String, MutableSet<String>>()
    private val published = HashSet<String>()

    // Level 1
    fun addDataset(name: String, columns: List<String>, edges: List<List<String>>): Boolean {
        if (name in this.columns || columns.toSet().size != columns.size) {
            return false
        }
        val pairs = HashSet<Pair<String, String>>()
        val parsed = mutableListOf<Edge>()
        for (edge in edges) {
            if (edge.size !in 3..4 || edge[0] !in columns || !isColumnRef(edge[1])) {
                return false
            }
            val usage = edge[2]
            val masking = edge.size == 4
            if (usage !in USAGES || (masking && (edge[3] != "masking" || usage !in MASKABLE))) {
                return false
            }
            if (!pairs.add(edge[0] to edge[1])) {
                return false
            }
            parsed.add(Edge(edge[1], "$name.${edge[0]}", usage, masking))
        }
        this.columns[name] = columns.toList()
        for (edge in parsed) {
            this.edges.add(edge)
            forward.getOrPut(edge.source) { mutableListOf() }.add(edge)
            backward.getOrPut(edge.target) { mutableListOf() }.add(edge)
        }
        return true
    }

    fun validate(): List<List<String>> {
        val issues = mutableListOf<List<String>>()
        for (edge in edges) {
            val (dataset, column) = edge.source.split(".")
            val declared = columns[dataset]
            when {
                declared == null -> issues.add(listOf("unknown-dataset", edge.target, edge.source))
                column !in declared -> issues.add(listOf("unknown-column", edge.target, edge.source))
            }
        }
        cycles().forEach { issues.add(listOf("cycle") + it) }
        return issues.sortedWith(ROWS)
    }

    fun inputsOf(column: String): List<String> = backward[column].orEmpty().map { it.source }.sorted()

    // Level 2
    fun upstream(column: String): List<String> = byDistance(walk(column, false) { true })

    fun downstream(column: String): List<String> = byDistance(walk(column, true) { true })

    // Level 3
    fun impact(column: String, change: String): List<List<String>> {
        val reached = affected(column, change)
        return byDistance(reached).map { listOf(it, if (reached.getValue(it) == 1) "direct" else "derived") }
    }

    fun isBreaking(column: String, change: String): Boolean {
        if (change != "retype") {
            return affected(column, change).isNotEmpty()
        }
        return typed(column).keys.any { name -> forward[name].orEmpty().any { it.usage != "identity" } }
    }

    fun impactedDatasets(column: String, change: String): List<String> =
        affected(column, change).keys.map(::datasetOf).toSortedSet().toList()

    // Level 4
    fun tag(column: String, label: String): Boolean {
        if (!declared(column)) {
            return false
        }
        return labels.getOrPut(column) { HashSet() }.add(label)
    }

    fun tagsOf(column: String): List<String> {
        val sources = walk(column, false) { it.carriesValue() }
        sources[column] = 0
        return sources.keys.flatMap { labels[it].orEmpty() }.toSortedSet().toList()
    }

    fun publish(dataset: String): Boolean = dataset in columns && published.add(dataset)

    fun exposures(label: String): List<List<String>> {
        val found = mutableListOf<List<String>>()
        for ((source, given) in labels) {
            if (label !in given) {
                continue
            }
            val reached = walk(source, true) { it.carriesValue() }
            reached[source] = 0
            reached.keys.filter { datasetOf(it) in published }.forEach { found.add(listOf(it, source)) }
        }
        return found.sortedWith(ROWS)
    }

    // Helpers
    private fun declared(column: String): Boolean {
        if (!isColumnRef(column)) {
            return false
        }
        val (dataset, name) = column.split(".")
        return columns[dataset]?.contains(name) == true
    }

    /** Breadth-first distances from start along the kept edges; start is in the answer only on a cycle. */
    private fun walk(start: String, ahead: Boolean, keep: (Edge) -> Boolean): MutableMap<String, Int> {
        val distance = HashMap<String, Int>()
        val queue = ArrayDeque<Pair<String, Int>>()
        queue.addLast(start to 0)
        while (queue.isNotEmpty()) {
            val (node, steps) = queue.removeFirst()
            for (edge in (if (ahead) forward else backward)[node].orEmpty()) {
                val next = if (ahead) edge.target else edge.source
                if (keep(edge) && next !in distance) {
                    distance[next] = steps + 1
                    queue.addLast(next to steps + 1)
                }
            }
        }
        return distance
    }

    private fun typed(column: String): Map<String, Int> {
        val typed = walk(column, true) { it.usage == "identity" }
        typed[column] = 0
        return typed
    }

    private fun affected(column: String, change: String): Map<String, Int> {
        if (change == "drop") {
            return walk(column, true) { true }
        }
        if (change == "rename") {
            return forward[column].orEmpty().associate { it.target to 1 }
        }
        val affected = HashMap<String, Int>()
        for ((name, steps) in typed(column)) {
            for (edge in forward[name].orEmpty()) {
                affected[edge.target] = minOf(affected[edge.target] ?: Int.MAX_VALUE, steps + 1)
            }
        }
        return affected
    }

    private fun byDistance(distance: Map<String, Int>): List<String> =
        distance.keys.sortedWith(compareBy<String>({ distance.getValue(it) }, { it }))

    /** Strongly connected groups that hold a cycle, by Kosaraju's two passes. */
    private fun cycles(): List<List<String>> {
        val nodes = edges.flatMap { listOf(it.source, it.target) }.toSortedSet()
        val selfLoops = edges.filter { it.source == it.target }.map { it.source }.toSet()
        val finished = mutableListOf<String>()
        val seen = HashSet<String>()
        for (root in nodes) {
            if (!seen.add(root)) {
                continue
            }
            val stack = ArrayDeque<Pair<String, Int>>()
            stack.addLast(root to 0)
            while (stack.isNotEmpty()) {
                val (node, at) = stack.removeLast()
                val out = forward[node].orEmpty()
                if (at == out.size) {
                    finished.add(node)
                    continue
                }
                stack.addLast(node to at + 1)
                val next = out[at].target
                if (seen.add(next)) {
                    stack.addLast(next to 0)
                }
            }
        }
        val grouped = HashSet<String>()
        val groups = mutableListOf<List<String>>()
        for (root in finished.asReversed()) {
            if (!grouped.add(root)) {
                continue
            }
            val members = mutableListOf(root)
            val pending = ArrayDeque(listOf(root))
            while (pending.isNotEmpty()) {
                for (edge in backward[pending.removeLast()].orEmpty()) {
                    if (grouped.add(edge.source)) {
                        members.add(edge.source)
                        pending.addLast(edge.source)
                    }
                }
            }
            if (members.size > 1 || root in selfLoops) {
                groups.add(members.sorted())
            }
        }
        return groups
    }
}
