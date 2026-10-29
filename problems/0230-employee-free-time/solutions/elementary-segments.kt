class Solution {
    fun employeeFreeTime(schedule: List<List<IntArray>>): Array<IntArray> {
        val intervals = schedule.flatten()
        val points = intervals.flatMap { listOf(it[0], it[1]) }.toSortedSet().toList()
        return points
            .zipWithNext()
            // No interval starts or ends strictly inside (left, right): it is all busy or all free.
            .filter { (left, _) -> intervals.none { it[0] <= left && left < it[1] } }
            .map { (left, right) -> intArrayOf(left, right) }
            .toTypedArray()
    }
}
