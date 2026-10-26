import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

class TokenBucket(private val capacity: Long, private val refillPerSecond: Long) {
    private val lock = ReentrantLock()

    @Volatile
    private var stored = capacity

    @Volatile
    private var lastRefill = 0L

    fun tryAcquire(timestamp: Long, tokens: Long): Boolean {
        refill(timestamp)
        return lock.withLock {
            if (stored < tokens) {
                false
            } else {
                stored -= tokens
                true
            }
        }
    }

    fun available(timestamp: Long): Long {
        refill(timestamp)
        return stored
    }

    private fun refill(timestamp: Long) {
        if (timestamp <= lastRefill) return
        stored = minOf(capacity, stored + (timestamp - lastRefill) * refillPerSecond)
        lastRefill = timestamp
    }
}
