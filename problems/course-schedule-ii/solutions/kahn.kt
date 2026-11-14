class Solution {
    fun findOrder(numCourses: Int, prerequisites: Array<IntArray>): IntArray {
        val unlocks = Array(numCourses) { mutableListOf<Int>() }
        val waiting = IntArray(numCourses) // prerequisites each course still waits for
        for ((course, before) in prerequisites) {
            unlocks[before].add(course)
            waiting[course]++
        }
        val ready = ArrayDeque<Int>()
        for (course in 0 until numCourses) {
            if (waiting[course] == 0) ready.addLast(course)
        }
        val order = IntArray(numCourses)
        var taken = 0
        while (ready.isNotEmpty()) {
            val course = ready.removeFirst()
            order[taken++] = course
            for (unlocked in unlocks[course]) {
                if (--waiting[unlocked] == 0) ready.addLast(unlocked)
            }
        }
        // Courses never taken wait, directly or not, on a cycle.
        return if (taken == numCourses) order else IntArray(0)
    }
}
