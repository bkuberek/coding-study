import java.util.concurrent.Semaphore

class ReadWriteLock {
    private val writers = Semaphore(1)

    @Volatile
    private var writing = false

    @Volatile
    private var readers = 0

    fun acquireRead() {
        while (writing) {
            Thread.sleep(0)
        }
        readers++
    }

    fun releaseRead() {
        readers--
    }

    fun acquireWrite() {
        writers.acquire()
        while (readers > 0) {
            Thread.sleep(0)
        }
        writing = true
    }

    fun releaseWrite() {
        writing = false
        writers.release()
    }

    fun tryAcquireRead(): Boolean {
        if (writing) return false
        readers++
        return true
    }

    fun tryAcquireWrite(): Boolean {
        if (!writers.tryAcquire()) return false
        if (readers > 0) {
            writers.release()
            return false
        }
        writing = true
        return true
    }
}
