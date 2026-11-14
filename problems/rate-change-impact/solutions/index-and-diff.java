import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

public class Solution {
    private record Change(String code, BigDecimal percent) {}

    public String[][] rateChangeImpact(String[] oldCodes, BigDecimal[] oldRates, String[] newCodes, BigDecimal[] newRates) {
        Map<String, BigDecimal> old = new HashMap<>();
        for (int i = 0; i < oldCodes.length; i++) {
            old.put(oldCodes[i], oldRates[i]);
        }
        Map<String, BigDecimal> current = new HashMap<>();
        for (int i = 0; i < newCodes.length; i++) {
            current.put(newCodes[i], newRates[i]);
        }

        List<Change> changed = new ArrayList<>();
        List<String> added = new ArrayList<>();
        for (Map.Entry<String, BigDecimal> entry : current.entrySet()) {
            BigDecimal before = old.get(entry.getKey());
            if (before == null) {
                added.add(entry.getKey());
            } else if (entry.getValue().compareTo(before) != 0) { // equals() is scale-sensitive: 12.50 != 12.5
                BigDecimal percent = entry.getValue()
                        .subtract(before)
                        .multiply(BigDecimal.valueOf(100))
                        .divide(before, 2, RoundingMode.HALF_UP);
                changed.add(new Change(entry.getKey(), percent));
            }
        }
        List<String> removed = new ArrayList<>();
        for (String code : old.keySet()) {
            if (!current.containsKey(code)) {
                removed.add(code);
            }
        }

        // Numeric order of the rounded percent, largest first; ties by code.
        // Chain thenComparing onto the descending comparator; reversed() on the chain would flip the tie-break too.
        changed.sort(Comparator.<Change, BigDecimal>comparing(Change::percent, Comparator.reverseOrder()).thenComparing(Change::code));
        Collections.sort(added);
        Collections.sort(removed);

        List<String[]> rows = new ArrayList<>();
        for (Change change : changed) {
            rows.add(new String[] {change.code(), "changed", change.percent().toPlainString()});
        }
        for (String code : added) {
            rows.add(new String[] {code, "added", ""});
        }
        for (String code : removed) {
            rows.add(new String[] {code, "removed", ""});
        }
        return rows.toArray(new String[0][]);
    }
}
