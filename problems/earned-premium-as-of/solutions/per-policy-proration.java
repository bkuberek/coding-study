import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;

public class Solution {
    public BigDecimal earnedPremium(BigDecimal[] premiums, LocalDate[][] terms, LocalDate valuationDate) {
        BigDecimal total = BigDecimal.ZERO;
        for (int i = 0; i < premiums.length; i++) {
            long termDays = ChronoUnit.DAYS.between(terms[i][0], terms[i][1]);
            long earnedDays = Math.min(Math.max(ChronoUnit.DAYS.between(terms[i][0], valuationDate), 0), termDays);
            // Each policy is rounded to cents on its own; the book total is the sum of rounded amounts.
            total = total.add(
                    premiums[i]
                            .multiply(BigDecimal.valueOf(earnedDays))
                            .divide(BigDecimal.valueOf(termDays), 2, RoundingMode.HALF_UP));
        }
        return total;
    }
}
