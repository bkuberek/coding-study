import java.util.*;

/**
 * A map from key to row holds the table. A second map holds each key's version, the position at
 * which its last change became visible, and keeps it when the row is deleted: that tombstone is
 * what stops an old insert from bringing a deleted row back.
 *
 * <p>A change is skipped when its position is not after the key's version, or not after the
 * snapshot the table started from. A transaction's changes wait in a buffer until its commit,
 * then run into an overlay, a small map of the rows they change, which is written into the table
 * only when every change worked.
 */
public class ReplicaTable {
    private static final String OK = "ok";
    private static final String SKIPPED = "skipped";
    private static final int NEVER = -1;

    private record Change(String op, List<String> row) {}

    private final List<String> names;
    private Map<String, List<String>> table = new HashMap<>();
    private Map<String, Integer> versions = new HashMap<>();
    private int floor = 0;
    private int schemaVersion = 0;
    private final Map<String, List<Change>> staged = new HashMap<>();

    public ReplicaTable(List<String> columns) {
        this.names = new ArrayList<>(columns);
    }

    // Level 1
    public String apply(String op, List<String> row) {
        String code = check(table.containsKey(row.get(0)), op, row);
        if (code.equals(OK)) {
            if (op.equals("delete")) {
                table.remove(row.get(0));
            } else {
                table.put(row.get(0), new ArrayList<>(row));
            }
        }
        return code;
    }

    public List<List<String>> rows() {
        List<String> keys = new ArrayList<>(table.keySet());
        Collections.sort(keys);
        List<List<String>> result = new ArrayList<>();
        for (String key : keys) {
            result.add(new ArrayList<>(table.get(key)));
        }
        return result;
    }

    // Level 2
    public String applyAt(int lsn, String op, List<String> row) {
        String key = row.get(0);
        if (lsn <= floor || lsn <= version(key)) {
            return SKIPPED;
        }
        String code = apply(op, row);
        if (code.equals(OK)) {
            versions.put(key, lsn);
        }
        return code;
    }

    public int version(String key) {
        return versions.getOrDefault(key, NEVER);
    }

    // Level 3
    public void loadSnapshot(int lsn, List<List<String>> snapshot) {
        table = new HashMap<>();
        versions = new HashMap<>();
        for (List<String> row : snapshot) {
            table.put(row.get(0), new ArrayList<>(row));
            versions.put(row.get(0), lsn);
        }
        floor = lsn;
    }

    public void stage(String tx, String op, List<String> row) {
        staged.computeIfAbsent(tx, t -> new ArrayList<>()).add(new Change(op, new ArrayList<>(row)));
    }

    public String commit(int lsn, String tx) {
        List<Change> changes = staged.remove(tx);
        if (changes == null) {
            changes = List.of();
        }
        if (lsn <= floor) {
            return SKIPPED;
        }
        // A key mapped to null was deleted by this transaction.
        Map<String, List<String>> overlay = new LinkedHashMap<>();
        for (Change change : changes) {
            String key = change.row().get(0);
            if (lsn <= version(key)) {
                continue;
            }
            boolean present = overlay.containsKey(key) ? overlay.get(key) != null : table.containsKey(key);
            String code = check(present, change.op(), change.row());
            if (!code.equals(OK)) {
                return code;
            }
            overlay.put(key, change.op().equals("delete") ? null : change.row());
        }
        if (overlay.isEmpty()) {
            return SKIPPED;
        }
        for (Map.Entry<String, List<String>> entry : overlay.entrySet()) {
            if (entry.getValue() == null) {
                table.remove(entry.getKey());
            } else {
                table.put(entry.getKey(), entry.getValue());
            }
            versions.put(entry.getKey(), lsn);
        }
        return OK;
    }

    public void rollback(String tx) {
        staged.remove(tx);
    }

    // Level 4
    public String alterAt(int lsn, List<String> change) {
        if (lsn <= floor || lsn <= schemaVersion) {
            return SKIPPED;
        }
        String code = alter(change);
        if (code.equals(OK)) {
            schemaVersion = lsn;
        }
        return code;
    }

    public List<String> columns() {
        return new ArrayList<>(names);
    }

    public List<List<String>> compare(List<String> sourceColumns, List<List<String>> sourceRows) {
        List<List<String>> report = new ArrayList<>();
        TreeSet<String> allNames = new TreeSet<>(names);
        allNames.addAll(sourceColumns);
        for (String name : allNames) {
            if (!names.contains(name)) {
                report.add(List.of("missing-column", name));
            } else if (!sourceColumns.contains(name)) {
                report.add(List.of("extra-column", name));
            }
        }
        TreeSet<String> common = new TreeSet<>(names);
        common.retainAll(sourceColumns);
        Map<String, List<String>> source = new HashMap<>();
        for (List<String> row : sourceRows) {
            source.put(row.get(0), row);
        }
        TreeSet<String> keys = new TreeSet<>(table.keySet());
        keys.addAll(source.keySet());
        for (String key : keys) {
            List<String> here = table.get(key);
            List<String> there = source.get(key);
            if (here == null) {
                report.add(List.of("missing-row", key));
            } else if (there == null) {
                report.add(List.of("extra-row", key));
            } else {
                for (String name : common) {
                    String a = here.get(names.indexOf(name));
                    String b = there.get(sourceColumns.indexOf(name));
                    if (!a.equals(b)) {
                        report.add(List.of("value-differs", key, name, a, b));
                    }
                }
            }
        }
        return report;
    }

    // Changes
    private String check(boolean present, String op, List<String> row) {
        if (!op.equals("delete") && row.size() != names.size()) {
            return "column-count";
        }
        if (op.equals("insert")) {
            return present ? "duplicate-key" : OK;
        }
        return present ? OK : "unknown-key";
    }

    private String alter(List<String> change) {
        String kind = change.get(0);
        String name = change.get(1);
        if (kind.equals("add")) {
            if (names.contains(name)) {
                return "duplicate-column";
            }
            names.add(name);
            for (List<String> row : table.values()) {
                row.add(change.get(2));
            }
            return OK;
        }
        int index = names.indexOf(name);
        if (index < 0) {
            return "unknown-column";
        }
        if (kind.equals("drop")) {
            if (index == 0) {
                return "key-column";
            }
            names.remove(index);
            for (List<String> row : table.values()) {
                row.remove(index);
            }
            return OK;
        }
        if (names.contains(change.get(2))) {
            return "duplicate-column";
        }
        names.set(index, change.get(2));
        return OK;
    }
}
