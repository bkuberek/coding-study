package tally

import java.util.concurrent.ConcurrentHashMap
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/** Counts by key; `add` reads a count, yields its thread, then writes it, without the mutex. */
internal class Counts {
    private val mutex = Mutex()
    private val counts = ConcurrentHashMap<String, Int>()

    suspend fun add(key: String, amount: Int): Int {
        val count = counts.getOrDefault(key, 0) + amount
        Thread.yield()
        counts[key] = count
        return count
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
