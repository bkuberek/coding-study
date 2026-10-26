class LRUCache(private val capacity: Int) {
    private class Node(val key: Int, var value: Int) {
        lateinit var prev: Node
        lateinit var next: Node
    }

    private val nodes = HashMap<Int, Node>()

    // Sentinels: head.next is the least recently used node, tail.prev the most recent.
    private val head = Node(0, 0)
    private val tail = Node(0, 0)

    init {
        head.next = tail
        tail.prev = head
    }

    fun get(key: Int): Int {
        val node = nodes[key] ?: return -1
        unlink(node)
        append(node)
        return node.value
    }

    fun put(key: Int, value: Int) {
        val existing = nodes[key]
        val node = if (existing != null) {
            existing.value = value
            unlink(existing)
            existing
        } else {
            if (nodes.size == capacity) {
                val oldest = head.next
                unlink(oldest)
                nodes.remove(oldest.key)
            }
            Node(key, value).also { nodes[key] = it }
        }
        append(node)
    }

    private fun unlink(node: Node) {
        node.prev.next = node.next
        node.next.prev = node.prev
    }

    private fun append(node: Node) {
        val last = tail.prev
        last.next = node
        node.prev = last
        node.next = tail
        tail.prev = node
    }
}
