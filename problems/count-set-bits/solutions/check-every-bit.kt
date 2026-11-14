class Solution {
    fun hammingWeight(n: Long): Int {
        var count = 0
        for (position in 0 until WORD_BITS) {
            count += ((n ushr position) and 1L).toInt()
        }
        return count
    }

    private companion object {
        const val WORD_BITS = 32
    }
}
