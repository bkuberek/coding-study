import java.math.BigDecimal

class Solution {
    fun calculateTax(brackets: Array<IntArray>, income: Int): BigDecimal {
        var cents = 0 // tax in hundredths of a unit: every rate is a whole percent
        var lower = 0
        for ((upper, percent) in brackets) {
            if (lower >= income) break
            cents += (minOf(upper, income) - lower) * percent
            lower = upper
        }
        return BigDecimal.valueOf(cents.toLong(), 2)
    }
}
