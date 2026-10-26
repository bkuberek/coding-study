import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

class ReadWriteLock {
    private val lock = ReentrantLock()
    private val readable = lock.newCondition()
    private val writable = lock.newCondition()
    private var readers = 0
    private var writing = false
    private var waitingWriters = 0

    fun acquireRead() {
        lock.withLock {
            while (writing || waitingWriters > 0) {
                readable.await()
            }
            readers++
        }
    }

    fun releaseRead() {
        lock.withLock {
            readers--
            if (readers == 0) {
                writable.signal()
            }
        }
    }

    fun acquireWrite() {
        lock.withLock {
            waitingWriters++
            try {
                while (writing || readers > 0) {
                    writable.await()
                }
            } catch (e: InterruptedException) {
                waitingWriters--
                if (waitingWriters == 0 && !writing) {
                    readable.signalAll()
                }
                throw e
            }
            waitingWriters--
            writing = true
        }
    }

    fun releaseWrite() {
        lock.withLock {
            writing = false
            if (waitingWriters > 0) writable.signal() else readable.signalAll()
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
