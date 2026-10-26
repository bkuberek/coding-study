class Solution {
    fun multiply(num1: String, num2: String): String {
        if (num1 == "0" || num2 == "0") return "0"
        val m = num1.length
        val n = num2.length
        // digits[k] is result digit k counted from the left; the product has at most m + n digits.
        val digits = IntArray(m + n)
        for (i in m - 1 downTo 0) {
            val a = num1[i] - '0'
            var carry = 0
            for (j in n - 1 downTo 0) {
                val value = digits[i + j + 1] + a * (num2[j] - '0') + carry
                digits[i + j + 1] = value % 10
                carry = value / 10
            }
            digits[i] += carry
        }
        val start = if (digits[0] == 0) 1 else 0 // at most one leading zero
        return buildString(m + n) {
            for (k in start until digits.size) append('0' + digits[k])
        }
    }
}
