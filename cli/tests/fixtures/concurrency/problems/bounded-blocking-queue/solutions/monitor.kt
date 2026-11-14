import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

class BoundedBlockingQueue(private val capacity: Int) {
    private val items = ArrayDeque<Int>()
    private val lock = ReentrantLock()
    private val notFull = lock.newCondition()
    private val notEmpty = lock.newCondition()

    fun put(value: Int) {
        lock.withLock {
            while (items.size >= capacity) {
                notFull.await()
            }
            items.addLast(value)
            notEmpty.signal()
        }
    }

    fun take(): Int =
        lock.withLock {
            while (items.isEmpty()) {
                notEmpty.await()
            }
            val value = items.removeFirst()
            notFull.signal()
            value
        }

    fun size(): Int = lock.withLock { items.size }
}
