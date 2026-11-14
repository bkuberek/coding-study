import java.time.LocalDate;
import java.util.*;
import java.util.function.Function;

public class RecordHistory {
    private static final class FieldHistory {
        private final List<Long> writeTimes = new ArrayList<>(); // every write, in timestamp order
        private final List<LocalDate> writeDates = new ArrayList<>();
        private final List<String> writeValues = new ArrayList<>();
        private final TreeMap<LocalDate, String> view = new TreeMap<>(); // current view: one value per date

        void write(long timestamp, LocalDate effectiveDate, String value) {
            writeTimes.add(timestamp);
            writeDates.add(effectiveDate);
            writeValues.add(value);
            view.put(effectiveDate, value); // a correction replaces the value for that date
        }

        String current(LocalDate onDate) {
            Map.Entry<LocalDate, String> entry = view.floorEntry(onDate);
            return entry == null ? "" : entry.getValue();
        }

        String asKnown(LocalDate onDate, long knownAt) {
            int known = countKnown(knownAt);
            LocalDate bestDate = null;
            String bestValue = "";
            for (int i = 0; i < known; i++) {
                LocalDate effectiveDate = writeDates.get(i);
                // not-before lets a later write for the same date replace an earlier one
                if (!effectiveDate.isAfter(onDate) && (bestDate == null || !effectiveDate.isBefore(bestDate))) {
                    bestDate = effectiveDate;
                    bestValue = writeValues.get(i);
                }
            }
            return bestValue;
        }

        // Number of writes made at or before knownAt (timestamps are sorted and distinct).
        private int countKnown(long knownAt) {
            int low = 0;
            int high = writeTimes.size();
            while (low < high) {
                int middle = (low + high) >>> 1;
                if (writeTimes.get(middle) <= knownAt) {
                    low = middle + 1;
                } else {
                    high = middle;
                }
            }
            return low;
        }
    }

    private final Map<String, TreeMap<String, FieldHistory>> records = new HashMap<>();

    public RecordHistory() {
    }

    public void setValue(long timestamp, String recordId, String field, LocalDate effectiveDate, String value) {
        records.computeIfAbsent(recordId, id -> new TreeMap<>())
                .computeIfAbsent(field, name -> new FieldHistory())
                .write(timestamp, effectiveDate, value);
    }

    public String getValue(long timestamp, String recordId, String field, LocalDate onDate) {
        FieldHistory history = history(recordId, field);
        return history == null ? "" : history.current(onDate);
    }

    public List<String> snapshot(long timestamp, String recordId, LocalDate onDate) {
        return snapshotWith(recordId, history -> history.current(onDate));
    }

    public String getValueAsKnown(long timestamp, String recordId, String field, LocalDate onDate, long knownAt) {
        FieldHistory history = history(recordId, field);
        return history == null ? "" : history.asKnown(onDate, knownAt);
    }

    public List<String> snapshotAsKnown(long timestamp, String recordId, LocalDate onDate, long knownAt) {
        return snapshotWith(recordId, history -> history.asKnown(onDate, knownAt));
    }

    private FieldHistory history(String recordId, String field) {
        TreeMap<String, FieldHistory> fields = records.get(recordId);
        return fields == null ? null : fields.get(field);
    }

    private List<String> snapshotWith(String recordId, Function<FieldHistory, String> read) {
        List<String> entries = new ArrayList<>();
        // The TreeMap iterates the field names in sorted order.
        for (Map.Entry<String, FieldHistory> field : records.getOrDefault(recordId, new TreeMap<>()).entrySet()) {
            String value = read.apply(field.getValue());
            if (!value.isEmpty()) {
                entries.add(field.getKey() + "=" + value);
            }
        }
        return entries;
    }
}
