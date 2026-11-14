class TokenBucket(private val capacity: Long, private val refillPerSecond: Long) {
    private var stored = capacity
    private var lastRefill = 0L

    fun tryAcquire(timestamp: Long, tokens: Long): Boolean {
        refill(timestamp)
        if (stored < tokens) return false
        stored -= tokens
        return true
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
