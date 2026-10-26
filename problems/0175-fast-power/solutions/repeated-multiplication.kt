import kotlin.math.abs

class Solution {
    fun myPow(x: Double, n: Int): Double {
        val base = if (n >= 0) x else 1 / x
        var remaining = abs(n.toLong()) // abs(Int.MIN_VALUE) would stay negative
        var result = 1.0
        var done = 0L
        while (done < remaining) {
            result *= base
            done++
            if (result == 1.0) {
                // base^done == 1, so the powers repeat with period done (x = 1 or x = -1).
                remaining = (remaining - done) % done
                done = 0
            } else if (result == 0.0 || result.isInfinite()) {
                break // further multiplications cannot change the result
            }
        }
        return result
    }
}
