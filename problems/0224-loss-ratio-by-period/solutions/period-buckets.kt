import java.math.BigDecimal
import java.math.RoundingMode
import java.time.LocalDate

class Solution {
    fun lossRatios(
        earnedDates: Array<LocalDate>,
        earnedAmounts: Array<BigDecimal>,
        lossDates: Array<LocalDate>,
        lossAmounts: Array<BigDecimal>,
        fromDate: LocalDate,
        toDate: LocalDate,
        periodMonths: Int,
    ): List<BigDecimal> {
        val first = periodIndex(fromDate, periodMonths)
        val count = periodIndex(toDate, periodMonths) - first + 1
        val earned = sumByPeriod(earnedDates, earnedAmounts, periodMonths, first, count)
        val losses = sumByPeriod(lossDates, lossAmounts, periodMonths, first, count)
        return List(count) { slot ->
            // signum, not ==: a total of 0.00 is not equal to ZERO. `/` would round half-even at the loss's scale.
            if (earned[slot].signum() == 0) NO_EARNED_PREMIUM else losses[slot].divide(earned[slot], 4, RoundingMode.HALF_UP)
        }
    }

    // Periods are calendar-aligned blocks of months counted from January of year 0.
    private fun periodIndex(day: LocalDate, periodMonths: Int): Int =
        (day.year * 12 + day.monthValue - 1) / periodMonths

    private fun sumByPeriod(
        dates: Array<LocalDate>,
        amounts: Array<BigDecimal>,
        periodMonths: Int,
        first: Int,
        count: Int,
    ): Array<BigDecimal> {
        val totals = Array(count) { BigDecimal.ZERO }
        for (i in dates.indices) {
            val slot = periodIndex(dates[i], periodMonths) - first
            if (slot in 0 until count) {
                totals[slot] += amounts[i]
            }
        }
        return totals
    }

    private companion object {
        val NO_EARNED_PREMIUM: BigDecimal = BigDecimal.ONE.negate()
    }
}
