import java.util.PriorityQueue

class Solution {
    fun minMeetingRooms(intervals: Array<IntArray>): Int {
        // End times of the meetings currently holding a room; the smallest is on top.
        val ends = PriorityQueue<Int>()
        for ((start, end) in intervals.sortedBy { it[0] }) {
            if (ends.isNotEmpty() && ends.peek() <= start) {
                ends.poll()
            }
            ends.add(end)
        }
        return ends.size
    }
}
