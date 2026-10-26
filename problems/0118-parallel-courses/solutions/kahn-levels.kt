class Solution {
    fun minimumSemesters(n: Int, relations: Array<IntArray>): Int {
        val unlocks = List(n + 1) { mutableListOf<Int>() }
        val waiting = IntArray(n + 1)
        for ((before, after) in relations) {
            unlocks[before].add(after)
            waiting[after]++
        }
        var semesterCourses = (1..n).filter { waiting[it] == 0 }
        var semesters = 0
        var taken = 0
        while (semesterCourses.isNotEmpty()) {
            semesters++
            taken += semesterCourses.size
            val nextSemester = mutableListOf<Int>()
            for (course in semesterCourses) {
                for (unlocked in unlocks[course]) {
                    if (--waiting[unlocked] == 0) nextSemester.add(unlocked)
                }
            }
            semesterCourses = nextSemester
        }
        return if (taken == n) semesters else -1
    }
}
