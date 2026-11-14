import java.math.BigDecimal

class Solution {
    fun calculateTax(brackets: Array<IntArray>, income: Int): BigDecimal {
        var cents = 0 // tax in hundredths of a unit: every rate is a whole percent
        var bracket = 0
        for (unit in 0 until income) {
            // Unit number unit covers income from unit to unit + 1.
            while (brackets[bracket][0] <= unit) {
                bracket++
            }
            cents += brackets[bracket][1]
        }
        return BigDecimal.valueOf(cents.toLong(), 2)
    }
}
