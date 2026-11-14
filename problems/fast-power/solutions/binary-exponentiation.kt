class Solution {
    fun myPow(x: Double, n: Int): Double {
        // Widen first: -n overflows for n = Int.MIN_VALUE.
        var exponent = n.toLong()
        var base = x
        if (exponent < 0) {
            base = 1 / base
            exponent = -exponent
        }
        var result = 1.0
        // Invariant: result * base^exponent equals the original x^n.
        while (exponent > 0) {
            if ((exponent and 1L) == 1L) result *= base
            base *= base
            exponent = exponent shr 1
        }
        return result
    }
}
