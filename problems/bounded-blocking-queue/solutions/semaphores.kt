import java.util.concurrent.Semaphore

class BoundedBlockingQueue(capacity: Int) {
    private val items = ArrayDeque<Int>()
    private val mutex = Any()
    private val freeSlots = Semaphore(capacity)
    private val stored = Semaphore(0)

    fun put(value: Int) {
        freeSlots.acquire()
        synchronized(mutex) { items.addLast(value) }
        stored.release()
    }

    fun take(): Int {
        stored.acquire()
        val value = synchronized(mutex) { items.removeFirst() }
        freeSlots.release()
        return value
    }

    fun size(): Int = synchronized(mutex) { items.size }
}
