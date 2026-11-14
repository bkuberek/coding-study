private const val UNVISITED = 0
private const val ON_PATH = 1
private const val DONE = 2

class Solution {
    fun canFinish(numCourses: Int, prerequisites: Array<IntArray>): Boolean {
        val required = List(numCourses) { mutableListOf<Int>() }
        for ((course, before) in prerequisites) {
            required[course].add(before)
        }
        val state = IntArray(numCourses) { UNVISITED }

        // Whether every prerequisite chain below course ends without looping.
        fun completes(course: Int): Boolean {
            state[course] = ON_PATH
            for (before in required[course]) {
                if (state[before] == ON_PATH) return false // the chain came back to a course still being explored
                if (state[before] == UNVISITED && !completes(before)) return false
            }
            state[course] = DONE
            return true
        }

        return (0 until numCourses).all { state[it] == DONE || completes(it) }
    }
}
