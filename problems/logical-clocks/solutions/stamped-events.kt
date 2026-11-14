private class Stamp(
    val process: Int,
    val lamport: Int,
    val vector: IntArray,
    val l: Long,
    val c: Long,
    val wall: Long,
    val isSend: Boolean,
) {
    var value: String = ""
}

private fun atMost(first: IntArray, second: IntArray): Boolean = first.indices.all { first[it] <= second[it] }

/**
 * The update of Kulkarni et al.: `l` is the largest physical reading heard of, and `c` counts the
 * events since `l` last changed.
 */
private fun nextHybrid(current: Pair<Long, Long>, wall: Long, sent: Stamp?): Pair<Long, Long> {
    val (oldL, oldC) = current
    if (sent == null) {
        val l = maxOf(oldL, wall)
        return l to (if (l == oldL) oldC + 1 else 0L)
    }
    val l = maxOf(oldL, sent.l, wall)
    return when {
        l == oldL && l == sent.l -> l to maxOf(oldC, sent.c) + 1
        l == oldL -> l to oldC + 1
        l == sent.l -> l to sent.c + 1
        else -> l to 0L
    }
}

/**
 * Each process keeps the current value of its three clocks: a Lamport counter, a vector and a
 * hybrid pair. Every event updates them by the rules of its kind and keeps a copy as its stamp,
 * so every question afterwards is answered from the stamps alone.
 */
class LogicalClocks(private val processes: Int) {
    private val lamportNow = IntArray(processes)
    private val vectorNow = Array(processes) { IntArray(processes) }
    private val hybridNow = Array(processes) { 0L to 0L }
    private val events = HashMap<String, Stamp>()
    private val received = HashSet<String>()
    private val writes = HashMap<String, MutableList<String>>()

    // Level 1
    fun local(process: Int, event: String, wall: Long): Int = record(process, event, wall, null, false)

    fun send(process: Int, event: String, wall: Long): Int = record(process, event, wall, null, true)

    fun receive(process: Int, event: String, message: String, wall: Long): Int {
        val sent = events[message] ?: return -1
        if (!sent.isSend || message in received || sent.process == process) return -1
        val stamp = record(process, event, wall, sent, false)
        if (stamp != -1) received.add(message)
        return stamp
    }

    fun totalOrder(): List<String> = sortedBy(compareBy<Stamp>({ it.lamport }, { it.process }))

    // Level 2
    fun vector(event: String): List<Int> = events[event]?.vector?.toList() ?: emptyList()

    fun compare(first: String, second: String): String {
        val one = events[first] ?: return ""
        val other = events[second] ?: return ""
        return when {
            first == second -> "same"
            atMost(one.vector, other.vector) -> "before"
            atMost(other.vector, one.vector) -> "after"
            else -> "concurrent"
        }
    }

    // Level 3
    fun write(process: Int, event: String, key: String, value: String, wall: Long): Int {
        val stamp = record(process, event, wall, null, false)
        if (stamp != -1) {
            events.getValue(event).value = value
            writes.getOrPut(key) { ArrayList() }.add(event)
        }
        return stamp
    }

    fun read(process: Int, key: String): List<String> {
        if (process !in 0 until processes) return emptyList()
        val now = vectorNow[process]
        val known = writes[key].orEmpty().map { events.getValue(it) }.filter { atMost(it.vector, now) }
        val siblings = known.filter { stamp -> known.none { it !== stamp && atMost(stamp.vector, it.vector) } }
        return siblings.map { it.value }.sorted()
    }

    fun concurrentWrites(key: String): List<List<String>> {
        val names = writes[key].orEmpty().sorted()
        val pairs = ArrayList<List<String>>()
        for (i in names.indices) {
            for (j in i + 1 until names.size) {
                if (compare(names[i], names[j]) == "concurrent") pairs.add(listOf(names[i], names[j]))
            }
        }
        return pairs
    }

    // Level 4
    fun hlc(event: String): List<Long> = events[event]?.let { listOf(it.l, it.c) } ?: emptyList()

    fun hlcOrder(): List<String> = sortedBy(compareBy<Stamp>({ it.l }, { it.c }, { it.process }))

    fun maxOffset(): Long = events.values.maxOfOrNull { it.l - it.wall } ?: 0L

    // Shared
    private fun sortedBy(order: Comparator<Stamp>): List<String> =
        events.keys.sortedWith { a, b -> order.compare(events.getValue(a), events.getValue(b)) }

    private fun record(process: Int, event: String, wall: Long, sent: Stamp?, isSend: Boolean): Int {
        if (process !in 0 until processes || event in events) return -1
        var lamport = lamportNow[process]
        val vector = vectorNow[process].copyOf()
        if (sent == null) {
            lamport += 1
        } else {
            lamport = maxOf(lamport, sent.lamport) + 1
            for (i in 0 until processes) vector[i] = maxOf(vector[i], sent.vector[i])
        }
        vector[process] += 1
        val hybrid = nextHybrid(hybridNow[process], wall, sent)
        lamportNow[process] = lamport
        vectorNow[process] = vector
        hybridNow[process] = hybrid
        events[event] = Stamp(process, lamport, vector, hybrid.first, hybrid.second, wall, isSend)
        return lamport
    }
}
