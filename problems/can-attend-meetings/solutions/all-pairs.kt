class Solution {
    fun canAttendMeetings(intervals: Array<IntArray>): Boolean {
        for (i in intervals.indices) {
            for (j in i + 1 until intervals.size) {
                // Half-open meetings share a moment exactly when each starts before the other ends.
                if (intervals[i][0] < intervals[j][1] && intervals[j][0] < intervals[i][1]) {
                    return false
                }
            }
        }
        return true
    }
}
