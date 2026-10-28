import java.math.BigDecimal
import java.math.RoundingMode
import java.time.LocalDate
import java.time.temporal.ChronoUnit

class Solution {
    fun unearnedPremium(termPremium: BigDecimal, termStart: LocalDate, termEnd: LocalDate, changeDate: LocalDate): BigDecimal {
        if (changeDate < termStart || changeDate > termEnd) {
            return BigDecimal.ONE.negate()
        }
        val remaining = ChronoUnit.DAYS.between(changeDate, termEnd)
        val termDays = ChronoUnit.DAYS.between(termStart, termEnd)
        // `/` would keep the premium's scale and round half-even, so divide with an explicit scale.
        return (termPremium * BigDecimal.valueOf(remaining))
            .divide(BigDecimal.valueOf(termDays), 2, RoundingMode.HALF_UP)
    }
}
