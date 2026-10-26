class Solution {
    fun hammingWeight(n: Long): Int {
        // The low 32 bits as an Int: values from 2^31 up become negative, with the same bits.
        var word = n.toInt()
        var count = 0
        while (word != 0) {
            word = word and (word - 1) // clears the lowest set bit
            count++
        }
        return count
    }
}
