/**
 * Rows are indexed once by id, then every question is a walk over the index. Nothing here
 * recurses: the outline and the subtree sizes use an explicit stack and a breadth-first order, so
 * a chain of 10^5 managers is as safe as a flat one.
 */
class OrgChart {
    private var ids: List<String> = emptyList()
    private var parents: Map<String, String> = emptyMap()
    private var names: Map<String, String> = emptyMap()
    private var kids: Map<String, List<String>> = emptyMap()
    private var orphanIds: List<String> = emptyList()
    private var tops: List<String> = emptyList()
    private var attached: Set<String> = emptySet()
    private var sizes: Map<String, Int> = emptyMap()
    private var cycleList: List<List<String>> = emptyList()

    // Level 1
    fun load(rows: List<List<String>>) {
        ids = rows.map { it[0] }
        parents = rows.associate { it[0] to it[1] }
        names = rows.associate { it[0] to it[2] }
        val grouped = HashMap<String, MutableList<String>>()
        for (id in ids) {
            grouped.getOrPut(parents.getValue(id)) { mutableListOf() }.add(id)
        }
        kids = grouped
        orphanIds = ids.filter { parents.getValue(it).isNotEmpty() && parents.getValue(it) !in names }
        val orphanSet = orphanIds.toSet()
        tops = ids.filter { parents.getValue(it).isEmpty() || it in orphanSet }
        val order = ArrayList(tops)
        val reached = HashSet(tops)
        var next = 0
        while (next < order.size) {
            for (kid in kids[order[next]].orEmpty()) {
                reached.add(kid)
                order.add(kid)
            }
            next++
        }
        attached = reached
        val subtree = HashMap<String, Int>()
        for (id in order) {
            subtree[id] = 1
        }
        for (at in order.indices.reversed()) {
            val parent = parents.getValue(order[at])
            val parentSize = subtree[parent]
            if (parentSize != null) {
                subtree[parent] = parentSize + subtree.getValue(order[at])
            }
        }
        sizes = subtree
        cycleList = findCycles()
    }

    fun roots(): List<String> = kids[""].orEmpty().toList()

    fun nameOf(employee: String): String = names[employee] ?: ""

    fun children(employee: String): List<String> = if (employee in names) kids[employee].orEmpty().toList() else emptyList()

    // Level 2
    fun orphans(): List<String> = orphanIds.toList()

    fun cycles(): List<List<String>> = cycleList.map { it.toList() }

    // Level 3
    fun chain(employee: String): List<String> {
        if (employee !in attached) {
            return emptyList()
        }
        val path = mutableListOf(employee)
        var parent = parents.getValue(employee)
        while (parent in names) {
            path.add(parent)
            parent = parents.getValue(parent)
        }
        return path
    }

    fun lowestCommonManager(first: String, second: String): String {
        val aboveSecond = chain(second).toSet()
        return chain(first).firstOrNull { it in aboveSecond } ?: ""
    }

    // Level 4
    fun subtreeSize(employee: String): Int = sizes[employee] ?: 0

    fun outline(order: String): List<String> {
        val lines = mutableListOf<String>()
        val stack = ArrayDeque<Pair<String, Int>>()
        for (top in sorted(tops, order).asReversed()) {
            stack.addLast(top to 0)
        }
        while (stack.isNotEmpty()) {
            val (current, depth) = stack.removeLast()
            lines.add("  ".repeat(depth) + names.getValue(current) + " (" + current + ")")
            for (kid in sorted(kids[current].orEmpty(), order).asReversed()) {
                stack.addLast(kid to depth + 1)
            }
        }
        return lines
    }

    private fun sorted(members: List<String>, order: String): List<String> = when (order) {
        "name" -> members.sortedWith(compareBy<String>({ names.getValue(it) }, { it }))
        "size" -> members.sortedWith(compareBy<String>({ -sizes.getValue(it) }, { names.getValue(it) }, { it }))
        else -> members
    }

    private fun findCycles(): List<List<String>> {
        val position = ids.withIndex().associate { it.value to it.index }
        val seen = HashSet(attached)
        val found = mutableListOf<List<String>>()
        for (start in ids) {
            val walk = mutableListOf<String>()
            var current = start
            while (current !in seen) {
                seen.add(current)
                walk.add(current)
                current = parents.getValue(current)
            }
            val at = walk.indexOf(current)
            if (at >= 0) {
                val cycle = walk.subList(at, walk.size)
                val first = cycle.indices.minByOrNull { position.getValue(cycle[it]) } ?: 0
                found.add(cycle.subList(first, cycle.size) + cycle.subList(0, first))
            }
        }
        return found.sortedBy { position.getValue(it[0]) }
    }
}
