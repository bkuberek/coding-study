class Solution {
    fun insert(intervals: Array<IntArray>, newInterval: IntArray): Array<IntArray> {
        val before = intervals.takeWhile { it[1] < newInterval[0] }
        val after = intervals.takeLastWhile { it[0] > newInterval[1] }
        val overlapping = intervals.slice(before.size until intervals.size - after.size)
        val start = minOf(newInterval[0], overlapping.firstOrNull()?.get(0) ?: newInterval[0])
        val end = maxOf(newInterval[1], overlapping.lastOrNull()?.get(1) ?: newInterval[1])
        return (before + listOf(intArrayOf(start, end)) + after).toTypedArray()
    }
}
