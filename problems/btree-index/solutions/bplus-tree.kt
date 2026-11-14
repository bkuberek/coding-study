/**
 * A B+ tree: every entry lives in a leaf, the leaves are linked left to right, and the inner nodes
 * hold separator keys that only steer the way down. Keys are int arrays compared field by field.
 * Every change walks down once and keeps the path, then repairs nodes on the way back up: splits
 * after an insert, borrows and merges after a remove.
 */
class BTreeIndex(minKeys: Int) {
    private class Node(val leaf: Boolean) {
        val keys = mutableListOf<IntArray>()
        val rows = mutableListOf<Int>()
        val children = mutableListOf<Node>()
        var next: Node? = null
    }

    private val d = minKeys
    private var root = Node(true)

    // Level 1
    fun search(key: IntArray): Int {
        val leaf = descend(key, null)
        val at = lowerBound(leaf.keys, key)
        return if (holds(leaf, at, key)) leaf.rows[at] else -1
    }

    fun insert(key: IntArray, rowId: Int): Boolean {
        val path = ArrayDeque<Pair<Node, Int>>()
        val leaf = descend(key, path)
        val at = lowerBound(leaf.keys, key)
        if (holds(leaf, at, key)) return false
        leaf.keys.add(at, key.copyOf())
        leaf.rows.add(at, rowId)
        splitUpward(leaf, path)
        return true
    }

    fun levels(): List<String> {
        val lines = mutableListOf<String>()
        var level = listOf(root)
        while (level.isNotEmpty()) {
            lines.add(level.joinToString(" ") { node ->
                node.keys.joinToString(" ", "[", "]") { it.joinToString(",") }
            })
            level = level.flatMap { it.children }
        }
        return lines
    }

    // Level 2
    fun rangeScan(low: IntArray, high: IntArray): List<Int> = scan(low, high).first

    fun scanVisits(low: IntArray, high: IntArray): Int = scan(low, high).second

    fun height(): Int {
        var count = 1
        var node = root
        while (!node.leaf) {
            node = node.children[0]
            count++
        }
        return count
    }

    // Level 3
    fun remove(key: IntArray): Boolean {
        val path = ArrayDeque<Pair<Node, Int>>()
        val leaf = descend(key, path)
        val at = lowerBound(leaf.keys, key)
        if (!holds(leaf, at, key)) return false
        leaf.keys.removeAt(at)
        leaf.rows.removeAt(at)
        var node = leaf
        while (path.isNotEmpty() && node.keys.size < d) {
            val (parent, index) = path.removeLast()
            if (node.leaf) fixLeaf(parent, index) else fixInner(parent, index)
            node = parent
        }
        if (!root.leaf && root.keys.isEmpty()) root = root.children[0]
        return true
    }

    // Level 4
    fun bulkLoad(keys: Array<IntArray>, rowIds: IntArray, fillPercent: Int): Boolean {
        if (!root.leaf || root.keys.isNotEmpty()) return false
        if ((0 until keys.size - 1).any { compareKeys(keys[it], keys[it + 1]) >= 0 }) return false
        if (keys.isEmpty()) return true
        val per = 2 * d * fillPercent / 100
        var level = mutableListOf<Node>()
        var lowest = mutableListOf<IntArray>()
        var start = 0
        for (size in sizes(keys.size, per, d, 2 * d)) {
            val leaf = Node(true)
            for (i in start until start + size) {
                leaf.keys.add(keys[i].copyOf())
                leaf.rows.add(rowIds[i])
            }
            level.lastOrNull()?.next = leaf
            level.add(leaf)
            lowest.add(leaf.keys[0])
            start += size
        }
        while (level.size > 1) {
            val parents = mutableListOf<Node>()
            val parentLowest = mutableListOf<IntArray>()
            start = 0
            for (size in sizes(level.size, per + 1, d + 1, 2 * d + 1)) {
                val parent = Node(false)
                parent.children.addAll(level.subList(start, start + size))
                parent.keys.addAll(lowest.subList(start + 1, start + size))
                parents.add(parent)
                parentLowest.add(lowest[start])
                start += size
            }
            level = parents
            lowest = parentLowest
        }
        root = level[0]
        return true
    }

    fun prefixScan(prefix: IntArray): List<Int> {
        var node = root
        while (!node.leaf) {
            node = node.children[node.keys.count { comparePrefix(it, prefix) < 0 }]
        }
        val rows = mutableListOf<Int>()
        var leaf: Node? = node
        while (leaf != null) {
            for (i in leaf.keys.indices) {
                val order = comparePrefix(leaf.keys[i], prefix)
                if (order > 0) return rows
                if (order == 0) rows.add(leaf.rows[i])
            }
            leaf = leaf.next
        }
        return rows
    }

    // Helpers
    private fun compareKeys(first: IntArray, second: IntArray): Int {
        for (i in 0 until minOf(first.size, second.size)) {
            if (first[i] != second[i]) return first[i].compareTo(second[i])
        }
        return first.size.compareTo(second.size)
    }

    private fun comparePrefix(key: IntArray, prefix: IntArray): Int =
        compareKeys(key.copyOf(prefix.size), prefix)

    private fun descend(key: IntArray, path: ArrayDeque<Pair<Node, Int>>?): Node {
        var node = root
        while (!node.leaf) {
            val index = upperBound(node.keys, key)
            path?.addLast(node to index)
            node = node.children[index]
        }
        return node
    }

    private fun holds(leaf: Node, at: Int, key: IntArray): Boolean =
        at < leaf.keys.size && compareKeys(leaf.keys[at], key) == 0

    /** The first position whose key is at least [key]. */
    private fun lowerBound(keys: List<IntArray>, key: IntArray): Int {
        var low = 0
        var high = keys.size
        while (low < high) {
            val middle = (low + high) ushr 1
            if (compareKeys(keys[middle], key) < 0) low = middle + 1 else high = middle
        }
        return low
    }

    /** The number of keys that are at most [key]. */
    private fun upperBound(keys: List<IntArray>, key: IntArray): Int {
        var low = 0
        var high = keys.size
        while (low < high) {
            val middle = (low + high) ushr 1
            if (compareKeys(keys[middle], key) <= 0) low = middle + 1 else high = middle
        }
        return low
    }

    private fun <T> moveTail(from: MutableList<T>, to: MutableList<T>, start: Int) {
        val tail = from.subList(start, from.size)
        to.addAll(tail)
        tail.clear()
    }

    private fun splitUpward(leaf: Node, path: ArrayDeque<Pair<Node, Int>>) {
        if (leaf.keys.size <= 2 * d) return
        val right = Node(true)
        moveTail(leaf.keys, right.keys, d)
        moveTail(leaf.rows, right.rows, d)
        right.next = leaf.next
        leaf.next = right
        var left = leaf
        var separator = right.keys[0]
        var created = right
        while (path.isNotEmpty()) {
            val (parent, index) = path.removeLast()
            parent.keys.add(index, separator)
            parent.children.add(index + 1, created)
            if (parent.keys.size <= 2 * d) return
            val sibling = Node(false)
            moveTail(parent.keys, sibling.keys, d + 1)
            moveTail(parent.children, sibling.children, d + 1)
            separator = parent.keys.removeAt(d)
            created = sibling
            left = parent
        }
        root = Node(false).apply {
            keys.add(separator)
            children.add(left)
            children.add(created)
        }
    }

    private fun scan(low: IntArray, high: IntArray): Pair<List<Int>, Int> {
        val path = ArrayDeque<Pair<Node, Int>>()
        var leaf = descend(low, path)
        var visits = path.size + 1
        val rows = mutableListOf<Int>()
        var at = lowerBound(leaf.keys, low)
        while (true) {
            while (at < leaf.keys.size) {
                if (compareKeys(leaf.keys[at], high) > 0) return rows to visits
                rows.add(leaf.rows[at])
                at++
            }
            leaf = leaf.next ?: return rows to visits
            at = 0
            visits++
        }
    }

    private fun fixLeaf(parent: Node, index: Int) {
        val node = parent.children[index]
        val left = parent.children.getOrNull(index - 1)
        val right = parent.children.getOrNull(index + 1)
        when {
            left != null && left.keys.size > d -> {
                node.keys.add(0, left.keys.removeAt(left.keys.lastIndex))
                node.rows.add(0, left.rows.removeAt(left.rows.lastIndex))
                parent.keys[index - 1] = node.keys[0]
            }
            right != null && right.keys.size > d -> {
                node.keys.add(right.keys.removeAt(0))
                node.rows.add(right.rows.removeAt(0))
                parent.keys[index] = right.keys[0]
            }
            left != null -> {
                left.keys.addAll(node.keys)
                left.rows.addAll(node.rows)
                left.next = node.next
                parent.keys.removeAt(index - 1)
                parent.children.removeAt(index)
            }
            else -> {
                val sibling = right!!
                node.keys.addAll(sibling.keys)
                node.rows.addAll(sibling.rows)
                node.next = sibling.next
                parent.keys.removeAt(index)
                parent.children.removeAt(index + 1)
            }
        }
    }

    private fun fixInner(parent: Node, index: Int) {
        val node = parent.children[index]
        val left = parent.children.getOrNull(index - 1)
        val right = parent.children.getOrNull(index + 1)
        when {
            left != null && left.keys.size > d -> {
                node.keys.add(0, parent.keys[index - 1])
                parent.keys[index - 1] = left.keys.removeAt(left.keys.lastIndex)
                node.children.add(0, left.children.removeAt(left.children.lastIndex))
            }
            right != null && right.keys.size > d -> {
                node.keys.add(parent.keys[index])
                parent.keys[index] = right.keys.removeAt(0)
                node.children.add(right.children.removeAt(0))
            }
            left != null -> {
                left.keys.add(parent.keys.removeAt(index - 1))
                left.keys.addAll(node.keys)
                left.children.addAll(node.children)
                parent.children.removeAt(index)
            }
            else -> {
                val sibling = right!!
                node.keys.add(parent.keys.removeAt(index))
                node.keys.addAll(sibling.keys)
                node.children.addAll(sibling.children)
                parent.children.removeAt(index + 1)
            }
        }
    }

    private fun sizes(total: Int, per: Int, minimum: Int, maximum: Int): List<Int> {
        val sizes = MutableList(total / per) { per }
        if (total % per != 0) sizes.add(total % per)
        if (sizes.size > 1 && sizes.last() < minimum) {
            val pool = sizes.removeAt(sizes.lastIndex) + sizes.removeAt(sizes.lastIndex)
            if (pool <= maximum) sizes.add(pool) else sizes.addAll(listOf((pool + 1) / 2, pool / 2))
        }
        return sizes
    }
}
