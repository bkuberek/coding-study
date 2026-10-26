class Solution {
    fun eraseOverlapIntervals(intervals: Array<IntArray>): Int {
        val ordered = intervals.sortedBy { it[0] }
        var removed = 0
        var keptEnd = ordered[0][1]
        for ((start, end) in ordered.drop(1)) {
            if (start < keptEnd) {
                // Conflict: keep whichever of the two ends first.
                removed++
                keptEnd = minOf(keptEnd, end)
            } else {
                keptEnd = end
            }
        }
        return removed
    }
}
