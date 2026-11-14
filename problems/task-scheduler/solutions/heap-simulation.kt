import java.util.PriorityQueue

class Solution {
    fun leastInterval(tasks: CharArray, cooldown: Int): Int {
        val counts = IntArray(26)
        for (task in tasks) counts[task - 'A']++
        // Remaining counts of the tasks that may run now, largest first.
        val ready = PriorityQueue<Int>(reverseOrder())
        counts.filter { it > 0 }.forEach(ready::offer)
        // Tasks that just ran, as (time they may run again, remaining count), in time order.
        val cooling = ArrayDeque<Pair<Int, Int>>()
        var time = 0
        while (ready.isNotEmpty() || cooling.isNotEmpty()) {
            if (ready.isNotEmpty()) {
                val remaining = ready.poll() - 1
                if (remaining > 0) cooling.addLast(time + cooldown + 1 to remaining)
                time++
            } else {
                time = cooling.first().first // nothing can run: skip the idle stretch at once
            }
            while (cooling.isNotEmpty() && cooling.first().first <= time) {
                ready.offer(cooling.removeFirst().second)
            }
        }
        return time
    }
}
