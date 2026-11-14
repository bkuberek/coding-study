class Solution {
    fun numOfMinutes(n: Int, headID: Int, manager: IntArray, informTime: IntArray): Int {
        val reports = Array(n) { mutableListOf<Int>() }
        manager.forEachIndexed { employee, boss ->
            if (boss != -1) reports[boss].add(employee)
        }
        var longest = 0
        // Each entry is (employee, minute at which they hear the news).
        val pending = ArrayDeque<Pair<Int, Int>>()
        pending.addLast(headID to 0)
        while (pending.isNotEmpty()) {
            val (employee, heardAt) = pending.removeLast()
            longest = maxOf(longest, heardAt)
            val passedOnAt = heardAt + informTime[employee]
            for (report in reports[employee]) {
                pending.addLast(report to passedOnAt)
            }
        }
        return longest
    }
}
