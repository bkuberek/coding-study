class Solution {
    fun canAttendMeetings(intervals: Array<IntArray>): Boolean {
        // After sorting by start, only neighbors can be the first clash.
        return intervals
            .sortedBy { it[0] }
            .zipWithNext()
            .all { (earlier, later) -> earlier[1] <= later[0] }
    }
}
