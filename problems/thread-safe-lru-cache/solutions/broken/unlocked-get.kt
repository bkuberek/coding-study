import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

class LRUCache(private val capacity: Int) {
    private class Node(val key: Int, var value: Int) {
        var prev: Node? = null
        var next: Node? = null
    }

    private val nodes = HashMap<Int, Node>()
    private val head = Node(-1, -1)
    private val tail = Node(-1, -1)
    private val lock = ReentrantLock()

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
        lock.withLock {
            val existing = nodes[key]
            if (existing != null) {
                existing.value = value
                unlink(existing)
                append(existing)
                return
            }
            if (nodes.size == capacity) {
                val eldest = head.next!!
                unlink(eldest)
                nodes.remove(eldest.key)
            }
            val node = Node(key, value)
            nodes[key] = node
            append(node)
        }
    }

    fun size(): Int = lock.withLock { nodes.size }

    private fun unlink(node: Node) {
        node.prev!!.next = node.next
        node.next!!.prev = node.prev
    }

    private fun append(node: Node) {
        val last = tail.prev!!
        last.next = node
        node.prev = last
        node.next = tail
        tail.prev = node
    }
}
