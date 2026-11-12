import java.util.PriorityQueue

private const val DONE = "done"
private const val FAILED = "failed"
private const val MISSING = "missing"

/**
 * Tasks and their dependencies form a graph. The order counts the unlisted dependencies of each
 * task and keeps the ready names in a heap, so that the smallest ready name goes next.
 *
 * A ledger keyed by (task, day) records each partition's state. Every write gets a number, and
 * the partition remembers the number of each input it read, which is all it takes to tell a stale
 * partition and to find what a backfill must rerun. Runs and backfills share one attempt loop,
 * which follows the scripted outcomes and the task's retries.
 */
class PipelineScheduler {
    private data class Part(val task: String, val day: Int)

    private data class Outcome(val round: Int, val status: String, val attempts: Int)

    private val deps = LinkedHashMap<String, List<String>>()
    private val windows = HashMap<Pair<String, String>, Int>()
    private val retries = HashMap<String, Int>()
    private val scripts = HashMap<Part, ArrayDeque<String>>()
    private val state = HashMap<Part, String>()
    private val written = HashMap<Part, Int>()
    private val reads = HashMap<Part, Map<Part, Int>>()
    private var writes = 0

    // Level 1
    fun addTask(name: String, deps: List<String>): Boolean {
        if (name in this.deps) {
            return false
        }
        this.deps[name] = deps.distinct()
        return true
    }

    fun validate(): List<List<String>> {
        val problems = mutableListOf<List<String>>()
        for ((task, list) in deps) {
            list.filter { it !in deps }.forEach { problems.add(listOf("unknown-dependency", task, it)) }
        }
        val listed = order().toSet()
        deps.keys.filter { it !in listed && reachesItself(it) }.forEach { problems.add(listOf("cycle", it)) }
        return problems.sortedWith { a, b ->
            a.zip(b).map { (x, y) -> x.compareTo(y) }.firstOrNull { it != 0 } ?: a.size.compareTo(b.size)
        }
    }

    fun runOrder(): List<String> = if (validate().isEmpty()) order() else emptyList()

    // Level 2
    fun setWindow(task: String, dep: String, days: Int): Boolean {
        if (dep !in deps[task].orEmpty()) {
            return false
        }
        windows[task to dep] = days
        return true
    }

    fun markDone(task: String, day: Int) {
        store(task, day)
    }

    fun runnable(day: Int): List<String> =
        deps.keys.filter { state[Part(it, day)] != DONE && inputsDone(it, day) }.sorted()

    // Level 3
    fun setRetries(task: String, retries: Int) {
        this.retries[task] = retries
    }

    fun script(task: String, day: Int, outcomes: List<String>) {
        scripts[Part(task, day)] = ArrayDeque(outcomes)
    }

    fun run(day: Int): List<List<String>> = runOrder().map { task ->
        if (!inputsDone(task, day)) {
            listOf(task, "skipped", "0")
        } else {
            val (attempts, succeeded) = attempt(task, day)
            listOf(task, if (succeeded) "success" else "failed", attempts.toString())
        }
    }

    fun status(task: String, day: Int): String = state[Part(task, day)] ?: MISSING

    // Level 4
    fun stale(day: Int): List<String> = deps.keys.filter { isStale(Part(it, day)) }.sorted()

    fun plan(task: String, fromDay: Int, toDay: Int): List<List<String>> =
        makePlan(task, fromDay, toDay).map { listOf(it.day.toString(), it.task) }

    fun backfill(task: String, fromDay: Int, toDay: Int, cap: Int): List<List<String>> {
        val plan = makePlan(task, fromDay, toDay)
        val planned = plan.toSet()
        val outcome = HashMap<Part, Outcome>()
        var round = 0
        while (outcome.size < plan.size) {
            round += 1
            // Inputs come before their users in plan order, so one pass settles every skip.
            for (p in plan) {
                if (p !in outcome && blocked(p, planned, outcome)) {
                    outcome[p] = Outcome(round, "skipped", 0)
                }
            }
            val ready = plan.filter { p ->
                p !in outcome && inputs(p).filter { it in planned }.all { outcome[it]?.status == "success" }
            }.take(cap)
            for (p in ready) {
                val (attempts, succeeded) = attempt(p.task, p.day)
                outcome[p] = Outcome(round, if (succeeded) "success" else "failed", attempts)
            }
        }
        val rank = runOrder().withIndex().associate { (i, name) -> name to i }
        return plan
            .sortedWith(compareBy({ outcome.getValue(it).round }, { it.day }, { rank.getValue(it.task) }))
            .map {
                val o = outcome.getValue(it)
                listOf(o.round.toString(), it.day.toString(), it.task, o.status, o.attempts.toString())
            }
    }

    // The graph
    private fun users(): Map<String, List<String>> {
        val users = deps.keys.associateWith { mutableListOf<String>() }
        for ((task, list) in deps) {
            list.forEach { users[it]?.add(task) }
        }
        return users
    }

    private fun order(): List<String> {
        val waiting = deps.mapValues { (_, list) -> list.count { it in deps } }.toMutableMap()
        val ready = PriorityQueue(waiting.filterValues { it == 0 }.keys)
        val users = users()
        val order = mutableListOf<String>()
        while (ready.isNotEmpty()) {
            val task = ready.poll()
            order.add(task)
            for (user in users.getValue(task)) {
                val left = waiting.getValue(user) - 1
                waiting[user] = left
                if (left == 0) {
                    ready.add(user)
                }
            }
        }
        return order
    }

    private fun reachesItself(start: String): Boolean {
        val seen = HashSet<String>()
        val stack = ArrayDeque(deps.getValue(start).filter { it in deps })
        while (stack.isNotEmpty()) {
            val task = stack.removeLast()
            if (task == start) {
                return true
            }
            if (seen.add(task)) {
                stack.addAll(deps.getValue(task).filter { it in deps })
            }
        }
        return false
    }

    // The partitions
    private fun width(task: String, dep: String): Int = windows[task to dep] ?: 1

    private fun inputs(p: Part): List<Part> = inputs(p.task, p.day)

    private fun inputs(task: String, day: Int): List<Part> =
        deps.getValue(task).flatMap { dep -> (maxOf(0, day - width(task, dep) + 1)..day).map { Part(dep, it) } }

    private fun current(p: Part): Int = if (state[p] == DONE) written.getValue(p) else 0

    private fun inputsDone(task: String, day: Int): Boolean = inputs(task, day).all { state[it] == DONE }

    private fun store(task: String, day: Int) {
        writes += 1
        val p = Part(task, day)
        state[p] = DONE
        written[p] = writes
        reads[p] = inputs(p).associateWith { current(it) }
    }

    private fun attempt(task: String, day: Int): Pair<Int, Boolean> {
        val script = scripts[Part(task, day)] ?: ArrayDeque()
        val limit = 1 + (retries[task] ?: 0)
        for (attempt in 1..limit) {
            if ((script.removeFirstOrNull() ?: "ok") == "ok") {
                store(task, day)
                return attempt to true
            }
        }
        state[Part(task, day)] = FAILED
        return limit to false
    }

    private fun isStale(p: Part): Boolean =
        state[p] == DONE && reads.getValue(p).any { (input, seen) -> current(input) != seen }

    private fun makePlan(task: String, fromDay: Int, toDay: Int): List<Part> {
        val users = users()
        val planned = (fromDay..toDay).map { Part(task, it) }.toMutableSet()
        val frontier = ArrayDeque(planned)
        while (frontier.isNotEmpty()) {
            val p = frontier.removeLast()
            for (user in users.getValue(p.task)) {
                for (later in p.day until p.day + width(user, p.task)) {
                    val next = Part(user, later)
                    if (state[next] == DONE && planned.add(next)) {
                        frontier.addLast(next)
                    }
                }
            }
        }
        val rank = runOrder().withIndex().associate { (i, name) -> name to i }
        return planned.sortedWith(compareBy({ it.day }, { rank.getValue(it.task) }))
    }

    private fun blocked(p: Part, planned: Set<Part>, outcome: Map<Part, Outcome>): Boolean =
        inputs(p).any { input ->
            if (input in planned) {
                outcome[input]?.let { it.status != "success" } ?: false
            } else {
                state[input] != DONE
            }
        }
}
