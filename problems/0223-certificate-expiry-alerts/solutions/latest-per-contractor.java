import java.time.LocalDate;
import java.util.*;

public class Solution {
    public String[][] certificateAlerts(String[] contractorIds, LocalDate[] expiryDates, LocalDate asOfDate, int windowDays) {
        Map<String, LocalDate> latest = new HashMap<>(); // a renewal supersedes: only the latest expiry counts
        for (int i = 0; i < contractorIds.length; i++) {
            latest.merge(contractorIds[i], expiryDates[i], (a, b) -> a.isAfter(b) ? a : b);
        }
        LocalDate horizon = asOfDate.plusDays(windowDays);
        List<Map.Entry<String, LocalDate>> flagged = new ArrayList<>();
        for (Map.Entry<String, LocalDate> entry : latest.entrySet()) {
            if (!entry.getValue().isAfter(horizon)) {
                flagged.add(entry);
            }
        }
        flagged.sort(Map.Entry.<String, LocalDate>comparingByValue().thenComparing(Map.Entry.comparingByKey()));
        String[][] rows = new String[flagged.size()][];
        for (int i = 0; i < rows.length; i++) {
            Map.Entry<String, LocalDate> entry = flagged.get(i);
            String status = entry.getValue().isAfter(asOfDate) ? "expiring" : "expired";
            rows[i] = new String[] {entry.getKey(), entry.getValue().toString(), status};
        }
        return rows;
    }
}
