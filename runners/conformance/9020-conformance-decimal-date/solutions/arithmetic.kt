import java.math.BigDecimal
import java.math.RoundingMode
import java.time.LocalDate
import java.time.temporal.ChronoUnit

class DecimalDates {
    private companion object {
        const val CENTS = 2
    }

    fun normalized(value: BigDecimal): BigDecimal = value

    fun add(left: BigDecimal, right: BigDecimal): BigDecimal = left + right

    fun total(values: Array<BigDecimal>): BigDecimal = values.fold(BigDecimal.ZERO) { sum, value -> sum + value }

    fun roundHalfUp(value: BigDecimal): BigDecimal = value.setScale(CENTS, RoundingMode.HALF_UP)

    fun roundHalfEven(value: BigDecimal): BigDecimal = value.setScale(CENTS, RoundingMode.HALF_EVEN)

    fun prorate(premium: BigDecimal, days: Int, totalDays: Int): BigDecimal =
        (premium * BigDecimal(days)).divide(BigDecimal(totalDays), CENTS, RoundingMode.HALF_UP)

    fun addDays(day: LocalDate, days: Int): LocalDate = day.plusDays(days.toLong())

    fun daysBetween(start: LocalDate, end: LocalDate): Int = ChronoUnit.DAYS.between(start, end).toInt()
}
