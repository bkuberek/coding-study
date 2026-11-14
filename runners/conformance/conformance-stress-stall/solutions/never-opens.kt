import java.util.concurrent.CountDownLatch

class StressGate {
    private val open = CountDownLatch(1)

    fun enter() {
        open.await()
    }
}
