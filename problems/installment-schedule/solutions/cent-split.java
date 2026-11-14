import java.math.BigDecimal;
import java.time.LocalDate;

public class Solution {
    public String[][] installmentSchedule(BigDecimal premium, int installmentCount, LocalDate firstDueDate) {
        if (installmentCount == 0) {
            return new String[0][];
        }
        long cents = premium.movePointRight(2).longValueExact(); // exact: at most two fractional digits
        long base = cents / installmentCount;
        long leftover = cents % installmentCount;
        String[][] schedule = new String[installmentCount][];
        for (int number = 0; number < installmentCount; number++) {
            // Leftover cents go to the first installments.
            long amount = number < leftover ? base + 1 : base;
            // plusMonths counts from the anchor and clamps to the last day of a short month.
            LocalDate due = firstDueDate.plusMonths(number);
            schedule[number] = new String[] {due.toString(), BigDecimal.valueOf(amount, 2).toPlainString()};
        }
        return schedule;
    }
}
