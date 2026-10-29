import java.math.BigDecimal
import java.math.RoundingMode
import java.time.LocalDate
import java.time.temporal.ChronoUnit

class Solution {
    fun earnedPremium(premiums: Array<BigDecimal>, terms: Array<Array<LocalDate>>, valuationDate: LocalDate): BigDecimal {
        var total = BigDecimal.ZERO
        for (i in premiums.indices) {
            val (start, end) = terms[i]
            val termDays = ChronoUnit.DAYS.between(start, end)
            val earnedDays = ChronoUnit.DAYS.between(start, valuationDate).coerceIn(0, termDays)
            // `/` would keep the premium's scale and round half-even, so divide with an explicit scale.
            // Each policy is rounded to cents on its own; the book total is the sum of rounded amounts.
            total += (premiums[i] * BigDecimal.valueOf(earnedDays))
                .divide(BigDecimal.valueOf(termDays), 2, RoundingMode.HALF_UP)
        }
        return total
    }
}
