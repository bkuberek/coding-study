/**
 * A workload of processes and the result of the latest run over it.
 *
 * First come, first served and shortest job first run each process to completion, so they jump
 * from one completion to the next. Round robin, the feedback queue and the cores advance a clock
 * one tick at a time and settle each tick in the order the statement fixes: the slice that ends,
 * the arrivals, the process that goes back to its queue, a boost, a preemption, a dispatch and
 * then a steal. One core records its segments, merging a slice that continues the one before.
 * Round robin is the case of one core without stealing.
 */
class CpuScheduler {
    private class Segment(val pid: String, val start: Int, var end: Int)

    private class Core {
        val segments = ArrayList<Segment>()
        var last: String? = null
        var switches = 0
        var busy = 0

        fun run(pid: String, start: Int, end: Int) {
            val tail = segments.lastOrNull()
            if (tail != null && tail.pid == pid && tail.end == start) {
                tail.end = end
            } else {
                if (last != null && last != pid) switches++
                segments.add(Segment(pid, start, end))
            }
            last = pid
            busy += end - start
        }
    }

    private class Run(pids: List<String>, coreCount: Int) {
        val pids = pids.toList()
        val first = HashMap<String, Int>()
        val done = HashMap<String, Int>()
        val cores = List(coreCount) { Core() }
        var migrations = 0
        var makespan = 0

        fun started(pid: String, time: Int) {
            first.putIfAbsent(pid, time)
        }

        fun timelines(): List<List<String>> =
            cores.map { core -> core.segments.map { "${it.pid}:${it.start}-${it.end}" } }
    }

    private val pids = ArrayList<String>()
    private val arrival = HashMap<String, Int>()
    private val burst = HashMap<String, Int>()
    private var latest: Run? = null

    // Level 1
    fun addProcess(pid: String, arrival: Int, burst: Int): Boolean {
        if (pid in this.arrival) return false
        pids.add(pid)
        this.arrival[pid] = arrival
        this.burst[pid] = burst
        return true
    }

    fun runFcfs(): List<String> {
        val run = Run(pids, 1)
        var clock = 0
        for (pid in byArrival()) {
            clock = runToCompletion(run, pid, maxOf(clock, arrival.getValue(pid)))
        }
        return keep(run, clock)[0]
    }

    fun runSjf(): List<String> {
        val run = Run(pids, 1)
        val position = pids.withIndex().associate { it.value to it.index }
        val order = compareBy<String>({ burst.getValue(it) }, { arrival.getValue(it) }, { position.getValue(it) })
        val pending = ArrayList(pids)
        var clock = 0
        while (pending.isNotEmpty()) {
            val now = clock
            val pick = pending.filter { arrival.getValue(it) <= now }.minWithOrNull(order)
            if (pick == null) {
                clock = pending.minOf { arrival.getValue(it) }
                continue
            }
            pending.remove(pick)
            clock = runToCompletion(run, pick, clock)
        }
        return keep(run, clock)[0]
    }

    fun waitingTime(pid: String): Int {
        val turnaround = turnaroundTime(pid)
        return if (turnaround == -1) -1 else turnaround - burst.getValue(pid)
    }

    fun turnaroundTime(pid: String): Int {
        val done = latest?.done?.get(pid) ?: return -1
        return done - arrival.getValue(pid)
    }

    fun averageWaiting(): String = average(::waitingTime)

    fun averageTurnaround(): String = average(::turnaroundTime)

    // Level 2
    fun runRoundRobin(quantum: Int): List<String> = roundRobin(1, quantum, false)[0]

    fun responseTime(pid: String): Int {
        val first = latest?.first?.get(pid) ?: return -1
        return first - arrival.getValue(pid)
    }

    fun averageResponse(): String = average(::responseTime)

    fun contextSwitches(): Int = latest?.cores?.sumOf { it.switches } ?: -1

    // Level 3
    fun runMlfq(quanta: IntArray, boostPeriod: Int): List<String> {
        val run = Run(pids, 1)
        val core = run.cores[0]
        val remaining = HashMap(burst)
        val arrivals = ArrayDeque(byArrival())
        val queues = MutableList(quanta.size) { ArrayDeque<String>() }
        val level = HashMap<String, Int>()
        val used = HashMap<String, Int>()
        var running: String? = null
        var left = pids.size
        var clock = 0
        while (true) {
            var demoted: String? = null
            val current = running
            if (current != null) {
                if (remaining.getValue(current) == 0) {
                    run.done[current] = clock
                    running = null
                    left--
                } else if (used.getValue(current) == quanta[level.getValue(current)]) {
                    level[current] = minOf(level.getValue(current) + 1, quanta.size - 1)
                    used[current] = 0
                    demoted = current
                    running = null
                }
            }
            if (left == 0) break
            while (arrivals.isNotEmpty() && arrival.getValue(arrivals.first()) == clock) {
                val pid = arrivals.removeFirst()
                level[pid] = 0
                used[pid] = 0
                queues[0].addLast(pid)
            }
            if (demoted != null) queues[level.getValue(demoted)].addLast(demoted)
            if (boostPeriod > 0 && clock > 0 && clock % boostPeriod == 0) {
                val merged = ArrayDeque<String>()
                for (queue in queues) {
                    merged.addAll(queue)
                    queue.clear()
                }
                queues[0] = merged
                for (pid in merged + listOfNotNull(running)) {
                    level[pid] = 0
                    used[pid] = 0
                }
            }
            val onCpu = running
            if (onCpu != null && (0 until level.getValue(onCpu)).any { queues[it].isNotEmpty() }) {
                queues[level.getValue(onCpu)].addLast(onCpu)
                running = null
            }
            if (running == null) {
                running = queues.firstOrNull { it.isNotEmpty() }?.removeFirst()
            }
            val pid = running
            if (pid != null) {
                run.started(pid, clock)
                core.run(pid, clock, clock + 1)
                remaining[pid] = remaining.getValue(pid) - 1
                used[pid] = used.getValue(pid) + 1
            }
            clock++
        }
        return keep(run, clock)[0]
    }

    // Level 4
    fun runMulticore(cores: Int, quantum: Int, steal: Boolean): List<List<String>> =
        roundRobin(cores, quantum, steal)

    fun utilization(core: Int): String {
        val run = latest ?: return ""
        if (core !in run.cores.indices) return ""
        return fraction(run.cores[core].busy, run.makespan)
    }

    fun migrations(): Int = latest?.migrations ?: -1

    // The clock loops
    private fun roundRobin(cores: Int, quantum: Int, steal: Boolean): List<List<String>> {
        val run = Run(pids, cores)
        val remaining = HashMap(burst)
        val arrivals = ArrayDeque(byArrival())
        val queues = List(cores) { ArrayDeque<String>() }
        val running = arrayOfNulls<String>(cores)
        val used = IntArray(cores)
        var left = pids.size
        var clock = 0
        while (true) {
            val expired = arrayOfNulls<String>(cores)
            for (c in 0 until cores) {
                val pid = running[c] ?: continue
                if (remaining.getValue(pid) == 0) {
                    run.done[pid] = clock
                    running[c] = null
                    left--
                } else if (used[c] == quantum) {
                    expired[c] = pid
                    running[c] = null
                }
            }
            if (left == 0) break
            while (arrivals.isNotEmpty() && arrival.getValue(arrivals.first()) == clock) {
                val loads = (0 until cores).map { c ->
                    queues[c].size + (if (running[c] != null) 1 else 0) + (if (expired[c] != null) 1 else 0)
                }
                queues[loads.indexOf(loads.min())].addLast(arrivals.removeFirst())
            }
            for (c in 0 until cores) {
                expired[c]?.let { queues[c].addLast(it) }
                if (running[c] == null && queues[c].isNotEmpty()) {
                    running[c] = queues[c].removeFirst()
                    used[c] = 0
                }
            }
            if (steal) {
                for (c in 0 until cores) {
                    if (running[c] != null) continue
                    var victim = 0
                    for (v in 1 until cores) if (queues[v].size > queues[victim].size) victim = v
                    if (queues[victim].isNotEmpty()) {
                        running[c] = queues[victim].removeLast()
                        used[c] = 0
                        run.migrations++
                    }
                }
            }
            for (c in 0 until cores) {
                val pid = running[c] ?: continue
                run.started(pid, clock)
                run.cores[c].run(pid, clock, clock + 1)
                remaining[pid] = remaining.getValue(pid) - 1
                used[c]++
            }
            clock++
        }
        return keep(run, clock)
    }

    private fun runToCompletion(run: Run, pid: String, start: Int): Int {
        val end = start + burst.getValue(pid)
        run.started(pid, start)
        run.cores[0].run(pid, start, end)
        run.done[pid] = end
        return end
    }

    private fun byArrival(): List<String> = pids.sortedBy { arrival.getValue(it) }

    private fun keep(run: Run, makespan: Int): List<List<String>> {
        run.makespan = makespan
        latest = run
        return run.timelines()
    }

    private fun average(metric: (String) -> Int): String {
        val run = latest ?: return ""
        return fraction(run.pids.sumOf(metric), run.pids.size)
    }

    private fun fraction(numerator: Int, denominator: Int): String {
        var a = numerator
        var b = denominator
        while (b != 0) {
            val r = a % b
            a = b
            b = r
        }
        return "${numerator / a}/${denominator / a}"
    }
}
