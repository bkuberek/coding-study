import java.util.PriorityQueue

class Solution {
    fun employeeFreeTime(schedule: List<List<IntArray>>): Array<IntArray> {
        // One entry per employee: the start of their next interval, who they are, and its position.
        val upcoming = PriorityQueue<IntArray>(compareBy({ it[0] }, { it[1] }))
        schedule.forEachIndexed { person, shifts -> upcoming.add(intArrayOf(shifts[0][0], person, 0)) }
        val free = mutableListOf<IntArray>()
        var busyUntil = upcoming.peek()[0]
        while (upcoming.isNotEmpty()) {
            val (start, person, position) = upcoming.poll()
            val shifts = schedule[person]
            if (start > busyUntil) {
                free.add(intArrayOf(busyUntil, start))
            }
            busyUntil = maxOf(busyUntil, shifts[position][1])
            if (position + 1 < shifts.size) {
                upcoming.add(intArrayOf(shifts[position + 1][0], person, position + 1))
            }
        }
        return free.toTypedArray()
    }
}
