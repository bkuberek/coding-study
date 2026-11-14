class Solution {
    fun minInterval(intervals: Array<IntArray>, queries: IntArray): IntArray {
        val points = queries.distinct().sorted().toIntArray()
        val sizeAt = IntArray(points.size) { -1 }
        // nextOpen[k]: a link toward the first point at or after k without an answer yet;
        // points.size is a sentinel meaning "none left".
        val nextOpen = IntArray(points.size + 1) { it }

        fun firstOpen(start: Int): Int {
            var root = start
            while (nextOpen[root] != root) root = nextOpen[root]
            var k = start
            while (nextOpen[k] != root) {
                val next = nextOpen[k]
                nextOpen[k] = root
                k = next
            }
            return root
        }

        for ((left, right) in intervals.sortedBy { it[1] - it[0] }) {
            val firstAtOrAfter = points.binarySearch(left).let { if (it >= 0) it else -(it + 1) }
            var k = firstOpen(firstAtOrAfter)
            while (k < points.size && points[k] <= right) {
                sizeAt[k] = right - left + 1
                nextOpen[k] = k + 1
                k = firstOpen(k + 1)
            }
        }
        return IntArray(queries.size) { j -> sizeAt[points.binarySearch(queries[j])] }
    }
}
