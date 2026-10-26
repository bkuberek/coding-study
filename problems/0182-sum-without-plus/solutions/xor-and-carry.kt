class Solution {
    fun getSum(a: Int, b: Int): Int {
        // Int is 32-bit two's complement, so the carry falls off the top bit as in hardware.
        var sum = a
        var carry = b
        while (carry != 0) {
            val next = (sum and carry) shl 1
            sum = sum xor carry // the sum of every column, ignoring carries
            carry = next
        }
        return sum
    }
}
