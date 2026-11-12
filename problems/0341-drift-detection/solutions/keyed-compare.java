import java.util.*;

/**
 * The recorded state maps an address to an id and attributes, and a scan maps an id to a type and
 * attributes. Drift is found by looking each recorded id up in the scan, comparing values after the
 * type's normalization rules, and filtering the rows through the ignore rules. Import adds a
 * recorded entry, the plan compares the desired state with the recorded one, and a reconcile turns
 * each drift row into the action of the newest policy that matches.
 */
public class DriftDetector {
    private record Entry(String tag, Map<String, String> attributes) {}

    private record DriftRow(List<String> row, String address) {}

    private final Map<String, Entry> recorded = new HashMap<>();
    private final Map<String, Entry> observed = new HashMap<>();
    private final Set<List<String>> ignores = new LinkedHashSet<>();
    private final Set<String> lists = new HashSet<>();
    private final Map<String, String> defaults = new HashMap<>();
    private final Map<String, Map<String, String>> desired = new HashMap<>();
    private final LinkedHashMap<String, String> policies = new LinkedHashMap<>();

    public DriftDetector() {}

    // Level 1
    public boolean record(String address, String resourceId, List<List<String>> attributes) {
        return recorded.put(address, new Entry(resourceId, toMap(attributes))) == null;
    }

    public boolean observe(String resourceId, String resourceType, List<List<String>> attributes) {
        return observed.put(resourceId, new Entry(resourceType, toMap(attributes))) == null;
    }

    public List<List<String>> drift() {
        List<List<String>> rows = new ArrayList<>();
        for (DriftRow found : driftRows()) {
            rows.add(found.row());
        }
        return rows;
    }

    // Level 2
    public boolean ignore(String pattern, String key) {
        return ignores.add(List.of(pattern, key));
    }

    public boolean unordered(String resourceType, String key) {
        return lists.add(resourceType + "." + key);
    }

    public boolean defaultValue(String resourceType, String key, String value) {
        return defaults.put(resourceType + "." + key, value) == null;
    }

    // Level 3
    public String importResource(String address, String resourceId) {
        Entry found = observed.get(resourceId);
        if (found == null) {
            return "not-found";
        }
        if (!kindOf(address).equals(found.tag())) {
            return "type-mismatch";
        }
        for (Entry entry : recorded.values()) {
            if (entry.tag().equals(resourceId)) {
                return "already-managed";
            }
        }
        if (recorded.containsKey(address)) {
            return "address-taken";
        }
        recorded.put(address, new Entry(resourceId, new HashMap<>(found.attributes())));
        return "imported";
    }

    public boolean desire(String address, List<List<String>> attributes) {
        return desired.put(address, toMap(attributes)) == null;
    }

    public List<List<String>> plan() {
        TreeSet<String> addresses = new TreeSet<>(desired.keySet());
        addresses.addAll(recorded.keySet());
        List<List<String>> rows = new ArrayList<>();
        for (String address : addresses) {
            Entry entry = recorded.get(address);
            Map<String, String> wanted = desired.get(address);
            if (entry == null) {
                rows.add(List.of("create", address));
            } else if (wanted == null) {
                rows.add(List.of("delete", address));
            } else {
                for (String key : differing(kindOf(address), entry.attributes(), wanted)) {
                    rows.add(List.of("update", address, key,
                            entry.attributes().getOrDefault(key, ""), wanted.getOrDefault(key, "")));
                }
            }
        }
        return rows;
    }

    // Level 4
    public boolean policy(String pattern, String mode) {
        boolean isNew = policies.remove(pattern) == null;
        policies.put(pattern, mode);
        return isNew;
    }

    public List<List<String>> reconcile() {
        List<List<String>> rows = new ArrayList<>();
        for (DriftRow found : driftRows()) {
            List<String> row = found.row();
            String address = found.address();
            if (row.get(0).equals("unmanaged")) {
                rows.add(List.of("alert-unmanaged", row.get(1), row.get(2)));
                continue;
            }
            String mode = mode(address);
            if (row.get(0).equals("deleted")) {
                switch (mode) {
                    case "revert" -> rows.add(List.of("recreate", address));
                    case "accept" -> rows.add(List.of("forget", address));
                    default -> rows.add(List.of("alert-deleted", address, row.get(2)));
                }
                continue;
            }
            String key = row.get(2);
            String recordedValue = row.get(3);
            String scanned = row.get(4);
            if (mode.equals("alert")) {
                rows.add(List.of("alert", address, key, recordedValue, scanned));
                continue;
            }
            String wanted = desired.get(address).getOrDefault(key, "");
            if (same(kindOf(address), key, emptyToNull(scanned), emptyToNull(wanted))) {
                continue;
            }
            rows.add(mode.equals("revert")
                    ? List.of("revert", address, key, scanned, wanted)
                    : List.of("accept", address, key, wanted, scanned));
        }
        return rows;
    }

    // Comparing
    private static Map<String, String> toMap(List<List<String>> attributes) {
        Map<String, String> map = new HashMap<>();
        for (List<String> pair : attributes) {
            map.put(pair.get(0), pair.get(1));
        }
        return map;
    }

    private static String kindOf(String address) {
        return address.substring(0, address.indexOf('.'));
    }

    private static String emptyToNull(String value) {
        return value.isEmpty() ? null : value;
    }

    /** Whether {@code text} matches {@code pattern}, where {@code *} stands for any run of characters. */
    static boolean glob(String pattern, String text) {
        int p = 0;
        int t = 0;
        int star = -1;
        int mark = 0;
        while (t < text.length()) {
            if (p < pattern.length() && pattern.charAt(p) != '*' && pattern.charAt(p) == text.charAt(t)) {
                p++;
                t++;
            } else if (p < pattern.length() && pattern.charAt(p) == '*') {
                star = p;
                mark = t;
                p++;
            } else if (star >= 0) {
                mark++;
                p = star + 1;
                t = mark;
            } else {
                return false;
            }
        }
        while (p < pattern.length() && pattern.charAt(p) == '*') {
            p++;
        }
        return p == pattern.length();
    }

    private boolean same(String resourceType, String key, String first, String second) {
        String id = resourceType + "." + key;
        String fallback = defaults.get(id);
        String a = first == null ? fallback : first;
        String b = second == null ? fallback : second;
        if (a == null || b == null) {
            return a == b;
        }
        if (lists.contains(id)) {
            List<String> left = new ArrayList<>(Arrays.asList(a.split(",", -1)));
            List<String> right = new ArrayList<>(Arrays.asList(b.split(",", -1)));
            Collections.sort(left);
            Collections.sort(right);
            return left.equals(right);
        }
        return a.equals(b);
    }

    private List<String> differing(String resourceType, Map<String, String> first, Map<String, String> second) {
        TreeSet<String> keys = new TreeSet<>(first.keySet());
        keys.addAll(second.keySet());
        List<String> found = new ArrayList<>();
        for (String key : keys) {
            if (!same(resourceType, key, first.get(key), second.get(key))) {
                found.add(key);
            }
        }
        return found;
    }

    private boolean ignored(String text, String key) {
        for (List<String> rule : ignores) {
            if (rule.get(1).equals(key) && glob(rule.get(0), text)) {
                return true;
            }
        }
        return false;
    }

    private String mode(String address) {
        String mode = "alert";
        for (Map.Entry<String, String> rule : policies.entrySet()) {
            if (glob(rule.getKey(), address)) {
                mode = rule.getValue();
            }
        }
        return mode;
    }

    private List<DriftRow> driftRows() {
        List<DriftRow> rows = new ArrayList<>();
        Set<String> managed = new HashSet<>();
        for (String address : new TreeSet<>(recorded.keySet())) {
            Entry entry = recorded.get(address);
            managed.add(entry.tag());
            if (ignored(address, "*")) {
                continue;
            }
            Entry found = observed.get(entry.tag());
            if (found == null) {
                rows.add(new DriftRow(List.of("deleted", address, entry.tag()), address));
                continue;
            }
            for (String key : differing(kindOf(address), entry.attributes(), found.attributes())) {
                if (!ignored(address, key)) {
                    rows.add(new DriftRow(List.of("changed", address, key,
                            entry.attributes().getOrDefault(key, ""),
                            found.attributes().getOrDefault(key, "")), address));
                }
            }
        }
        for (String resourceId : new TreeSet<>(observed.keySet())) {
            String resourceType = observed.get(resourceId).tag();
            if (!managed.contains(resourceId) && !ignored(resourceType + "." + resourceId, "*")) {
                rows.add(new DriftRow(List.of("unmanaged", resourceId, resourceType), ""));
            }
        }
        return rows;
    }
}
