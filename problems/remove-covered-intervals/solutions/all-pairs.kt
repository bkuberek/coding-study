class Solution {
    fun removeCoveredIntervals(intervals: Array<IntArray>): Int =
        intervals.indices.count { i -> !isCovered(intervals, i) }

    private fun isCovered(intervals: Array<IntArray>, i: Int): Boolean =
        // The interval itself would cover itself, so skip j == i.
        intervals.indices.any { j ->
            j != i && intervals[j][0] <= intervals[i][0] && intervals[i][1] <= intervals[j][1]
        }
}
