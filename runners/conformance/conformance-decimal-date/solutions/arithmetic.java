import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.*;

public class DecimalDates {
    private static final int CENTS = 2;

    public DecimalDates() {
    }

    public BigDecimal normalized(BigDecimal value) {
        return value;
    }

    public BigDecimal add(BigDecimal left, BigDecimal right) {
        return left.add(right);
    }

    public BigDecimal total(BigDecimal[] values) {
        BigDecimal sum = BigDecimal.ZERO;
        for (BigDecimal value : values) {
            sum = sum.add(value);
        }
        return sum;
    }

    public BigDecimal roundHalfUp(BigDecimal value) {
        return value.setScale(CENTS, RoundingMode.HALF_UP);
    }

    public BigDecimal roundHalfEven(BigDecimal value) {
        return value.setScale(CENTS, RoundingMode.HALF_EVEN);
    }

    public BigDecimal prorate(BigDecimal premium, int days, int totalDays) {
        return premium
                .multiply(BigDecimal.valueOf(days))
                .divide(BigDecimal.valueOf(totalDays), CENTS, RoundingMode.HALF_UP);
    }

    public LocalDate addDays(LocalDate day, int days) {
        return day.plusDays(days);
    }

    public int daysBetween(LocalDate start, LocalDate end) {
        return (int) ChronoUnit.DAYS.between(start, end);
    }
}
