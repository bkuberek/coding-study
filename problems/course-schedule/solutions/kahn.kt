class Solution {
    fun canFinish(numCourses: Int, prerequisites: Array<IntArray>): Boolean {
        val unlocks = List(numCourses) { mutableListOf<Int>() }
        val waiting = IntArray(numCourses) // prerequisites each course still waits for
        for ((course, before) in prerequisites) {
            unlocks[before].add(course)
            waiting[course]++
        }
        val ready = ArrayDeque((0 until numCourses).filter { waiting[it] == 0 })
        var taken = 0
        while (ready.isNotEmpty()) {
            val course = ready.removeFirst()
            taken++
            for (unlocked in unlocks[course]) {
                if (--waiting[unlocked] == 0) ready.addLast(unlocked)
            }
        }
        // Courses never taken wait, directly or not, on a cycle.
        return taken == numCourses
    }
}
