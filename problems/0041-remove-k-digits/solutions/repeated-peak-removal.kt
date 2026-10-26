class Solution {
    fun removeKDigits(num: String, k: Int): String {
        val digits = StringBuilder(num)
        repeat(k) {
            // The first digit larger than its successor, or the last digit if none is.
            var peak = 0
            while (peak + 1 < digits.length && digits[peak] <= digits[peak + 1]) {
                peak++
            }
            digits.deleteAt(peak)
        }
        return digits.trimStart('0').ifEmpty { "0" }.toString()
    }
}
