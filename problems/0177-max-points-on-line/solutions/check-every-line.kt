class Solution {
    fun maxPoints(points: Array<IntArray>): Int {
        if (points.size <= 2) return points.size
        var best = 2
        for (i in points.indices) {
            val (x1, y1) = points[i]
            for (j in i + 1 until points.size) {
                val dx = points[j][0] - x1
                val dy = points[j][1] - y1
                // (x, y) is on the line through both points when the cross product is zero.
                val onLine = points.count { (x, y) -> dy * (x - x1) == dx * (y - y1) }
                best = maxOf(best, onLine)
            }
        }
        return best
    }
}
