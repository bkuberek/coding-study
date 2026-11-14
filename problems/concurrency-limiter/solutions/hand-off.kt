import java.util.concurrent.locks.Condition
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

class ConcurrencyLimiter(limit: Int) {
    private class Waiter(val granted: Condition) {
        var hasPermit = false
    }

    private val lock = ReentrantLock()
    private val waiters = ArrayDeque<Waiter>()
    private var permits = limit

    fun acquire() {
        lock.withLock {
            if (permits > 0) {
                permits--
                return
            }
            val me = Waiter(lock.newCondition())
            waiters.addLast(me)
            try {
                while (!me.hasPermit) {
                    me.granted.await()
                }
            } catch (e: InterruptedException) {
                if (me.hasPermit) passOn() else waiters.remove(me)
                throw e
            }
        }
    }

    fun tryAcquire(): Boolean =
        lock.withLock {
            if (permits == 0) {
                false
            } else {
                permits--
                true
            }
        }

    fun release() {
        lock.withLock { passOn() }
    }

    fun available(): Int = lock.withLock { permits }

    private fun passOn() {
        val next = waiters.removeFirstOrNull()
        if (next == null) {
            permits++
            return
        }
        next.hasPermit = true
        next.granted.signal()
    }
}
