import java.util.PriorityQueue

class Solution {
    fun getOrder(tasks: Array<IntArray>): IntArray {
        val arrivals = tasks.indices.sortedBy { tasks[it][0] }
        // Waiting tasks by processing time, then by index.
        val waiting = PriorityQueue<Int>(compareBy<Int> { tasks[it][1] }.thenBy { it })
        val order = IntArray(tasks.size)
        var time = 0L // a sum of processing times can pass Int.MAX_VALUE
        var next = 0
        for (picked in tasks.indices) {
            if (waiting.isEmpty() && time < tasks[arrivals[next]][0]) {
                time = tasks[arrivals[next]][0].toLong() // idle until the next arrival
            }
            while (next < tasks.size && tasks[arrivals[next]][0] <= time) {
                waiting.offer(arrivals[next++])
            }
            val index = waiting.poll()
            time += tasks[index][1]
            order[picked] = index
        }
        return order
    }
}
