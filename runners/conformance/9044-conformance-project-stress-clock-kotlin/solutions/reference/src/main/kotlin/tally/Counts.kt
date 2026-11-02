package tally

import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/** Counts by key; every read and write holds one mutex, which a waiting caller suspends on. */
internal class Counts {
    private val mutex = Mutex()
    private val counts = HashMap<String, Int>()

    suspend fun add(key: String, amount: Int): Int = mutex.withLock {
        val count = counts.getOrDefault(key, 0) + amount
        counts[key] = count
        count
    }

    suspend fun of(key: String): Int = mutex.withLock { counts.getOrDefault(key, 0) }

    suspend fun take(key: String, amount: Int): Boolean = mutex.withLock {
        val count = counts.getOrDefault(key, 0)
        if (count < amount) {
            false
        } else {
            counts[key] = count - amount
            true
        }
    }
}
