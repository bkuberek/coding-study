import java.util.*;

/**
 * Each process keeps the current value of its three clocks: a Lamport counter, a vector and a
 * hybrid pair. Every event updates them by the rules of its kind and keeps a copy as its stamp,
 * so every question afterwards is answered from the stamps alone.
 */
public class LogicalClocks {
    private static final class Stamp {
        final int process;
        final int lamport;
        final int[] vector;
        final long l;
        final long c;
        final long wall;
        final boolean isSend;
        String value = "";

        Stamp(int process, int lamport, int[] vector, long l, long c, long wall, boolean isSend) {
            this.process = process;
            this.lamport = lamport;
            this.vector = vector;
            this.l = l;
            this.c = c;
            this.wall = wall;
            this.isSend = isSend;
        }
    }

    private final int processes;
    private final int[] lamportNow;
    private final int[][] vectorNow;
    private final long[][] hybridNow;
    private final Map<String, Stamp> events = new HashMap<>();
    private final Set<String> received = new HashSet<>();
    private final Map<String, List<String>> writes = new HashMap<>();

    public LogicalClocks(int processes) {
        this.processes = processes;
        this.lamportNow = new int[processes];
        this.vectorNow = new int[processes][processes];
        this.hybridNow = new long[processes][2];
    }

    // Level 1
    public int local(int process, String event, long wall) {
        return record(process, event, wall, null, false);
    }

    public int send(int process, String event, long wall) {
        return record(process, event, wall, null, true);
    }

    public int receive(int process, String event, String message, long wall) {
        Stamp sent = events.get(message);
        if (sent == null || !sent.isSend || received.contains(message)) {
            return -1;
        }
        if (sent.process == process) {
            return -1;
        }
        int stamp = record(process, event, wall, sent, false);
        if (stamp != -1) {
            received.add(message);
        }
        return stamp;
    }

    public List<String> totalOrder() {
        return sortedBy(Comparator.<Stamp>comparingInt(s -> s.lamport).thenComparingInt(s -> s.process));
    }

    // Level 2
    public List<Integer> vector(String event) {
        Stamp stamp = events.get(event);
        List<Integer> answer = new ArrayList<>();
        if (stamp != null) {
            for (int entry : stamp.vector) {
                answer.add(entry);
            }
        }
        return answer;
    }

    public String compare(String first, String second) {
        Stamp one = events.get(first);
        Stamp other = events.get(second);
        if (one == null || other == null) {
            return "";
        }
        if (first.equals(second)) {
            return "same";
        }
        if (atMost(one.vector, other.vector)) {
            return "before";
        }
        if (atMost(other.vector, one.vector)) {
            return "after";
        }
        return "concurrent";
    }

    // Level 3
    public int write(int process, String event, String key, String value, long wall) {
        int stamp = record(process, event, wall, null, false);
        if (stamp != -1) {
            events.get(event).value = value;
            writes.computeIfAbsent(key, k -> new ArrayList<>()).add(event);
        }
        return stamp;
    }

    public List<String> read(int process, String key) {
        if (process < 0 || process >= processes) {
            return new ArrayList<>();
        }
        int[] now = vectorNow[process];
        List<Stamp> known = new ArrayList<>();
        for (String name : writes.getOrDefault(key, List.of())) {
            Stamp stamp = events.get(name);
            if (atMost(stamp.vector, now)) {
                known.add(stamp);
            }
        }
        List<String> values = new ArrayList<>();
        for (Stamp stamp : known) {
            boolean superseded = false;
            for (Stamp other : known) {
                if (other != stamp && atMost(stamp.vector, other.vector)) {
                    superseded = true;
                    break;
                }
            }
            if (!superseded) {
                values.add(stamp.value);
            }
        }
        Collections.sort(values);
        return values;
    }

    public List<List<String>> concurrentWrites(String key) {
        List<String> names = new ArrayList<>(writes.getOrDefault(key, List.of()));
        Collections.sort(names);
        List<List<String>> pairs = new ArrayList<>();
        for (int i = 0; i < names.size(); i++) {
            for (int j = i + 1; j < names.size(); j++) {
                if (compare(names.get(i), names.get(j)).equals("concurrent")) {
                    pairs.add(List.of(names.get(i), names.get(j)));
                }
            }
        }
        return pairs;
    }

    // Level 4
    public List<Long> hlc(String event) {
        Stamp stamp = events.get(event);
        return stamp == null ? new ArrayList<>() : new ArrayList<>(List.of(stamp.l, stamp.c));
    }

    public List<String> hlcOrder() {
        return sortedBy(Comparator.<Stamp>comparingLong(s -> s.l)
                .thenComparingLong(s -> s.c)
                .thenComparingInt(s -> s.process));
    }

    public long maxOffset() {
        long largest = 0;
        for (Stamp stamp : events.values()) {
            largest = Math.max(largest, stamp.l - stamp.wall);
        }
        return largest;
    }

    // Shared
    private static boolean atMost(int[] first, int[] second) {
        for (int i = 0; i < first.length; i++) {
            if (first[i] > second[i]) {
                return false;
            }
        }
        return true;
    }

    private List<String> sortedBy(Comparator<Stamp> order) {
        List<String> names = new ArrayList<>(events.keySet());
        names.sort((a, b) -> order.compare(events.get(a), events.get(b)));
        return names;
    }

    private int record(int process, String event, long wall, Stamp sent, boolean isSend) {
        if (process < 0 || process >= processes || events.containsKey(event)) {
            return -1;
        }
        int lamport = lamportNow[process];
        int[] vector = vectorNow[process].clone();
        if (sent == null) {
            lamport += 1;
        } else {
            lamport = Math.max(lamport, sent.lamport) + 1;
            for (int i = 0; i < processes; i++) {
                vector[i] = Math.max(vector[i], sent.vector[i]);
            }
        }
        vector[process] += 1;
        long[] hybrid = nextHybrid(hybridNow[process], wall, sent);
        lamportNow[process] = lamport;
        vectorNow[process] = vector;
        hybridNow[process] = hybrid;
        events.put(event, new Stamp(process, lamport, vector, hybrid[0], hybrid[1], wall, isSend));
        return lamport;
    }

    /**
     * The update of Kulkarni et al.: {@code l} is the largest physical reading heard of, and
     * {@code c} counts the events since {@code l} last changed.
     */
    private static long[] nextHybrid(long[] current, long wall, Stamp sent) {
        long oldL = current[0];
        long oldC = current[1];
        if (sent == null) {
            long l = Math.max(oldL, wall);
            return new long[] {l, l == oldL ? oldC + 1 : 0};
        }
        long l = Math.max(Math.max(oldL, sent.l), wall);
        if (l == oldL && l == sent.l) {
            return new long[] {l, Math.max(oldC, sent.c) + 1};
        }
        if (l == oldL) {
            return new long[] {l, oldC + 1};
        }
        if (l == sent.l) {
            return new long[] {l, sent.c + 1};
        }
        return new long[] {l, 0};
    }
}
