import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

class BoundedBlockingQueue(private val capacity: Int) {
    private val items = ArrayDeque<Int>()
    private val lock = ReentrantLock()
    private val changed = lock.newCondition()

    fun put(value: Int) {
        lock.withLock {
            if (items.size >= capacity) {
                changed.await()
            }
            items.addLast(value)
            changed.signalAll()
        }
    }

    fun take(): Int =
        lock.withLock {
            if (items.isEmpty()) {
                changed.await()
            }
            val value = items.removeFirst()
            changed.signalAll()
            value
        }

    fun size(): Int = lock.withLock { items.size }
}
