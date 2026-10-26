import kotlin.math.abs

class Solution {
    fun maxPoints(points: Array<IntArray>): Int {
        var best = 1
        for (i in points.indices) {
            val (x1, y1) = points[i]
            val directions = HashMap<Long, Int>()
            var most = 0
            for (j in i + 1 until points.size) {
                var dx = points[j][0] - x1
                var dy = points[j][1] - y1
                val divisor = gcd(abs(dx), abs(dy)) // never 0: the points are distinct
                dx /= divisor
                dy /= divisor
                // One representative per direction: dx > 0, or dx == 0 and dy > 0.
                if (dx < 0 || (dx == 0 && dy < 0)) {
                    dx = -dx
                    dy = -dy
                }
                val count = directions.merge(dx * KEY_BASE + dy, 1) { old, one -> old + one }!!
                most = maxOf(most, count)
            }
            best = maxOf(best, most + 1) // + 1 for the anchor
        }
        return best
    }

    private tailrec fun gcd(a: Int, b: Int): Int = if (b == 0) a else gcd(b, a % b)

    private companion object {
        // Reduced components lie in [-2 * 10^4, 2 * 10^4], so this packs a direction into one Long.
        const val KEY_BASE = 100_000L
    }
}
