class Solution {
    fun getSum(a: Int, b: Int): Int {
        var result = 0
        var carry = 0
        for (position in 0 until WORD_BITS) {
            val x = (a ushr position) and 1
            val y = (b ushr position) and 1
            result = result or ((x xor y xor carry) shl position)
            carry = (x and y) or (carry and (x xor y)) // carry out: at least two of the three bits
        }
        return result
    }

    private companion object {
        const val WORD_BITS = 32
    }
}
