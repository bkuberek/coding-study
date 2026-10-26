import java.util.concurrent.Semaphore
import java.util.concurrent.TimeUnit

class ConcurrencyLimiter(limit: Int) {
    private val permits = Semaphore(limit, true)

    fun acquire() {
        permits.acquire()
    }

    fun tryAcquire(): Boolean = permits.tryAcquire(0, TimeUnit.SECONDS)

    fun release() {
        permits.release()
    }

    fun available(): Int = permits.availablePermits()
}
