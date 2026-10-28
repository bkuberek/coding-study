import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.*;

public class RateTable {
    private record Version(int id, Map<String, BigDecimal> rates) {}

    private static final BigDecimal NOT_FOUND = BigDecimal.ONE.negate();

    // Parallel lists sorted by effective date; equal dates stay in publish order.
    private final List<LocalDate> dates = new ArrayList<>();
    private final List<Version> versions = new ArrayList<>();
    private int published = 0;

    public RateTable() {
    }

    public void publish(LocalDate effectiveDate, String[] classCodes, BigDecimal[] rates) {
        published++;
        int slot = versionsOnOrBefore(effectiveDate);
        // A fresh map, so a published version never changes afterwards.
        Map<String, BigDecimal> table = new HashMap<>();
        for (int i = 0; i < classCodes.length; i++) {
            table.put(classCodes[i], rates[i]);
        }
        dates.add(slot, effectiveDate);
        versions.add(slot, new Version(published, table));
    }

    public BigDecimal rateAsOf(LocalDate onDate, String classCode) {
        int slot = versionsOnOrBefore(onDate);
        if (slot == 0) {
            return NOT_FOUND;
        }
        return versions.get(slot - 1).rates().getOrDefault(classCode, NOT_FOUND);
    }

    public int versionAsOf(LocalDate onDate) {
        int slot = versionsOnOrBefore(onDate);
        return slot > 0 ? versions.get(slot - 1).id() : -1;
    }

    // Number of versions effective on or before the day (upper bound). Collections.binarySearch
    // may return any of several equal dates, so the search is written out.
    private int versionsOnOrBefore(LocalDate day) {
        int low = 0;
        int high = dates.size();
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (dates.get(middle).compareTo(day) <= 0) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low;
    }
}
