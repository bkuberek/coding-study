import java.time.LocalDate;
import java.util.*;

public class Solution {
    public LocalDate[][] coverageGaps(LocalDate[][] periods, LocalDate windowStart, LocalDate windowEnd) {
        LocalDate[][] sorted = periods.clone();
        Arrays.sort(sorted, (a, b) -> a[0].compareTo(b[0]));
        List<LocalDate[]> gaps = new ArrayList<>();
        LocalDate cursor = windowStart; // every day of the window before cursor is covered or already reported
        for (LocalDate[] period : sorted) {
            if (!cursor.isBefore(windowEnd)) {
                break;
            }
            if (period[0].isAfter(cursor)) {
                LocalDate gapEnd = period[0].isBefore(windowEnd) ? period[0] : windowEnd;
                gaps.add(new LocalDate[] {cursor, gapEnd});
            }
            if (period[1].isAfter(cursor)) {
                cursor = period[1];
            }
        }
        if (cursor.isBefore(windowEnd)) {
            gaps.add(new LocalDate[] {cursor, windowEnd});
        }
        return gaps.toArray(new LocalDate[0][]);
    }
}
