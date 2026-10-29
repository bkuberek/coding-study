import java.math.BigDecimal;
import java.time.DateTimeException;
import java.time.LocalDate;
import java.util.*;
import java.util.regex.Pattern;

public class Solution {
    private static final String[] FIELDS = {"contractorId", "classCode", "payroll", "periodStart"};
    // [0-9], written out: the digits are ASCII only.
    private static final Pattern CONTRACTOR_ID = Pattern.compile("[a-z0-9-]{1,20}");
    private static final Pattern CLASS_CODE = Pattern.compile("[0-9]{4}");
    private static final Pattern PAYROLL = Pattern.compile("[0-9]+(\\.[0-9]{1,2})?");
    private static final Pattern ISO_DAY = Pattern.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}");
    private static final BigDecimal MAX_PAYROLL = BigDecimal.valueOf(1_000_000_000L);
    private static final LocalDate FIRST_DAY = LocalDate.of(2000, 1, 1);
    private static final LocalDate LAST_DAY = LocalDate.of(2099, 12, 31);

    public List<String> validateRows(String[][] rows) {
        List<String> errors = new ArrayList<>();
        Set<List<String>> seenKeys = new HashSet<>();
        for (int index = 0; index < rows.length; index++) {
            String[] row = rows[index];
            if (row.length != FIELDS.length) {
                errors.add(index + ":row:column-count");
                continue;
            }
            String[] reasons = {
                checkPattern(row[0], CONTRACTOR_ID),
                checkPattern(row[1], CLASS_CODE),
                checkPayroll(row[2]),
                checkPeriodStart(row[3]),
            };
            for (int column = 0; column < FIELDS.length; column++) {
                if (!reasons[column].isEmpty()) {
                    errors.add(index + ":" + FIELDS[column] + ":" + reasons[column]);
                }
            }
            if (reasons[0].isEmpty() && reasons[1].isEmpty() && reasons[3].isEmpty()) {
                // add() returns false when the key was already there.
                if (!seenKeys.add(List.of(row[0], row[1], row[3]))) {
                    errors.add(index + ":row:duplicate");
                }
            }
        }
        return errors;
    }

    private static String checkPattern(String value, Pattern pattern) {
        if (value.isEmpty()) {
            return "missing";
        }
        return pattern.matcher(value).matches() ? "" : "invalid";
    }

    private static String checkPayroll(String value) {
        String reason = checkPattern(value, PAYROLL);
        if (!reason.isEmpty()) {
            return reason;
        }
        BigDecimal amount = new BigDecimal(value);
        return amount.signum() > 0 && amount.compareTo(MAX_PAYROLL) <= 0 ? "" : "out-of-range";
    }

    private static String checkPeriodStart(String value) {
        String reason = checkPattern(value, ISO_DAY);
        if (!reason.isEmpty()) {
            return reason;
        }
        LocalDate day;
        try {
            day = LocalDate.parse(value); // strict: 2026-02-30 throws instead of rolling over
        } catch (DateTimeException e) {
            return "invalid";
        }
        if (day.getYear() < 1) {
            return "invalid"; // LocalDate accepts year 0, but real days start in year 1
        }
        return day.isBefore(FIRST_DAY) || day.isAfter(LAST_DAY) ? "out-of-range" : "";
    }
}
