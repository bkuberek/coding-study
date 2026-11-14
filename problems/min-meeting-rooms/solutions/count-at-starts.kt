class Solution {
    fun minMeetingRooms(intervals: Array<IntArray>): Int =
        // The busiest moment is always the start of some meeting.
        intervals.maxOf { (moment) -> intervals.count { (start, end) -> moment in start until end } }
}
