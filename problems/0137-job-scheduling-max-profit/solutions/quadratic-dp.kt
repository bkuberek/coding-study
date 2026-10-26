class Solution {
    fun jobScheduling(startTime: IntArray, endTime: IntArray, profit: IntArray): Int {
        val order = startTime.indices.sortedBy { endTime[it] }
        // best[i] is the most profit from the first i jobs in end-time order.
        val best = IntArray(order.size + 1)
        for ((i, job) in order.withIndex()) {
            // Walk back to the last job that ends no later than this one starts.
            var compatible = i - 1
            while (compatible >= 0 && endTime[order[compatible]] > startTime[job]) compatible--
            best[i + 1] = maxOf(best[i], profit[job] + best[compatible + 1])
        }
        return best[order.size]
    }
}
