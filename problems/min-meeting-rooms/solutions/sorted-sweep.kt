class Solution {
    fun minMeetingRooms(intervals: Array<IntArray>): Int {
        val starts = IntArray(intervals.size) { intervals[it][0] }.apply { sort() }
        val ends = IntArray(intervals.size) { intervals[it][1] }.apply { sort() }
        var rooms = 0
        var ended = 0
        for (start in starts) {
            if (ends[ended] <= start) {
                // Some meeting has ended by now: its room is reused.
                ended++
            } else {
                rooms++
            }
        }
        return rooms
    }
}
