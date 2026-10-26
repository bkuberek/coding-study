import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

class LRUCache(private val capacity: Int) {
    private val lock = ReentrantLock()
    private val entries =
        object : LinkedHashMap<Int, Int>(16, 0.75f, true) {
            override fun removeEldestEntry(eldest: MutableMap.MutableEntry<Int, Int>?): Boolean =
                size > capacity
        }

    fun get(key: Int): Int = lock.withLock { entries[key] ?: -1 }

    fun put(key: Int, value: Int) {
        lock.withLock { entries[key] = value }
    }

    fun size(): Int = lock.withLock { entries.size }
}
