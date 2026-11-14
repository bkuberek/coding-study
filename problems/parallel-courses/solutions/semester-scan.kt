class Solution {
    fun minimumSemesters(n: Int, relations: Array<IntArray>): Int {
        val required = List(n + 1) { mutableListOf<Int>() }
        for ((before, after) in relations) {
            required[after].add(before)
        }
        val finishedIn = IntArray(n + 1) // semester a course was taken in; 0 while not taken
        var done = 0
        var semester = 0
        while (done < n) {
            semester++
            val current = semester
            // Free courses need every prerequisite finished in an earlier semester.
            val free = (1..n).filter { course ->
                finishedIn[course] == 0 && required[course].all { finishedIn[it] in 1 until current }
            }
            if (free.isEmpty()) return -1
            for (course in free) finishedIn[course] = current
            done += free.size
        }
        return semester
    }
}
