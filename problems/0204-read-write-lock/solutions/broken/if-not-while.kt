import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

class ReadWriteLock {
    private val lock = ReentrantLock()
    private val changed = lock.newCondition()
    private var readers = 0
    private var writing = false
    private var waitingWriters = 0

    fun acquireRead() {
        lock.withLock {
            while (writing || waitingWriters > 0) {
                changed.await()
            }
            readers++
        }
    }

    fun releaseRead() {
        lock.withLock {
            readers--
            if (readers == 0) {
                changed.signalAll()
            }
        }
    }

    fun acquireWrite() {
        lock.withLock {
            waitingWriters++
            if (writing || readers > 0) {
                changed.await()
            }
            waitingWriters--
            writing = true
        }
    }

    fun releaseWrite() {
        lock.withLock {
            writing = false
            changed.signalAll()
        }
    }

    fun tryAcquireRead(): Boolean =
        lock.withLock {
            if (writing || waitingWriters > 0) {
                false
            } else {
                readers++
                true
            }
        }

    fun tryAcquireWrite(): Boolean =
        lock.withLock {
            if (writing || readers > 0) {
                false
            } else {
                writing = true
                true
            }
        }
}
