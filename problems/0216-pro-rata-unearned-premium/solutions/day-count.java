import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;

public class Solution {
    private static final BigDecimal OUTSIDE_TERM = BigDecimal.ONE.negate();

    public BigDecimal unearnedPremium(
            BigDecimal termPremium, LocalDate termStart, LocalDate termEnd, LocalDate changeDate) {
        if (changeDate.isBefore(termStart) || changeDate.isAfter(termEnd)) {
            return OUTSIDE_TERM;
        }
        long remaining = ChronoUnit.DAYS.between(changeDate, termEnd);
        long termDays = ChronoUnit.DAYS.between(termStart, termEnd);
        return termPremium
                .multiply(BigDecimal.valueOf(remaining))
                .divide(BigDecimal.valueOf(termDays), 2, RoundingMode.HALF_UP);
    }
}
