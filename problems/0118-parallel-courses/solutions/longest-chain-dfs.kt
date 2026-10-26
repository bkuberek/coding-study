private const val ON_PATH = -1 // marks a course whose chain length is still being computed

class Solution {
    fun minimumSemesters(n: Int, relations: Array<IntArray>): Int {
        val required = List(n + 1) { mutableListOf<Int>() }
        for ((before, after) in relations) {
            required[after].add(before)
        }
        // chain[c]: courses on the longest prerequisite chain ending at c; 0 = not computed yet.
        val chain = IntArray(n + 1)

        // Longest chain ending at course, or -1 if its prerequisites loop.
        fun chainLength(course: Int): Int {
            if (chain[course] == ON_PATH) return -1
            if (chain[course] > 0) return chain[course]
            chain[course] = ON_PATH
            var longest = 0
            for (before in required[course]) {
                val length = chainLength(before)
                if (length < 0) return -1
                longest = maxOf(longest, length)
            }
            chain[course] = longest + 1
            return chain[course]
        }

        var semesters = 0
        for (course in 1..n) {
            val length = chainLength(course)
            if (length < 0) return -1
            semesters = maxOf(semesters, length)
        }
        return semesters
    }
}
