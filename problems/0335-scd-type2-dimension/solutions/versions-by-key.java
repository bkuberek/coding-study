import java.util.*;

/**
 * Every business key keeps its versions in a list sorted by validFrom, and the versions never
 * overlap, so the version valid at a date is one binary search away. Untracked attributes hold one
 * value per business key, copied into every version, and the date of the latest load that carried
 * the key decides whether a row may still overwrite them.
 */
public class DimensionTable {
    private static final int OPEN_END = 99991231;
    private static final int UNKNOWN_MEMBER = 0;

    private static final class Version {
        final int key;
        final String businessKey;
        final List<String> values;
        final int validFrom;
        int validTo;

        Version(int key, String businessKey, List<String> values, int validFrom, int validTo) {
            this.key = key;
            this.businessKey = businessKey;
            this.values = values;
            this.validFrom = validFrom;
            this.validTo = validTo;
        }

        List<String> row() {
            List<String> row = new ArrayList<>();
            row.add(String.valueOf(key));
            row.add(businessKey);
            row.addAll(values);
            row.add(String.valueOf(validFrom));
            row.add(String.valueOf(validTo));
            row.add(validTo == OPEN_END ? "Y" : "N");
            return row;
        }
    }

    private final int width;
    private final Map<String, Integer> position = new HashMap<>();
    private final List<Integer> tracked = new ArrayList<>();
    private final Map<Integer, Version> bySurrogate = new HashMap<>();
    private final TreeMap<String, List<Version>> versions = new TreeMap<>();
    private final Map<String, Integer> lastLoad = new HashMap<>();
    private int nextKey = 1;
    private Set<String> present = new HashSet<>();

    public DimensionTable(List<String> attributes) {
        width = attributes.size();
        for (int index = 0; index < attributes.size(); index++) {
            position.put(attributes.get(index), index);
        }
    }

    // Level 1
    public List<Integer> load(List<List<String>> rows, int loadDate) {
        return apply(rows, loadDate);
    }

    public int lookup(String businessKey) {
        List<Version> list = versions.get(businessKey);
        if (list == null || list.get(list.size() - 1).validTo != OPEN_END) {
            return -1;
        }
        return list.get(list.size() - 1).key;
    }

    public List<String> rowOf(int surrogateKey) {
        Version version = bySurrogate.get(surrogateKey);
        return version == null ? new ArrayList<>() : version.row();
    }

    public int size() {
        return bySurrogate.size();
    }

    // Level 2
    public boolean trackHistory(String attribute) {
        Integer index = position.get(attribute);
        if (index == null || tracked.contains(index)) {
            return false;
        }
        tracked.add(index);
        return true;
    }

    public List<List<String>> history(String businessKey) {
        List<List<String>> rows = new ArrayList<>();
        for (Version version : versions.getOrDefault(businessKey, List.of())) {
            rows.add(version.row());
        }
        return rows;
    }

    // Level 3
    public int lookupAt(String businessKey, int asOf) {
        Version version = validAt(businessKey, asOf);
        return version == null ? -1 : version.key;
    }

    public List<List<String>> snapshotAt(int asOf) {
        List<List<String>> rows = new ArrayList<>();
        for (String businessKey : versions.keySet()) {
            Version version = validAt(businessKey, asOf);
            if (version != null) {
                rows.add(version.row());
            }
        }
        return rows;
    }

    public List<List<String>> resolveFacts(List<List<String>> facts) {
        List<List<String>> resolved = new ArrayList<>();
        for (List<String> fact : facts) {
            String factId = fact.get(0);
            String businessKey = fact.get(1);
            if (!versions.containsKey(businessKey)) {
                resolved.add(List.of(factId, String.valueOf(UNKNOWN_MEMBER), "unknown-key"));
                continue;
            }
            Version version = validAt(businessKey, Integer.parseInt(fact.get(2)));
            if (version == null) {
                resolved.add(List.of(factId, String.valueOf(UNKNOWN_MEMBER), "no-version"));
            } else {
                String status = version.validTo == OPEN_END ? "current" : "late";
                resolved.add(List.of(factId, String.valueOf(version.key), status));
            }
        }
        return resolved;
    }

    // Level 4
    public List<Integer> loadFull(List<List<String>> rows, int loadDate) {
        List<Integer> counts = apply(rows, loadDate);
        int closed = 0;
        for (Map.Entry<String, List<Version>> entry : versions.entrySet()) {
            List<Version> list = entry.getValue();
            Version last = list.get(list.size() - 1);
            if (!present.contains(entry.getKey()) && last.validTo == OPEN_END) {
                last.validTo = loadDate;
                closed++;
            }
        }
        counts.add(closed);
        return counts;
    }

    public List<List<String>> fullHistory() {
        List<List<String>> rows = new ArrayList<>();
        for (List<Version> list : versions.values()) {
            for (Version version : list) {
                rows.add(version.row());
            }
        }
        return rows;
    }

    // Helpers
    private List<Integer> apply(List<List<String>> rows, int loadDate) {
        TreeMap<String, List<String>> latest = new TreeMap<>();
        for (List<String> row : rows) {
            latest.put(row.get(0), row.subList(1, row.size()));
        }
        present = new HashSet<>(latest.keySet());
        int inserted = 0;
        int changed = 0;
        int unchanged = 0;
        for (Map.Entry<String, List<String>> entry : latest.entrySet()) {
            String businessKey = entry.getKey();
            if (!versions.containsKey(businessKey)) {
                versions.put(businessKey, new ArrayList<>());
                lastLoad.put(businessKey, loadDate);
                insert(businessKey, new ArrayList<>(entry.getValue()), loadDate, OPEN_END);
                inserted++;
            } else if (merge(businessKey, entry.getValue(), loadDate)) {
                changed++;
            } else {
                unchanged++;
            }
        }
        return new ArrayList<>(List.of(inserted, changed, unchanged));
    }

    private boolean merge(String businessKey, List<String> values, int loadDate) {
        List<Version> list = versions.get(businessKey);
        boolean changed = false;
        if (loadDate >= lastLoad.get(businessKey)) {
            lastLoad.put(businessKey, loadDate);
            for (int index = 0; index < width; index++) {
                if (!tracked.contains(index) && !list.get(0).values.get(index).equals(values.get(index))) {
                    for (Version version : list) {
                        version.values.set(index, values.get(index));
                    }
                    changed = true;
                }
            }
        }
        Version holder = validAt(businessKey, loadDate);
        if (holder != null) {
            boolean same = true;
            for (int index : tracked) {
                same &= holder.values.get(index).equals(values.get(index));
            }
            if (same) {
                return changed;
            }
            if (holder.validFrom == loadDate) {
                for (int index : tracked) {
                    holder.values.set(index, values.get(index));
                }
                return true;
            }
            int end = holder.validTo;
            holder.validTo = loadDate;
            insert(businessKey, combine(list.get(0), values), loadDate, end);
            return true;
        }
        int end = OPEN_END;
        for (Version version : list) {
            if (version.validFrom > loadDate) {
                end = version.validFrom;
                break;
            }
        }
        insert(businessKey, combine(list.get(0), values), loadDate, end);
        return true;
    }

    /** The incoming tracked values with the key's untracked values. */
    private List<String> combine(Version shared, List<String> values) {
        List<String> combined = new ArrayList<>(shared.values);
        for (int index : tracked) {
            combined.set(index, values.get(index));
        }
        return combined;
    }

    private void insert(String businessKey, List<String> values, int validFrom, int validTo) {
        Version version = new Version(nextKey++, businessKey, values, validFrom, validTo);
        bySurrogate.put(version.key, version);
        List<Version> list = versions.get(businessKey);
        list.add(startsAtOrBefore(list, validFrom), version);
    }

    /** The number of versions whose validFrom is at or before the date. */
    private static int startsAtOrBefore(List<Version> list, int date) {
        int low = 0;
        int high = list.size();
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (list.get(middle).validFrom <= date) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low;
    }

    private Version validAt(String businessKey, int asOf) {
        List<Version> list = versions.get(businessKey);
        if (list == null) {
            return null;
        }
        int at = startsAtOrBefore(list, asOf) - 1;
        if (at < 0 || asOf >= list.get(at).validTo) {
            return null;
        }
        return list.get(at);
    }
}
