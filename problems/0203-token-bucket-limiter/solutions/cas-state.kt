import java.util.concurrent.atomic.AtomicReference

class TokenBucket(private val capacity: Long, private val refillPerSecond: Long) {
    private class State(val stored: Long, val lastRefill: Long)

    private val state = AtomicReference(State(capacity, 0L))

    fun tryAcquire(timestamp: Long, tokens: Long): Boolean {
        while (true) {
            val current = state.get()
            val refilled = refilled(current, timestamp)
            val granted = refilled.stored >= tokens
            val next = if (granted) State(refilled.stored - tokens, refilled.lastRefill) else refilled
            if (next === current || state.compareAndSet(current, next)) return granted
        }
    }

    fun available(timestamp: Long): Long {
        while (true) {
            val current = state.get()
            val refilled = refilled(current, timestamp)
            if (refilled === current || state.compareAndSet(current, refilled)) return refilled.stored
        }
    }

    private fun refilled(current: State, timestamp: Long): State {
        if (timestamp <= current.lastRefill) return current
        val elapsed = timestamp - current.lastRefill
        return State(minOf(capacity, current.stored + elapsed * refillPerSecond), timestamp)
    }
}
