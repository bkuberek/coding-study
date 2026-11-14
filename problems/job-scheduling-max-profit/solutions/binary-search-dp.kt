class Solution {
    fun jobScheduling(startTime: IntArray, endTime: IntArray, profit: IntArray): Int {
        val order = startTime.indices.sortedBy { endTime[it] }
        val ends = IntArray(order.size) { endTime[order[it]] }
        // best[i] is the most profit from the first i jobs in end-time order.
        val best = IntArray(order.size + 1)
        for ((i, job) in order.withIndex()) {
            // Upper bound: how many of the first i jobs end no later than this one starts.
            var low = 0
            var high = i
            while (low < high) {
                val middle = (low + high) ushr 1
                if (ends[middle] <= startTime[job]) low = middle + 1 else high = middle
            }
            best[i + 1] = maxOf(best[i], profit[job] + best[low])
        }
        return best[order.size]
    }
}
