import java.math.BigDecimal
import java.math.RoundingMode
import java.time.LocalDate
import java.time.temporal.ChronoUnit
import java.util.TreeMap

class EndorsedPolicy(
    private val termStart: LocalDate,
    private val termEnd: LocalDate,
    fullTermPremium: BigDecimal,
) {
    private val termDays = ChronoUnit.DAYS.between(termStart, termEnd)

    // Effective date -> the full-term premium in force from that date on.
    private val endorsements = TreeMap<LocalDate, BigDecimal>().apply { put(termStart, fullTermPremium) }

    fun endorse(effectiveDate: LocalDate, fullTermPremium: BigDecimal): Boolean {
        if (effectiveDate < termStart || effectiveDate >= termEnd) return false
        endorsements[effectiveDate] = fullTermPremium // same date: the later endorsement corrects it
        return true
    }

    fun premiumOn(onDate: LocalDate): BigDecimal {
        if (onDate < termStart || onDate >= termEnd) return OUTSIDE_TERM
        return endorsements.floorEntry(onDate).value
    }

    fun writtenPremium(): BigDecimal = earnedPremium(termEnd)

    fun earnedPremium(asOfDate: LocalDate): BigDecimal {
        val cutoff = asOfDate.coerceIn(termStart, termEnd)
        var weighted = BigDecimal.ZERO // sum of premium * days over the segments before the cutoff, exact
        for ((start, premium) in endorsements) {
            if (start >= cutoff) break
            val end = endorsements.higherKey(start) ?: termEnd
            val days = ChronoUnit.DAYS.between(start, minOf(end, cutoff))
            weighted += premium * BigDecimal.valueOf(days)
        }
        // `/` would keep the dividend's scale and round half-even, so divide with an explicit scale.
        return weighted.divide(BigDecimal.valueOf(termDays), 2, RoundingMode.HALF_UP)
    }

    private companion object {
        val OUTSIDE_TERM: BigDecimal = BigDecimal.ONE.negate()
    }
}
