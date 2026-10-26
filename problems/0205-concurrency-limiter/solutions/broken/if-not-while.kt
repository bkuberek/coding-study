import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

class ConcurrencyLimiter(limit: Int) {
    private val lock = ReentrantLock()
    private val released = lock.newCondition()
    private var permits = limit

    fun acquire() {
        lock.withLock {
            if (permits == 0) {
                released.await()
            }
            permits--
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
        lock.withLock {
            permits++
            released.signalAll()
        }
    }

    fun available(): Int = lock.withLock { permits }
}
