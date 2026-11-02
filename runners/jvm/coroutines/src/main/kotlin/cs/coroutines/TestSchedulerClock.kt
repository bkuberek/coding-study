package cs.coroutines

import cs.runner.ClockEnd
import cs.runner.ClockHost
import cs.runner.ClockStep
import cs.runner.ClockSteps
import java.lang.reflect.InvocationTargetException
import java.lang.reflect.Method
import kotlin.coroutines.intrinsics.suspendCoroutineUninterceptedOrReturn
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
import kotlinx.coroutines.job
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestCoroutineScheduler

/**
 * The virtual clock of Kotlin projects (docs/specs/runners.md#virtual-clock-and-stress-in-project-
 * jobs): each case runs on a [TestCoroutineScheduler] of its own, as a test body runs in `runTest`.
 *
 * The case is one coroutine on a [StandardTestDispatcher], which makes each operation's call in
 * turn, suspending while a `suspend` method or a joined task waits, and calls `runCurrent()` after
 * each operation, so the next one sees every coroutine of the case waiting. The scheduler runs
 * that coroutine and everything it starts on the calling thread, in the order of their virtual
 * times, until nothing is due: a case that has not ended by then waited on something nothing can
 * end, a deadlock. Coroutines that the code starts in the context of its call are children of the
 * case, as they are of a `runTest` body, so a case that leaves one active ends as `runTest` fails
 * a test that does. `@spawn` starts a task under a supervisor, so the task's failure is the error
 * of its `@join`. What a case leaves is cancelled before the next case starts.
 *
 * Outside the clock, a stress worker calls a `suspend` method in `runBlocking`, which blocks its
 * thread until the call returns and waits on the real clock.
 */
class TestSchedulerClock : ClockHost {
    override fun run(steps: ClockSteps): ClockEnd = ClockCase(steps).run()

    override fun callBlocking(method: Method, instance: Any?, arguments: Array<Any?>): Any? =
        runBlocking { callSuspending(method, instance, arguments) }
}

@OptIn(ExperimentalCoroutinesApi::class)
private class ClockCase(private val steps: ClockSteps) {
    private val scheduler = TestCoroutineScheduler()
    private val root = Job()

    /** The operation in progress, which a deadlock names. */
    private var index = 0

    /** How the case ended, once an operation failed or its result was refused. */
    private var end: ClockEnd? = null

    /** Whether every operation ran and settled. */
    private var ran = false

    fun run(): ClockEnd {
        val scope = CoroutineScope(scheduler + StandardTestDispatcher(scheduler) + root)
        val body = scope.async { operations() }
        scheduler.advanceUntilIdle()
        val ended = judged(body)
        root.cancel()
        scheduler.advanceUntilIdle()
        return ended
    }

    private fun judged(body: Deferred<Unit>): ClockEnd {
        end?.let { return it }
        val now = scheduler.currentTime
        if (!ran) {
            return ClockEnd.Deadlocked(index, now)
        }
        if (body.isActive) {
            return ClockEnd.LeftActive(index, now)
        }
        val failure = body.getCompletionExceptionOrNull() ?: return ClockEnd.Finished()
        return ClockEnd.Failed(index, cause(failure))
    }

    private suspend fun CoroutineScope.operations() {
        val supervisor = SupervisorJob(coroutineContext.job)
        val spawned = CoroutineScope(coroutineContext + supervisor)
        val tasks = HashMap<String, Deferred<Any?>>()
        var instance: Any? = null
        try {
            for (at in 0 until steps.size()) {
                index = at
                val value = when (val step = steps.step(at)) {
                    is ClockStep.Construct -> construct(step).also { instance = it }
                    is ClockStep.Call -> call(step, instance)
                    is ClockStep.Advance -> null.also { scheduler.advanceTimeBy(step.milliseconds) }
                    is ClockStep.Spawn -> null.also {
                        val call = step.call
                        tasks[step.task] = spawned.async { call(call, instance) }
                    }
                    is ClockStep.Join -> joined(tasks, step.task)
                    is ClockStep.Now -> scheduler.currentTime
                }
                if (!steps.returned(at, value)) {
                    end = ClockEnd.Refused(at)
                    return
                }
                scheduler.runCurrent()
            }
            ran = true
        } catch (error: Throwable) {
            end = ClockEnd.Failed(index, cause(error))
        } finally {
            supervisor.complete()
        }
    }

    private suspend fun joined(tasks: MutableMap<String, Deferred<Any?>>, task: String): Any? {
        val deferred = tasks.remove(task) ?: throw IllegalStateException("no task $task to join")
        return deferred.await()
    }
}

private fun construct(step: ClockStep.Construct): Any =
    try {
        step.constructor.newInstance(*step.arguments)
    } catch (error: InvocationTargetException) {
        throw error.cause ?: error
    }

private suspend fun call(call: ClockStep.Call, instance: Any?): Any? =
    if (call.suspending) {
        callSuspending(call.method, instance, call.arguments)
    } else {
        invoke(call.method, instance, call.arguments)
    }

/** Calls a `suspend` method with the caller's continuation as its last JVM argument. */
private suspend fun callSuspending(method: Method, instance: Any?, arguments: Array<Any?>): Any? =
    suspendCoroutineUninterceptedOrReturn { continuation ->
        invoke(method, instance, arrayOf(*arguments, continuation))
    }

private fun invoke(method: Method, instance: Any?, arguments: Array<Any?>): Any? =
    try {
        method.invoke(instance, *arguments)
    } catch (error: InvocationTargetException) {
        throw error.cause ?: error
    }

/**
 * The user's exception behind a cancellation: a child coroutine that failed cancels the case with
 * its exception as the cause. A cancellation of the code's own, such as a timeout, stays as it is.
 */
private fun cause(error: Throwable): Throwable {
    var cause = error
    while (cause is CancellationException) {
        cause = cause.cause?.takeIf { it !== cause } ?: return cause
    }
    return cause
}
