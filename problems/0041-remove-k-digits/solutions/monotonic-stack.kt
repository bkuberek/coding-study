class Solution {
    fun removeKDigits(num: String, k: Int): String {
        // The digits kept so far, used as a stack; they never decrease from bottom to top.
        val kept = StringBuilder(num.length)
        var remaining = k
        for (digit in num) {
            while (remaining > 0 && kept.isNotEmpty() && kept.last() > digit) {
                kept.setLength(kept.length - 1)
                remaining--
            }
            kept.append(digit)
        }
        // The kept digits never decrease, so leftover deletions are cheapest at the end.
        kept.setLength(kept.length - remaining)
        return kept.trimStart('0').ifEmpty { "0" }.toString()
    }
}
