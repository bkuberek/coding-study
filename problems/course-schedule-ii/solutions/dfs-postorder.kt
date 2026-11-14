class Solution {
    private companion object {
        const val UNSEEN = 0
        const val ACTIVE = 1
        const val DONE = 2
    }

    fun findOrder(numCourses: Int, prerequisites: Array<IntArray>): IntArray {
        val required = Array(numCourses) { mutableListOf<Int>() }
        for ((course, before) in prerequisites) {
            required[course].add(before)
        }
        val state = IntArray(numCourses)
        val cursor = IntArray(numCourses) // next prerequisite to visit, per course
        val order = IntArray(numCourses)
        var listed = 0
        for (root in 0 until numCourses) {
            if (state[root] != UNSEEN) continue
            state[root] = ACTIVE
            val stack = ArrayDeque<Int>()
            stack.addLast(root)
            while (stack.isNotEmpty()) {
                val course = stack.last()
                if (cursor[course] == required[course].size) {
                    // Every prerequisite is already in the order: the course can follow them.
                    stack.removeLast()
                    state[course] = DONE
                    order[listed++] = course
                    continue
                }
                val before = required[course][cursor[course]++]
                if (state[before] == ACTIVE) {
                    return IntArray(0) // the path loops back to a course still being explored
                }
                if (state[before] == UNSEEN) {
                    state[before] = ACTIVE
                    stack.addLast(before)
                }
            }
        }
        return order
    }
}
