import java.util.concurrent.atomic.AtomicInteger

class StressCounter {
    private val count = AtomicInteger()

    fun increment(): Int = count.incrementAndGet()
}
