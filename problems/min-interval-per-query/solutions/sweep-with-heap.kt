import java.util.PriorityQueue

class Solution {
    fun minInterval(intervals: Array<IntArray>, queries: IntArray): IntArray {
        val byLeft = intervals.sortedBy { it[0] }
        val answer = IntArray(queries.size) { -1 }
        // Entries are {size, right} of intervals that start at or before the current query.
        val candidates = PriorityQueue<IntArray>(compareBy({ it[0] }, { it[1] }))
        var added = 0
        for (index in queries.indices.sortedBy { queries[it] }) {
            val query = queries[index]
            while (added < byLeft.size && byLeft[added][0] <= query) {
                val (left, right) = byLeft[added++]
                candidates.add(intArrayOf(right - left + 1, right))
            }
            // An interval that ends before this query also ends before every later one.
            while (candidates.isNotEmpty() && candidates.peek()[1] < query) {
                candidates.poll()
            }
            candidates.peek()?.let { answer[index] = it[0] }
        }
        return answer
    }
}
