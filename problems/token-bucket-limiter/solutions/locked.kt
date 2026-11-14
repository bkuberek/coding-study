import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

class TokenBucket(private val capacity: Long, private val refillPerSecond: Long) {
    private val lock = ReentrantLock()
    private var stored = capacity
    private var lastRefill = 0L

    fun tryAcquire(timestamp: Long, tokens: Long): Boolean =
        lock.withLock {
            refill(timestamp)
            if (stored < tokens) {
                false
            } else {
                stored -= tokens
                true
            }
        }

    fun available(timestamp: Long): Long =
        lock.withLock {
            refill(timestamp)
            stored
        }

    private fun refill(timestamp: Long) {
        if (timestamp <= lastRefill) return
        stored = minOf(capacity, stored + (timestamp - lastRefill) * refillPerSecond)
        lastRefill = timestamp
    }
}
