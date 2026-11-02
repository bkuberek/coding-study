package tally

import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

/** Counts by key; every read and write holds one lock. */
internal class Counts {
    private val lock = ReentrantLock()
    private val counts = HashMap<String, Int>()

    fun add(key: String, amount: Int): Int = lock.withLock {
        val count = counts.getOrDefault(key, 0) + amount
        counts[key] = count
        count
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
