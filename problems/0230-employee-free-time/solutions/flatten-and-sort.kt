class Solution {
    fun employeeFreeTime(schedule: List<List<IntArray>>): Array<IntArray> {
        val intervals = schedule.flatten().sortedBy { it[0] }
        val free = mutableListOf<IntArray>()
        var busyUntil = intervals[0][1]
        for ((start, end) in intervals) {
            if (start > busyUntil) {
                free.add(intArrayOf(busyUntil, start))
            }
            busyUntil = maxOf(busyUntil, end)
        }
        return free.toTypedArray()
    }
}
