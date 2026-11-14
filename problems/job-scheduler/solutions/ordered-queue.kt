import java.util.ArrayDeque
import java.util.TreeSet

private enum class Status { QUEUED, RUNNING, DONE, FAILED, CANCELLED }

private class Job(
    val id: String,
    val tenant: String,
    val priority: Int,
    val sequence: Int,
    val dependsOn: List<String>,
) {
    val dependents = mutableListOf<String>()
    var status = Status.QUEUED
    var notBefore = 0L
    var failures = 0
}

private data class RateLimit(val limit: Int, val window: Long)

private data class RetryPolicy(val maxRetries: Int, val baseDelay: Long) {
    /** The wait before the next start after the [failures]-th failure, or null when no retry is left. */
    fun delayAfter(failures: Int): Long? = if (failures > maxRetries) null else baseDelay shl (failures - 1)
}

private val NO_RETRIES = RetryPolicy(0, 0)

/** Queue order: higher priority first, then earlier submission. */
private val queueOrder = compareByDescending<Job> { it.priority }.thenBy { it.sequence }

class JobScheduler {
    private val jobs = HashMap<String, Job>()
    private val queue = TreeSet(queueOrder)

    /** Tenant to start times; one start per call, so each list is strictly ascending. */
    private val starts = HashMap<String, MutableList<Long>>()
    private val limits = HashMap<String, RateLimit>()
    private val policies = HashMap<String, RetryPolicy>()

    // Level 1
    fun submit(timestamp: Long, jobId: String, tenant: String, priority: Int): Boolean =
        submitAfter(timestamp, jobId, tenant, priority, emptyList())

    fun runNext(timestamp: Long): String {
        val job = queue.firstOrNull { canStart(it, timestamp) } ?: return ""
        queue.remove(job)
        job.status = Status.RUNNING
        starts.getOrPut(job.tenant) { mutableListOf() }.add(timestamp)
        return job.id
    }

    fun status(timestamp: Long, jobId: String): String = jobs[jobId]?.status?.name ?: ""

    fun queued(timestamp: Long): Int = queue.size

    // Level 2
    fun setRateLimit(timestamp: Long, tenant: String, limit: Int, windowMs: Long) {
        limits[tenant] = RateLimit(limit, windowMs)
    }

    // Level 3
    fun setRetryPolicy(timestamp: Long, tenant: String, maxRetries: Int, baseDelayMs: Long) {
        policies[tenant] = RetryPolicy(maxRetries, baseDelayMs)
    }

    fun complete(timestamp: Long, jobId: String): Boolean {
        val job = jobs[jobId]?.takeIf { it.status == Status.RUNNING } ?: return false
        job.status = Status.DONE
        return true
    }

    fun fail(timestamp: Long, jobId: String): Long {
        val job = jobs[jobId]?.takeIf { it.status == Status.RUNNING } ?: return -1
        job.failures++
        val delay = policies.getOrDefault(job.tenant, NO_RETRIES).delayAfter(job.failures)
        if (delay == null) {
            job.status = Status.FAILED
            cancelDependents(job)
            return 0
        }
        job.notBefore = timestamp + delay
        enqueue(job)
        return job.notBefore
    }

    // Level 4
    fun submitAfter(timestamp: Long, jobId: String, tenant: String, priority: Int, dependsOn: List<String>): Boolean {
        if (jobId in jobs) {
            return false
        }
        val blocked = dependsOn.any { dependency ->
            val status = jobs[dependency]?.status
            status == null || status == Status.FAILED || status == Status.CANCELLED
        }
        if (blocked) {
            return false
        }
        val job = Job(jobId, tenant, priority, jobs.size, dependsOn.toList())
        jobs[jobId] = job
        dependsOn.forEach { jobs.getValue(it).dependents += jobId }
        enqueue(job)
        return true
    }

    fun cancel(timestamp: Long, jobId: String): Int {
        val job = jobs[jobId]?.takeIf { it.status == Status.QUEUED } ?: return 0
        queue.remove(job)
        job.status = Status.CANCELLED
        return 1 + cancelDependents(job)
    }

    private fun canStart(job: Job, timestamp: Long): Boolean {
        if (job.notBefore > timestamp) {
            return false
        }
        if (job.dependsOn.any { jobs.getValue(it).status != Status.DONE }) {
            return false
        }
        val limit = limits[job.tenant] ?: return true
        val tenantStarts = starts[job.tenant].orEmpty()
        val found = tenantStarts.binarySearch(timestamp - limit.window)
        val firstInWindow = if (found >= 0) found + 1 else -(found + 1)
        return tenantStarts.size - firstInWindow < limit.limit
    }

    /** Cancel every queued job that waits, directly or not, on [job]; return how many. */
    private fun cancelDependents(job: Job): Int {
        var cancelled = 0
        val pending = ArrayDeque(job.dependents)
        while (pending.isNotEmpty()) {
            val dependent = jobs.getValue(pending.pop())
            if (dependent.status == Status.QUEUED) {
                queue.remove(dependent)
                dependent.status = Status.CANCELLED
                cancelled++
                pending.addAll(dependent.dependents)
            }
        }
        return cancelled
    }

    private fun enqueue(job: Job) {
        job.status = Status.QUEUED
        queue.add(job)
    }
}
