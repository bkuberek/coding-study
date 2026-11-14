class Solution {
    fun findOrder(numCourses: Int, prerequisites: Array<IntArray>): IntArray {
        val required = Array(numCourses) { mutableListOf<Int>() }
        for ((course, before) in prerequisites) {
            required[course].add(before)
        }
        val taken = BooleanArray(numCourses)
        val order = IntArray(numCourses)
        for (round in 0 until numCourses) {
            // Take the first course whose prerequisites are all done; give up if there is none.
            val next = (0 until numCourses).firstOrNull { course ->
                !taken[course] && required[course].all { taken[it] }
            } ?: return IntArray(0)
            taken[next] = true
            order[round] = next
        }
        return order
    }
}
