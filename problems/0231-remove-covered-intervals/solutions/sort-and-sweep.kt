class Solution {
    fun removeCoveredIntervals(intervals: Array<IntArray>): Int {
        // Equal starts: the longer interval comes first, so it covers the shorter ones after it.
        val ordered = intervals.sortedWith(compareBy<IntArray>({ it[0] }, { -it[1] }))
        var remaining = 0
        var reach = -1 // the largest end among the intervals already swept
        for ((_, end) in ordered) {
            if (end > reach) {
                remaining++
                reach = end
            }
        }
        return remaining
    }
}
