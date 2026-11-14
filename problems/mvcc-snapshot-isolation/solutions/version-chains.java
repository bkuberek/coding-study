import java.util.*;

/**
 * Every key keeps a chain of committed versions, oldest first, each stamped with the commit time of
 * its writer and the id of that writer (0 for a put). A transaction buffers its writes until it
 * commits, so the chains only ever hold committed data, and a read is a binary search for the
 * newest stamp before the reader's start. Serializable transactions also leave their reads behind,
 * even after they commit, and every read-write antidependency between two of them is kept as a
 * pair of edges. An edge stops counting as soon as either end aborts.
 */
public class MvccStore {
    private static final class Transaction {
        final int start;
        final boolean serializable;
        String state = "active";
        int commitTime;
        final Map<String, String> writes = new LinkedHashMap<>();
        final Set<Integer> ins = new HashSet<>();
        final Set<Integer> outs = new HashSet<>();

        Transaction(int start, boolean serializable) {
            this.start = start;
            this.serializable = serializable;
        }
    }

    private static final class Chain {
        final List<Integer> stamps = new ArrayList<>();
        final List<String> values = new ArrayList<>();
        final List<Integer> writers = new ArrayList<>();

        /** The number of versions stamped before {@code time}. */
        int before(int time) {
            int position = Collections.binarySearch(stamps, time);
            return position >= 0 ? position : -position - 1;
        }
    }

    private int clock;
    private final Map<String, Chain> chains = new HashMap<>();
    private final Map<Integer, Transaction> transactions = new HashMap<>();
    private final Map<String, Set<Integer>> readers = new HashMap<>();

    // Level 1
    public int put(String key, String value) {
        clock++;
        append(key, value, clock, 0);
        return clock;
    }

    public int begin() {
        return start(false);
    }

    public String read(int tx, String key) {
        Transaction reader = active(tx);
        if (reader == null) {
            return "";
        }
        if (reader.writes.containsKey(key)) {
            return reader.writes.get(key);
        }
        if (reader.serializable && !recordRead(tx, reader, key)) {
            return "";
        }
        Chain chain = chains.get(key);
        if (chain == null) {
            return "";
        }
        int visible = chain.before(reader.start);
        return visible > 0 ? chain.values.get(visible - 1) : "";
    }

    public List<String> versions(String key) {
        List<String> listed = new ArrayList<>();
        Chain chain = chains.get(key);
        if (chain != null) {
            for (int i = chain.stamps.size() - 1; i >= 0; i--) {
                listed.add(chain.stamps.get(i) + ":" + chain.values.get(i));
            }
        }
        return listed;
    }

    // Level 2
    public boolean write(int tx, String key, String value) {
        Transaction writer = active(tx);
        if (writer == null) {
            return false;
        }
        if (writer.serializable && !recordWrite(tx, writer, key)) {
            return false;
        }
        writer.writes.put(key, value);
        return true;
    }

    public String commit(int tx) {
        Transaction t = active(tx);
        if (t == null) {
            return "not-active";
        }
        for (String key : t.writes.keySet()) {
            Chain chain = chains.get(key);
            if (chain != null && chain.stamps.get(chain.stamps.size() - 1) > t.start) {
                t.state = "aborted";
                return "write-conflict";
            }
        }
        if (t.serializable && !live(t.ins).isEmpty() && !live(t.outs).isEmpty()) {
            t.state = "aborted";
            return "dangerous-structure";
        }
        clock++;
        t.state = "committed";
        t.commitTime = clock;
        for (Map.Entry<String, String> entry : t.writes.entrySet()) {
            append(entry.getKey(), entry.getValue(), clock, tx);
        }
        return "committed";
    }

    public boolean abort(int tx) {
        Transaction t = active(tx);
        if (t == null) {
            return false;
        }
        t.state = "aborted";
        return true;
    }

    public String status(int tx) {
        Transaction t = transactions.get(tx);
        return t == null ? "unknown" : t.state;
    }

    // Level 3
    public int beginSerializable() {
        return start(true);
    }

    public List<String> antidependencies(int tx) {
        Transaction t = transactions.get(tx);
        List<String> edges = new ArrayList<>();
        if (t == null || t.state.equals("aborted")) {
            return edges;
        }
        for (int other : new TreeSet<>(live(t.ins))) {
            edges.add("in:" + other);
        }
        for (int other : new TreeSet<>(live(t.outs))) {
            edges.add("out:" + other);
        }
        return edges;
    }

    // Level 4
    public int horizon() {
        int oldest = clock;
        boolean any = false;
        for (Transaction t : transactions.values()) {
            if (t.state.equals("active") && (!any || t.start < oldest)) {
                oldest = t.start;
                any = true;
            }
        }
        return oldest;
    }

    public List<String> vacuum() {
        int limit = horizon();
        List<String> removed = new ArrayList<>();
        for (String key : new TreeSet<>(chains.keySet())) {
            Chain chain = chains.get(key);
            int keepFrom = chain.before(limit + 1) - 1;
            if (keepFrom <= 0) {
                continue;
            }
            for (int i = 0; i < keepFrom; i++) {
                removed.add(key + "@" + chain.stamps.get(i));
            }
            chain.stamps.subList(0, keepFrom).clear();
            chain.values.subList(0, keepFrom).clear();
            chain.writers.subList(0, keepFrom).clear();
        }
        return removed;
    }

    // Helpers
    private int start(boolean serializable) {
        clock++;
        transactions.put(clock, new Transaction(clock, serializable));
        return clock;
    }

    private Transaction active(int tx) {
        Transaction t = transactions.get(tx);
        return t != null && t.state.equals("active") ? t : null;
    }

    private void append(String key, String value, int stamp, int writer) {
        Chain chain = chains.computeIfAbsent(key, ignored -> new Chain());
        chain.stamps.add(stamp);
        chain.values.add(value);
        chain.writers.add(writer);
    }

    private boolean takesPart(int tx) {
        Transaction t = transactions.get(tx);
        return t != null && t.serializable && !t.state.equals("aborted");
    }

    private Set<Integer> live(Set<Integer> ids) {
        Set<Integer> result = new HashSet<>();
        for (int other : ids) {
            if (!transactions.get(other).state.equals("aborted")) {
                result.add(other);
            }
        }
        return result;
    }

    /**
     * The reader misses every version committed after it began and every write still buffered by
     * an active transaction: each such writer gets an edge from the reader.
     */
    private boolean recordRead(int tx, Transaction reader, String key) {
        List<Integer> committed = new ArrayList<>();
        Chain chain = chains.get(key);
        if (chain != null) {
            for (int i = chain.before(reader.start); i < chain.writers.size(); i++) {
                if (takesPart(chain.writers.get(i))) {
                    committed.add(chain.writers.get(i));
                }
            }
        }
        for (int writer : committed) {
            if (!live(transactions.get(writer).outs).isEmpty()) {
                reader.state = "aborted";
                return false;
            }
        }
        List<Integer> missed = new ArrayList<>(committed);
        for (Map.Entry<Integer, Transaction> entry : transactions.entrySet()) {
            Transaction other = entry.getValue();
            if (entry.getKey() != tx && other.serializable && other.state.equals("active")
                    && other.writes.containsKey(key)) {
                missed.add(entry.getKey());
            }
        }
        readers.computeIfAbsent(key, ignored -> new HashSet<>()).add(tx);
        for (int writer : missed) {
            edge(tx, writer);
        }
        return true;
    }

    /** Every reader of the key that overlaps the writer gets an edge to it. */
    private boolean recordWrite(int tx, Transaction writer, String key) {
        List<Integer> overlapping = new ArrayList<>();
        for (int other : readers.getOrDefault(key, Set.of())) {
            Transaction t = transactions.get(other);
            if (other == tx || !takesPart(other)) {
                continue;
            }
            if (t.state.equals("active") || t.commitTime > writer.start) {
                overlapping.add(other);
            }
        }
        for (int other : overlapping) {
            Transaction t = transactions.get(other);
            if (t.state.equals("committed") && !live(t.ins).isEmpty()) {
                writer.state = "aborted";
                return false;
            }
        }
        for (int reader : overlapping) {
            edge(reader, tx);
        }
        return true;
    }

    private void edge(int reader, int writer) {
        transactions.get(reader).outs.add(writer);
        transactions.get(writer).ins.add(reader);
    }
}
