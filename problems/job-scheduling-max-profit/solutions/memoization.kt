class Solution {
    fun jobScheduling(startTime: IntArray, endTime: IntArray, profit: IntArray): Int {
        val order = startTime.indices.sortedBy { startTime[it] }
        val starts = IntArray(order.size) { startTime[order[it]] }

        // The first position at or after `from` whose start is at least `time` (lower bound).
        fun firstStartingAt(time: Int, from: Int): Int {
            var low = from
            var high = starts.size
            while (low < high) {
                val middle = (low + high) ushr 1
                if (starts[middle] < time) low = middle + 1 else high = middle
            }
            return low
        }

        // memo[index] is the most profit from the jobs at sorted positions index..n-1, or -1.
        val memo = IntArray(order.size) { -1 }

        fun bestFrom(index: Int): Int {
            if (index == order.size) return 0
            if (memo[index] == -1) {
                val job = order[index]
                val following = firstStartingAt(endTime[job], index + 1)
                memo[index] = maxOf(bestFrom(index + 1), profit[job] + bestFrom(following))
            }
            return memo[index]
        }

        return bestFrom(0)
    }
}
