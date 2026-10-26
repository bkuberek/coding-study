private const val MOD = 1_000_000_007L

// Square-and-multiply; both factors stay below MOD, so each product fits in a Long.
private fun power(base: Long, exponent: Long): Long {
    var result = 1L
    var factor = base % MOD
    var rest = exponent
    while (rest > 0) {
        if ((rest and 1L) == 1L) result = result * factor % MOD
        factor = factor * factor % MOD
        rest = rest shr 1
    }
    return result
}

class Solution {
    fun uniquePaths(m: Int, n: Int): Int {
        // A route is a sequence of m + n - 2 moves; choose which of them are the shorter direction.
        val moves = (m + n - 2).toLong()
        val chosen = minOf(m, n) - 1
        var numerator = 1L
        var denominator = 1L
        for (step in 1..chosen) {
            numerator = numerator * (moves - chosen + step) % MOD
            denominator = denominator * step % MOD
        }
        // MOD is prime, so denominator^(MOD - 2) is its inverse (Fermat's little theorem).
        return (numerator * power(denominator, MOD - 2) % MOD).toInt()
    }
}
