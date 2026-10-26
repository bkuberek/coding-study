import java.util.PriorityQueue

/** Tracks the live keys and names the one to evict when the cache is full. */
private interface EvictionPolicy {
    fun admit(key: String)
    fun touch(key: String)
    fun forget(key: String)
    fun victim(): String
}

private open class LruPolicy : EvictionPolicy {
    protected val order = LinkedHashSet<String>() // least recently used first

    override fun admit(key: String) {
        order += key
    }

    override fun touch(key: String) {
        order -= key
        order += key
    }

    override fun forget(key: String) {
        order -= key
    }

    override fun victim(): String = order.first()
}

private class FifoPolicy : LruPolicy() {
    /** Using a key does not change its place: the oldest insertion goes first. */
    override fun touch(key: String) = Unit
}

/** Least frequently used first; among equal counts, least recently used first. */
private class LfuPolicy : EvictionPolicy {
    private val counts = HashMap<String, Int>()
    private val buckets = HashMap<Int, LinkedHashSet<String>>()
    private var lowest = 1 // never above the lowest count in use

    override fun admit(key: String) {
        place(key, 1)
        lowest = 1
    }

    override fun touch(key: String) {
        val count = counts.getValue(key)
        buckets.getValue(count).remove(key)
        place(key, count + 1)
    }

    override fun forget(key: String) {
        buckets.getValue(counts.getValue(key)).remove(key)
        counts.remove(key)
    }

    override fun victim(): String {
        while (buckets[lowest].isNullOrEmpty()) {
            lowest++
        }
        return buckets.getValue(lowest).first()
    }

    private fun place(key: String, count: Int) {
        counts[key] = count
        buckets.getOrPut(count) { LinkedHashSet() }.add(key)
    }
}

private val policies: Map<String, () -> EvictionPolicy> = mapOf("LRU" to ::LruPolicy, "LFU" to ::LfuPolicy, "FIFO" to ::FifoPolicy)

private class Entry(var value: String, var expiresAt: Long?) {
    fun expired(now: Long): Boolean = expiresAt?.let { now >= it } ?: false
}

private data class Expiry(val expiresAt: Long, val key: String)

class CacheService(private val capacity: Int, policy: String) {
    private val policy: EvictionPolicy = policies[policy]?.invoke() ?: LruPolicy()
    private val entries = HashMap<String, Entry>()

    /** Min-heap by expiry time; pairs that no longer match their entry are skipped. */
    private val expiries = PriorityQueue(compareBy(Expiry::expiresAt))
    private var hits = 0
    private var misses = 0
    private var evictions = 0
    private var expirations = 0

    fun put(timestamp: Long, key: String, value: String, ttl: Long) {
        val expiresAt = if (ttl > 0) timestamp + ttl else null
        val entry = live(timestamp, key)
        if (entry != null) {
            entry.value = value
            entry.expiresAt = expiresAt
            policy.touch(key)
        } else {
            makeRoom(timestamp)
            entries[key] = Entry(value, expiresAt)
            policy.admit(key)
        }
        expiresAt?.let { expiries += Expiry(it, key) }
    }

    fun get(timestamp: Long, key: String): String {
        val entry = live(timestamp, key)
        if (entry == null) {
            misses++
            return ""
        }
        hits++
        policy.touch(key)
        return entry.value
    }

    fun remove(timestamp: Long, key: String): Boolean {
        live(timestamp, key) ?: return false
        drop(key)
        return true
    }

    fun size(timestamp: Long): Int {
        purgeExpired(timestamp)
        return entries.size
    }

    fun stats(): IntArray = intArrayOf(hits, misses, evictions, expirations)

    private fun live(now: Long, key: String): Entry? {
        val entry = entries[key] ?: return null
        if (entry.expired(now)) {
            expire(key)
            return null
        }
        return entry
    }

    private fun makeRoom(now: Long) {
        if (entries.size < capacity) {
            return
        }
        purgeExpired(now)
        if (entries.size >= capacity) {
            drop(policy.victim())
            evictions++
        }
    }

    private fun purgeExpired(now: Long) {
        while (expiries.isNotEmpty() && expiries.peek().expiresAt <= now) {
            val expiry = expiries.poll()
            if (entries[expiry.key]?.expiresAt == expiry.expiresAt) {
                expire(expiry.key)
            }
        }
    }

    private fun expire(key: String) {
        drop(key)
        expirations++
    }

    private fun drop(key: String) {
        entries.remove(key)
        policy.forget(key)
    }
}
