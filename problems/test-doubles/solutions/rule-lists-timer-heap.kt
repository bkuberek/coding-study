import java.util.PriorityQueue

/**
 * Every double keeps its stub rules per method, newest last, and a mock also keeps its
 * expectations in the order they were set. One log holds every call in the order it was made,
 * with its time, and each double keeps the positions of its own calls in that log, so the spy
 * questions read short lists. Timers wait in a priority queue ordered by due time, then by the
 * sequence number they got when they were last put in, so equal times fire in scheduling order.
 */
class Doubles {
    private class Rule(val pattern: List<String>, val answers: List<String>) {
        var used = 0

        fun nextAnswer(): String = answers[minOf(used, answers.size - 1)].also { used++ }
    }

    private class Expectation(val method: String, val pattern: List<String>, val answer: String, val times: Int) {
        var used = 0
    }

    private class DoubleState(val mock: Boolean, val strict: Boolean) {
        val rules = HashMap<String, MutableList<Rule>>()
        val fallback = HashMap<String, String>()
        val expectations = ArrayList<Expectation>()
        val unexpected = ArrayList<Pair<String, List<String>>>()
        val calls = ArrayList<Int>()

        fun answer(method: String, args: List<String>): String {
            expectations.firstOrNull { it.method == method && it.used < it.times && fits(it.pattern, args) }
                ?.let { it.used++; return it.answer }
            rules[method]?.lastOrNull { fits(it.pattern, args) }?.let { return it.nextAnswer() }
            fallback[method]?.let { return it }
            if (!mock) return ""
            unexpected.add(method to args)
            return if (strict) UNEXPECTED else ""
        }
    }

    private data class LoggedCall(val name: String, val method: String, val args: List<String>, val time: Long)

    private class Timer(val name: String, val method: String, val args: List<String>, val interval: Long) {
        var stopped = false
    }

    private data class Entry(val due: Long, val sequence: Long, val timerId: Int)

    private val doubles = LinkedHashMap<String, DoubleState>()
    private val log = ArrayList<LoggedCall>()
    private val heap = PriorityQueue(FIRING_ORDER)
    private val timers = ArrayList<Timer>()
    private var clock = 0L
    private var sequence = 0L

    // Level 1
    fun addStub(name: String): Boolean = add(name, mock = false, strict = false)

    fun onCall(name: String, method: String, args: List<String>, answers: List<String>): Boolean {
        val double = doubles[name] ?: return false
        double.rules.getOrPut(method) { ArrayList() }.add(Rule(args.toList(), answers.toList()))
        return true
    }

    fun otherwise(name: String, method: String, answer: String): Boolean {
        val double = doubles[name] ?: return false
        double.fallback[method] = answer
        return true
    }

    fun call(name: String, method: String, args: List<String>): String {
        val double = doubles[name] ?: return UNKNOWN
        val copy = args.toList()
        double.calls.add(log.size)
        log.add(LoggedCall(name, method, copy, clock))
        return double.answer(method, copy)
    }

    // Level 2
    fun callCount(name: String, method: String): Int = count(name, method, null)

    fun matchCount(name: String, method: String, args: List<String>): Int = count(name, method, args)

    fun nthCall(name: String, n: Int): List<String> {
        val double = doubles[name] ?: return emptyList()
        if (n == 0 || Math.abs(n) > double.calls.size) return emptyList()
        val call = log[double.calls[if (n > 0) n - 1 else double.calls.size + n]]
        return listOf(call.method) + call.args
    }

    fun inOrder(steps: List<List<String>>): Boolean {
        var step = 0
        for (call in log) {
            if (step == steps.size) break
            val wanted = steps[step]
            if (wanted[0] == call.name && wanted[1] == call.method && fits(wanted.drop(2), call.args)) step++
        }
        return step == steps.size
    }

    // Level 3
    fun addMock(name: String, strict: Boolean): Boolean = add(name, mock = true, strict = strict)

    fun expect(name: String, method: String, args: List<String>, answer: String, times: Int): Boolean {
        val double = doubles[name]
        if (double == null || !double.mock) return false
        double.expectations.add(Expectation(method, args.toList(), answer, times))
        return true
    }

    fun verify(name: String): List<String> {
        val double = doubles[name] ?: return listOf(UNKNOWN)
        val missing = double.expectations.filter { it.used < it.times }
            .map { "missing $name.${it.method}(${it.pattern.joinToString(",")}) ${it.used}/${it.times}" }
        val surprises = double.unexpected
            .map { (method, args) -> "unexpected $name.$method(${args.joinToString(",")})" }
        return missing + surprises
    }

    fun verifyAll(): List<String> = doubles.filterValues { it.mock }.keys.flatMap { verify(it) }

    // Level 4
    fun now(): Long = clock

    fun schedule(delay: Long, name: String, method: String, args: List<String>): Int =
        timer(delay, 0, name, method, args)

    fun every(interval: Long, name: String, method: String, args: List<String>): Int =
        timer(interval, interval, name, method, args)

    fun cancel(timerId: Int): Boolean {
        val timer = timers.getOrNull(timerId - 1)
        if (timer == null || timer.stopped) return false
        timer.stopped = true
        return true
    }

    fun advance(ms: Long): List<String> {
        val end = clock + ms
        val fired = ArrayList<String>()
        while (heap.isNotEmpty() && heap.peek().due <= end) {
            val entry = heap.poll()
            val timer = timers[entry.timerId - 1]
            if (timer.stopped) continue
            clock = entry.due
            if (timer.interval > 0) push(entry.due + timer.interval, entry.timerId) else timer.stopped = true
            fired.add("${entry.timerId}@${entry.due}")
            call(timer.name, timer.method, timer.args)
        }
        clock = end
        return fired
    }

    fun pending(): List<String> =
        heap.filter { !timers[it.timerId - 1].stopped }.sortedWith(FIRING_ORDER).map { "${it.timerId}@${it.due}" }

    fun callTimes(name: String, method: String): List<Long> {
        val double = doubles[name] ?: return emptyList()
        return double.calls.map { log[it] }.filter { it.method == method }.map { it.time }
    }

    private fun count(name: String, method: String, pattern: List<String>?): Int {
        val double = doubles[name] ?: return -1
        return double.calls.map { log[it] }
            .count { it.method == method && (pattern == null || fits(pattern, it.args)) }
    }

    private fun add(name: String, mock: Boolean, strict: Boolean): Boolean {
        if (name in doubles) return false
        doubles[name] = DoubleState(mock, strict)
        return true
    }

    private fun timer(delay: Long, interval: Long, name: String, method: String, args: List<String>): Int {
        if (name !in doubles) return -1
        timers.add(Timer(name, method, args.toList(), interval))
        push(clock + delay, timers.size)
        return timers.size
    }

    private fun push(due: Long, timerId: Int) {
        sequence++
        heap.add(Entry(due, sequence, timerId))
    }

    private companion object {
        const val UNKNOWN = "!unknown"
        const val UNEXPECTED = "!unexpected"
        val FIRING_ORDER = compareBy<Entry>({ it.due }, { it.sequence })

        fun fits(pattern: List<String>, args: List<String>): Boolean =
            pattern.size == args.size && pattern.indices.all { pattern[it] == "*" || pattern[it] == args[it] }
    }
}
