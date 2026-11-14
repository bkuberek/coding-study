import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.*;

public class Solution {
    private static final BigDecimal NO_EARNED_PREMIUM = BigDecimal.ONE.negate();

    public List<BigDecimal> lossRatios(
            LocalDate[] earnedDates,
            BigDecimal[] earnedAmounts,
            LocalDate[] lossDates,
            BigDecimal[] lossAmounts,
            LocalDate fromDate,
            LocalDate toDate,
            int periodMonths) {
        int first = periodIndex(fromDate, periodMonths);
        int count = periodIndex(toDate, periodMonths) - first + 1;
        BigDecimal[] earned = sumByPeriod(earnedDates, earnedAmounts, periodMonths, first, count);
        BigDecimal[] losses = sumByPeriod(lossDates, lossAmounts, periodMonths, first, count);
        List<BigDecimal> ratios = new ArrayList<>();
        for (int slot = 0; slot < count; slot++) {
            // signum, not equals(ZERO): a total of 0.00 is not equal to ZERO.
            if (earned[slot].signum() == 0) {
                ratios.add(NO_EARNED_PREMIUM);
            } else {
                ratios.add(losses[slot].divide(earned[slot], 4, RoundingMode.HALF_UP));
            }
        }
        return ratios;
    }

    // Periods are calendar-aligned blocks of months counted from January of year 0.
    private static int periodIndex(LocalDate day, int periodMonths) {
        return (day.getYear() * 12 + day.getMonthValue() - 1) / periodMonths;
    }

    private static BigDecimal[] sumByPeriod(
            LocalDate[] dates, BigDecimal[] amounts, int periodMonths, int first, int count) {
        BigDecimal[] totals = new BigDecimal[count];
        Arrays.fill(totals, BigDecimal.ZERO);
        for (int i = 0; i < dates.length; i++) {
            int slot = periodIndex(dates[i], periodMonths) - first;
            if (slot >= 0 && slot < count) {
                totals[slot] = totals[slot].add(amounts[i]);
            }
        }
        return totals;
    }
}
