private const val RING_SIZE = 1L shl 32
private const val FNV_OFFSET_BASIS = 2166136261L
private const val FNV_PRIME = 16777619

/** FNV-1a, 32 bits, over the UTF-8 bytes; `Int` multiplication wraps at 32 bits. */
private fun fnv1a(text: String): Long {
    var value = FNV_OFFSET_BASIS.toInt()
    for (byte in text.toByteArray(Charsets.UTF_8)) {
        value = (value xor (byte.toInt() and 0xff)) * FNV_PRIME
    }
    return value.toLong() and 0xffffffffL
}

/**
 * Point 0 is the bare name and point i is `i#node`: the number goes first, because FNV-1a mixes
 * the first bytes of a text far better than its last ones.
 */
private fun labelsOf(node: String, count: Int): List<String> = listOf(node) + (1 until count).map { "$it#$node" }

private data class Point(val position: Long, val label: String, val node: String)

private val ringOrder = compareBy<Point>({ it.position }, { it.label })

/** The index of the first point at or after the position, wrapping to 0 past the last one. */
private fun startOf(ring: List<Point>, position: Long): Int {
    var low = 0
    var high = ring.size
    while (low < high) {
        val middle = (low + high) ushr 1
        if (ring[middle].position < position) low = middle + 1 else high = middle
    }
    return if (low < ring.size) low else 0
}

private fun ownerIn(ring: List<Point>, position: Long): String =
    if (ring.isEmpty()) "" else ring[startOf(ring, position)].node

private fun moduloIn(order: List<String>, key: String): String =
    if (order.isEmpty()) "" else order[(fnv1a(key) % order.size).toInt()]

/**
 * The ring is a list of points sorted by position and then by label, which is the ring order with
 * its tie-break. A key's owner is the first point at or after the key's position, found by binary
 * search, wrapping to the first point.
 */
class HashRing {
    private var points: List<Point> = emptyList()
    private val joined = ArrayList<String>()
    private val counts = HashMap<String, Int>()
    private val tracked = HashSet<String>()
    private var report: List<List<String>> = emptyList()

    // Level 1
    fun positionOf(text: String): Long = fnv1a(text)

    fun addNode(node: String): Long = if (addVirtualNode(node, 1)) fnv1a(node) else -1L

    fun removeNode(node: String): Boolean {
        if (node !in counts) return false
        val before = owners()
        points = points.filter { it.node != node }
        joined.remove(node)
        counts.remove(node)
        makeReport(before)
        return true
    }

    fun nodes(): List<String> = joined.sorted()

    fun nodeFor(key: String): String = ownerIn(points, fnv1a(key))

    fun moduloNodeFor(key: String): String = moduloIn(joined, key)

    fun countMoves(keys: List<String>, node: String): List<Int> {
        if (node in counts) return emptyList()
        val grown = (points + Point(fnv1a(node), node, node)).sortedWith(ringOrder)
        val order = joined + node
        val ringMoves = keys.count { ownerIn(points, fnv1a(it)) != ownerIn(grown, fnv1a(it)) }
        val moduloMoves = keys.count { moduloIn(joined, it) != moduloIn(order, it) }
        return listOf(ringMoves, moduloMoves)
    }

    // Level 2
    fun addVirtualNode(node: String, count: Int): Boolean {
        if (node in counts || count < 1) return false
        val before = owners()
        points = (points + labelsOf(node, count).map { Point(fnv1a(it), it, node) }).sortedWith(ringOrder)
        joined.add(node)
        counts[node] = count
        makeReport(before)
        return true
    }

    fun positions(node: String): List<Long> = counts[node]?.let { count -> labelsOf(node, count).map { fnv1a(it) } } ?: emptyList()

    fun arcShare(): List<Long> {
        val share = HashMap<String, Long>()
        points.forEachIndexed { index, point ->
            val previous = points[(index + points.size - 1) % points.size].position
            val arc = if (index > 0) point.position - previous else point.position - previous + RING_SIZE
            share[point.node] = (share[point.node] ?: 0L) + arc
        }
        return nodes().map { share[it] ?: 0L }
    }

    fun keyCounts(keys: List<String>): List<Int> {
        val owned = keys.groupingBy { nodeFor(it) }.eachCount()
        return nodes().map { owned[it] ?: 0 }
    }

    // Level 3
    fun trackKeys(keys: List<String>): Int {
        tracked.addAll(keys)
        return tracked.size
    }

    fun lastMoves(): List<List<String>> = report.map { it.toList() }

    fun ownedKeys(node: String): List<String> =
        if (node !in counts) emptyList() else tracked.filter { nodeFor(it) == node }.sorted()

    // Level 4
    fun replicas(key: String, count: Int): List<String> {
        if (count < 1 || points.isEmpty()) return emptyList()
        val start = startOf(points, fnv1a(key))
        val found = ArrayList<String>()
        var step = 0
        while (step < points.size && found.size < count) {
            val node = points[(start + step) % points.size].node
            if (node !in found) found.add(node)
            step++
        }
        return found
    }

    fun assignBounded(keys: List<String>, numerator: Int, denominator: Int): List<String> {
        if (points.isEmpty() || keys.isEmpty()) return emptyList()
        val total = (denominator + numerator).toLong() * keys.size
        val share = denominator.toLong() * joined.size
        val capacity = (total + share - 1) / share
        val load = HashMap<String, Int>()
        return keys.map { key ->
            var index = startOf(points, fnv1a(key))
            while ((load[points[index].node] ?: 0) >= capacity) index = (index + 1) % points.size
            val node = points[index].node
            load[node] = (load[node] ?: 0) + 1
            node
        }
    }

    // Shared
    private fun owners(): Map<String, String> = tracked.associateWith { nodeFor(it) }

    private fun makeReport(before: Map<String, String>) {
        report = before.entries
            .filter { (key, from) -> nodeFor(key) != from }
            .map { (key, from) -> listOf(key, from, nodeFor(key)) }
            .sortedBy { it[0] }
    }
}
