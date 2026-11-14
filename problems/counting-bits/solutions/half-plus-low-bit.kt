class Solution {
    fun countBits(n: Int): IntArray {
        val bits = IntArray(n + 1)
        for (i in 1..n) {
            // i shr 1 drops the lowest bit of i and is smaller than i, so its count is known.
            bits[i] = bits[i shr 1] + (i and 1)
        }
        return bits
    }
}
