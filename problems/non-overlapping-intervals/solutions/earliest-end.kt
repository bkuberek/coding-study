class Solution {
    fun eraseOverlapIntervals(intervals: Array<IntArray>): Int {
        var kept = 0
        var lastEnd = Long.MIN_VALUE
        for ((start, end) in intervals.sortedBy { it[1] }) {
            if (start >= lastEnd) {
                kept++
                lastEnd = end.toLong()
            }
        }
        return intervals.size - kept
    }
}
