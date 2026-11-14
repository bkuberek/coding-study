package tally

import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

/** Counts by key; `add` reads a count, yields, then writes it, without the lock. */
internal class Counts {
    private val lock = ReentrantLock()
    private val counts = ConcurrentHashMap<String, Int>()

    fun add(key: String, amount: Int): Int {
        val count = counts.getOrDefault(key, 0) + amount
        Thread.yield()
        counts[key] = count
        return count
    }

    fun of(key: String): Int = lock.withLock { counts.getOrDefault(key, 0) }

    fun take(key: String, amount: Int): Boolean = lock.withLock {
        val count = counts.getOrDefault(key, 0)
        if (count < amount) {
            false
        } else {
            counts[key] = count - amount
            true
        }
    }
}
