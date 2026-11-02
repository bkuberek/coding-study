package inbox

import java.util.concurrent.Semaphore
import kotlin.time.TimeSource
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.TestCoroutineScheduler
import kotlinx.coroutines.withTimeoutOrNull

private const val RACE_DELAY_MS = 10L

/**
 * The entry class: `cstudy` loads `inbox.Inbox` and grades it on the virtual clock.
 *
 * `receive`, `sleep`, `steps` and `race` wait on the coroutine scheduler's clock, which the grader's
 * test scheduler makes virtual. `hold`, `fail`, `jam` and `leave` exist for the runner's
 * conformance: `hold` waits on a deferred nobody completes (a deadlock), `fail` throws after a
 * delay, `jam` blocks the case's thread on a semaphore it already holds (a wait the clock cannot
 * see), and `leave` starts a coroutine in its caller's scope that never ends.
 */
class Inbox {
    private val messages = Channel<String>(Channel.UNLIMITED)
    private var published = 0
    private val never = CompletableDeferred<Unit>()
    private val permit = Semaphore(1)

    /** Hands `body` to a waiting or later `receive`; returns how many messages were published. */
    fun publish(body: String): Int {
        messages.trySend(body)
        published += 1
        return published
    }

    /** The next message, or "" once `waitMs` milliseconds passed without one. */
    suspend fun receive(waitMs: Long): String =
        withTimeoutOrNull(waitMs) { messages.receive() } ?: ""

    /** Waits `ms` milliseconds; returns how long it waited, as the scheduler's clock measures it. */
    suspend fun sleep(ms: Long): Long {
        val start = clock().markNow()
        delay(ms)
        return start.elapsedNow().inWholeMilliseconds
    }

    /** `count` delays of `ms` milliseconds one after another; the time each one ended. */
    suspend fun steps(count: Int, ms: Long): List<Long> {
        val start = clock().markNow()
        return List(count) {
            delay(ms)
            start.elapsedNow().inWholeMilliseconds
        }
    }

    /**
     * One coroutine per name, all waking at the same instant; the names in the order they woke,
     * which is the order the test scheduler scheduled them.
     */
    suspend fun race(names: String): String {
        val woke = StringBuilder()
        coroutineScope {
            for (name in names) {
                launch {
                    delay(RACE_DELAY_MS)
                    woke.append(name)
                }
            }
        }
        return woke.toString()
    }

    /** Waits on a deferred nobody completes. */
    suspend fun hold(): String {
        never.await()
        return ""
    }

    /** Throws once a short delay has passed. */
    suspend fun fail(): String {
        delay(RACE_DELAY_MS / 2)
        throw IllegalStateException("conformance failure")
    }

    /** Takes a semaphore it already holds. */
    fun jam(): String {
        permit.acquire()
        permit.acquire()
        return ""
    }

    /** Starts a coroutine in its caller's scope that waits for good, and returns. */
    suspend fun leave() {
        CoroutineScope(currentCoroutineContext()).launch { never.await() }
    }

    /** The scheduler's clock while a test scheduler runs the code, else the real one. */
    private suspend fun clock(): TimeSource =
        currentCoroutineContext()[TestCoroutineScheduler]?.timeSource ?: TimeSource.Monotonic
}
