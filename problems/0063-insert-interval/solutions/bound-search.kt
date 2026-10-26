class Solution {
    fun insert(intervals: Array<IntArray>, newInterval: IntArray): Array<IntArray> {
        // Separate sorted intervals have increasing starts and increasing ends.
        val first = firstIndex(intervals) { it[1] >= newInterval[0] }
        val after = firstIndex(intervals) { it[0] > newInterval[1] }
        val merged = if (first < after) {
            intArrayOf(minOf(newInterval[0], intervals[first][0]), maxOf(newInterval[1], intervals[after - 1][1]))
        } else {
            newInterval.copyOf()
        }
        return intervals.copyOfRange(0, first) + arrayOf(merged) + intervals.copyOfRange(after, intervals.size)
    }

    private inline fun firstIndex(intervals: Array<IntArray>, isPast: (IntArray) -> Boolean): Int {
        var low = 0
        var high = intervals.size
        while (low < high) {
            val middle = (low + high) ushr 1
            if (isPast(intervals[middle])) high = middle else low = middle + 1
        }
        return low
    }
}
