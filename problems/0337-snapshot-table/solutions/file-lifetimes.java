import java.util.*;

/**
 * Snapshots are numbered 1, 2, 3 in commit order, and history is a single line, so a data file is
 * live in one interval of snapshots: from the one that added it up to, not including, the one that
 * removed it. Each file keeps that interval, each snapshot keeps the files it added and removed,
 * and every question is a filter over the files or a walk over the snapshots.
 */
public class SnapshotTable {
    private static final int NEVER = Integer.MAX_VALUE;

    private static final class DataFile {
        final String path;
        final String partition;
        final String rows;
        final int added;
        int removed = NEVER;

        DataFile(String path, String partition, String rows, int added) {
            this.path = path;
            this.partition = partition;
            this.rows = rows;
            this.added = added;
        }

        boolean liveAt(int snapshot) {
            return added <= snapshot && snapshot < removed;
        }
    }

    private static final class Snapshot {
        final int id;
        final int parent;
        final long timestamp;
        final String operation;
        final List<DataFile> added = new ArrayList<>();
        final List<DataFile> removed = new ArrayList<>();

        Snapshot(int id, int parent, long timestamp, String operation) {
            this.id = id;
            this.parent = parent;
            this.timestamp = timestamp;
            this.operation = operation;
        }
    }

    private final Map<String, DataFile> files = new HashMap<>();
    private final List<Snapshot> snapshots = new ArrayList<>();
    private int firstRetained = 1;

    public SnapshotTable() {
    }

    // Level 1
    public int append(List<List<String>> files, long timestamp) {
        if (files.isEmpty() || !fresh(files)) {
            return -1;
        }
        return commitChange(files, List.of(), timestamp, null);
    }

    public int currentSnapshot() {
        return snapshots.size();
    }

    public List<String> scan() {
        return scanAt(currentSnapshot());
    }

    public List<List<String>> manifest(int snapshotId) {
        List<List<String>> entries = new ArrayList<>();
        if (!retained(snapshotId)) {
            return entries;
        }
        for (DataFile file : files.values()) {
            String status;
            if (file.liveAt(snapshotId)) {
                status = file.added == snapshotId ? "added" : "existing";
            } else if (file.removed == snapshotId) {
                status = "deleted";
            } else {
                continue;
            }
            entries.add(List.of(file.path, file.partition, file.rows, status));
        }
        entries.sort(Comparator.comparing(entry -> entry.get(0)));
        return entries;
    }

    // Level 2
    public int deleteFiles(List<String> paths, long timestamp) {
        if (paths.isEmpty() || !removable(paths, currentSnapshot())) {
            return -1;
        }
        return commitChange(List.of(), paths, timestamp, null);
    }

    public int overwrite(String partition, List<List<String>> files, long timestamp) {
        for (List<String> file : files) {
            if (!file.get(1).equals(partition)) {
                return -1;
            }
        }
        if (!fresh(files)) {
            return -1;
        }
        int current = currentSnapshot();
        List<String> old = new ArrayList<>();
        for (DataFile file : this.files.values()) {
            if (file.partition.equals(partition) && file.liveAt(current)) {
                old.add(file.path);
            }
        }
        if (old.isEmpty() && files.isEmpty()) {
            return -1;
        }
        return commitChange(files, old, timestamp, null);
    }

    public List<String> scanAt(int snapshotId) {
        List<String> paths = new ArrayList<>();
        if (!retained(snapshotId)) {
            return paths;
        }
        for (DataFile file : files.values()) {
            if (file.liveAt(snapshotId)) {
                paths.add(file.path);
            }
        }
        Collections.sort(paths);
        return paths;
    }

    public int snapshotAsOf(long timestamp) {
        int found = 0;
        for (Snapshot snapshot : snapshots) {
            if (snapshot.timestamp <= timestamp) {
                found = snapshot.id;
            }
        }
        return found >= firstRetained ? found : 0;
    }

    public List<List<String>> history() {
        List<List<String>> entries = new ArrayList<>();
        for (Snapshot s : snapshots.subList(firstRetained - 1, snapshots.size())) {
            entries.add(List.of(
                    String.valueOf(s.id),
                    String.valueOf(s.parent),
                    String.valueOf(s.timestamp),
                    s.operation,
                    String.valueOf(s.added.size()),
                    String.valueOf(s.removed.size())));
        }
        return entries;
    }

    // Level 3
    public List<String> commit(int base, List<List<String>> adds, List<String> removes, long timestamp) {
        int current = currentSnapshot();
        boolean baseOk = (base == 0 && firstRetained == 1) || retained(base);
        if (!baseOk || (adds.isEmpty() && removes.isEmpty()) || !fresh(adds) || !removable(removes, base)) {
            return List.of("invalid", "");
        }
        Set<String> removing = new HashSet<>(removes);
        Set<String> partitions = new HashSet<>();
        for (String path : removes) {
            partitions.add(files.get(path).partition);
        }
        for (Snapshot snapshot : snapshots.subList(base, current)) {
            boolean removedTwice = false;
            for (DataFile file : snapshot.removed) {
                removedTwice |= removing.contains(file.path);
            }
            boolean appended = false;
            if (!snapshot.operation.equals("replace")) {
                for (DataFile file : snapshot.added) {
                    appended |= partitions.contains(file.partition);
                }
            }
            if (removedTwice || appended) {
                return List.of("conflict", String.valueOf(snapshot.id));
            }
        }
        String outcome = base == current ? "committed" : "rebased";
        return List.of(outcome, String.valueOf(commitChange(adds, removes, timestamp, null)));
    }

    // Level 4
    public List<String> expireSnapshots(long olderThan, int retainLast) {
        int oldFirst = firstRetained;
        int lastCandidate = currentSnapshot() - retainLast;
        while (firstRetained <= lastCandidate && snapshots.get(firstRetained - 1).timestamp < olderThan) {
            firstRetained++;
        }
        List<String> freed = new ArrayList<>();
        for (DataFile file : files.values()) {
            if (oldFirst < file.removed && file.removed <= firstRetained) {
                freed.add(file.path);
            }
        }
        Collections.sort(freed);
        return freed;
    }

    public int compact(String partition, int maxFileRows, long timestamp) {
        int current = currentSnapshot();
        List<String> small = new ArrayList<>();
        long rows = 0;
        for (DataFile file : files.values()) {
            if (file.partition.equals(partition) && file.liveAt(current) && Long.parseLong(file.rows) < maxFileRows) {
                small.add(file.path);
                rows += Long.parseLong(file.rows);
            }
        }
        if (small.size() < 2) {
            return -1;
        }
        String path = partition + "/compacted-" + (current + 1);
        return commitChange(List.of(List.of(path, partition, String.valueOf(rows))), small, timestamp, "replace");
    }

    // Helpers
    private boolean retained(int snapshotId) {
        return firstRetained <= snapshotId && snapshotId <= currentSnapshot();
    }

    private boolean fresh(List<List<String>> adds) {
        Set<String> paths = new HashSet<>();
        for (List<String> file : adds) {
            if (!paths.add(file.get(0)) || files.containsKey(file.get(0))) {
                return false;
            }
        }
        return true;
    }

    private boolean removable(List<String> paths, int snapshotId) {
        if (new HashSet<>(paths).size() != paths.size()) {
            return false;
        }
        for (String path : paths) {
            DataFile file = files.get(path);
            if (file == null || !file.liveAt(snapshotId)) {
                return false;
            }
        }
        return true;
    }

    private int commitChange(List<List<String>> adds, List<String> removes, long timestamp, String operation) {
        int parent = currentSnapshot();
        int id = parent + 1;
        String kind = operation;
        if (kind == null) {
            kind = !adds.isEmpty() && !removes.isEmpty() ? "overwrite" : !adds.isEmpty() ? "append" : "delete";
        }
        Snapshot snapshot = new Snapshot(id, parent, timestamp, kind);
        for (String path : removes) {
            DataFile file = files.get(path);
            file.removed = id;
            snapshot.removed.add(file);
        }
        for (List<String> add : adds) {
            DataFile file = new DataFile(add.get(0), add.get(1), add.get(2), id);
            files.put(file.path, file);
            snapshot.added.add(file);
        }
        snapshots.add(snapshot);
        return id;
    }
}
