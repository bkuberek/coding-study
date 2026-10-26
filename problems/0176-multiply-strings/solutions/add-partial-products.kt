class Solution {
    fun multiply(num1: String, num2: String): String {
        if (num1 == "0" || num2 == "0") return "0"
        val first = num1.reversed().map { it - '0' } // little-endian
        var total = listOf<Int>()
        // School method: one row per digit of num2, shifted by its position.
        for ((shift, ch) in num2.reversed().withIndex()) {
            val row = List(shift) { 0 } + timesDigit(first, ch - '0')
            total = add(total, row)
        }
        return total.asReversed().joinToString("")
    }

    /** Little-endian digits of (digits * factor). */
    private fun timesDigit(digits: List<Int>, factor: Int): List<Int> {
        val product = ArrayList<Int>(digits.size + 1)
        var carry = 0
        for (digit in digits) {
            val value = digit * factor + carry
            product.add(value % 10)
            carry = value / 10
        }
        if (carry > 0) product.add(carry)
        return product
    }

    /** Little-endian digits of left + right. */
    private fun add(left: List<Int>, right: List<Int>): List<Int> {
        val length = maxOf(left.size, right.size)
        val total = ArrayList<Int>(length + 1)
        var carry = 0
        for (position in 0 until length) {
            val value = left.getOrElse(position) { 0 } + right.getOrElse(position) { 0 } + carry
            total.add(value % 10)
            carry = value / 10
        }
        if (carry > 0) total.add(carry)
        return total
    }
}
