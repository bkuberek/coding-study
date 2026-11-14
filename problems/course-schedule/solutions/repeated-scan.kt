class Solution {
    fun canFinish(numCourses: Int, prerequisites: Array<IntArray>): Boolean {
        val required = List(numCourses) { mutableListOf<Int>() }
        for ((course, before) in prerequisites) {
            required[course].add(before)
        }
        val taken = BooleanArray(numCourses)
        repeat(numCourses) {
            // Take the first course whose prerequisites are all done; give up if there is none.
            val next = (0 until numCourses).firstOrNull { course ->
                !taken[course] && required[course].all { taken[it] }
            } ?: return false
            taken[next] = true
        }
        return true
    }
}
