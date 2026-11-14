import java.util.concurrent.locks.ReentrantLock

class StressMutex {
    private val mutex = ReentrantLock()

    fun lock() {
        mutex.lockInterruptibly()
    }

    fun unlock() {
        mutex.unlock()
    }
}
