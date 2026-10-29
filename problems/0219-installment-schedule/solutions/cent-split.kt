import java.math.BigDecimal
import java.time.LocalDate

class Solution {
    fun installmentSchedule(premium: BigDecimal, installmentCount: Int, firstDueDate: LocalDate): Array<Array<String>> {
        if (installmentCount == 0) return emptyArray()
        val cents = premium.movePointRight(2).longValueExact() // exact: at most two fractional digits
        val base = cents / installmentCount
        val leftover = cents % installmentCount
        return Array(installmentCount) { number ->
            // Leftover cents go to the first installments.
            val amount = if (number < leftover) base + 1 else base
            // plusMonths counts from the anchor and clamps to the last day of a short month.
            val due = firstDueDate.plusMonths(number.toLong())
            arrayOf(due.toString(), BigDecimal.valueOf(amount, 2).toPlainString())
        }
    }
}
