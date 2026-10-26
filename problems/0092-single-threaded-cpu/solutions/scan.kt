class Solution {
    fun getOrder(tasks: Array<IntArray>): IntArray {
        val done = BooleanArray(tasks.size)
        val order = ArrayList<Int>(tasks.size)
        var time = 0L // a sum of processing times can pass Int.MAX_VALUE
        while (order.size < tasks.size) {
            // Scan every waiting task; a strict < keeps the smaller index on equal times.
            var best = -1
            var nextArrival = Long.MAX_VALUE
            for (index in tasks.indices) {
                if (done[index]) continue
                val (enqueue, processing) = tasks[index]
                if (enqueue <= time) {
                    if (best < 0 || processing < tasks[best][1]) best = index
                } else {
                    nextArrival = minOf(nextArrival, enqueue.toLong())
                }
            }
            if (best < 0) {
                time = nextArrival // idle until the next arrival
                continue
            }
            done[best] = true
            time += tasks[best][1]
            order.add(best)
        }
        return order.toIntArray()
    }
}
