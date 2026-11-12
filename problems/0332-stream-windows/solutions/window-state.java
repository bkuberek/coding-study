import java.util.*;

/**
 * Every event is kept in a log, so the batch views of levels 1 and 2 can group the whole stream
 * in any way they are asked.
 *
 * <p>The stream of levels 3 and 4 keeps a sorted map from (start, key) to a running count and sum
 * for the windows not yet emitted, and a second map for the windows already emitted that can
 * still be corrected. After each event the watermark moves, the open windows it has passed are
 * emitted in order, and the corrected windows it has left behind are forgotten.
 */
public class StreamWindows {
    private static final long KEYS = 1L << 21;

    private final List<int[]> events = new ArrayList<>();
    private int size = 0;
    private int lateness = 0;
    private int grace = 0;
    private int mark = 0;
    private final TreeMap<Long, int[]> open = new TreeMap<>();
    private final TreeMap<Long, int[]> closed = new TreeMap<>();
    private List<List<Integer>> out = new ArrayList<>();
    private final List<List<Integer>> side = new ArrayList<>();
    private int emitted = 0;
    private int updated = 0;

    /** One number per (start, key), ordered by start and then key, since 0 <= key < KEYS. */
    private static long window(int start, int key) {
        return start * KEYS + key;
    }

    private static int startOf(long window) {
        return (int) Math.floorDiv(window, KEYS);
    }

    private static int keyOf(long window) {
        return (int) Math.floorMod(window, KEYS);
    }

    private static void bump(Map<Long, int[]> groups, long window, int value) {
        int[] totals = groups.computeIfAbsent(window, w -> new int[2]);
        totals[0] += 1;
        totals[1] += value;
    }

    private static List<Integer> row(long window, int size, int count, int sum) {
        int start = startOf(window);
        return List.of(keyOf(window), start, start + size, count, sum);
    }

    private static List<List<Integer>> rows(TreeMap<Long, int[]> groups, int size) {
        List<List<Integer>> rows = new ArrayList<>();
        for (Map.Entry<Long, int[]> entry : groups.entrySet()) {
            rows.add(row(entry.getKey(), size, entry.getValue()[0], entry.getValue()[1]));
        }
        return rows;
    }

    // Level 1
    public void add(int key, int time, int value) {
        events.add(new int[] {key, time, value});
        if (size > 0) {
            stream(key, time, value);
        }
    }

    public List<List<Integer>> tumbling(int size) {
        TreeMap<Long, int[]> groups = new TreeMap<>();
        for (int[] event : events) {
            bump(groups, window(event[1] - event[1] % size, event[0]), event[2]);
        }
        return rows(groups, size);
    }

    // Level 2
    public List<List<Integer>> hopping(int size, int slide) {
        TreeMap<Long, int[]> groups = new TreeMap<>();
        for (int[] event : events) {
            int time = event[1];
            for (int start = time - time % slide; start > time - size; start -= slide) {
                bump(groups, window(start, event[0]), event[2]);
            }
        }
        return rows(groups, size);
    }

    public List<List<Integer>> sessions(int gap) {
        Map<Integer, List<int[]>> byKey = new HashMap<>();
        for (int[] event : events) {
            byKey.computeIfAbsent(event[0], k -> new ArrayList<>()).add(event);
        }
        List<int[]> sessions = new ArrayList<>();
        for (List<int[]> list : byKey.values()) {
            list.sort(Comparator.comparingInt(e -> e[1]));
            int[] current = null;
            for (int[] event : list) {
                if (current != null && event[1] < current[2]) {
                    current[2] = event[1] + gap;
                    current[3] += 1;
                    current[4] += event[2];
                } else {
                    current = new int[] {event[0], event[1], event[1] + gap, 1, event[2]};
                    sessions.add(current);
                }
            }
        }
        sessions.sort(Comparator.<int[]>comparingInt(s -> s[1]).thenComparingInt(s -> s[0]));
        List<List<Integer>> rows = new ArrayList<>();
        for (int[] s : sessions) {
            rows.add(List.of(s[0], s[1], s[2], s[3], s[4]));
        }
        return rows;
    }

    // Level 3
    public void configure(int size, int lateness) {
        this.size = size;
        this.lateness = lateness;
    }

    public int watermark() {
        return mark;
    }

    public List<List<Integer>> pending() {
        return rows(open, size);
    }

    public List<List<Integer>> poll() {
        List<List<Integer>> result = out;
        out = new ArrayList<>();
        return result;
    }

    // Level 4
    public void allowUpdates(int grace) {
        this.grace = grace;
    }

    public List<List<Integer>> dropped() {
        return new ArrayList<>(side);
    }

    public List<Integer> stats() {
        return List.of(emitted, updated, side.size());
    }

    // The stream
    private void stream(int key, int time, int value) {
        int start = time - time % size;
        int end = start + size;
        long w = window(start, key);
        if (end > mark) {
            bump(open, w, value);
        } else if (mark < end + grace) {
            correct(w, value);
        } else {
            side.add(List.of(key, time, value));
        }
        advance(time - lateness);
    }

    private void correct(long w, int value) {
        int[] old = closed.get(w);
        if (old == null) {
            int[] first = {1, value};
            closed.put(w, first);
            emitted += 1;
            out.add(row(w, size, first[0], first[1]));
        } else {
            out.add(row(w, size, -old[0], -old[1]));
            old[0] += 1;
            old[1] += value;
            updated += 1;
            out.add(row(w, size, old[0], old[1]));
        }
    }

    private void advance(int candidate) {
        if (candidate <= mark) {
            return;
        }
        mark = candidate;
        // A window is due when start + size <= mark, that is, when its number is below this bound.
        long bound = window(mark - size + 1, 0);
        SortedMap<Long, int[]> due = open.headMap(bound);
        for (Map.Entry<Long, int[]> entry : due.entrySet()) {
            int[] totals = entry.getValue();
            out.add(row(entry.getKey(), size, totals[0], totals[1]));
            closed.put(entry.getKey(), totals);
            emitted += 1;
        }
        due.clear();
        closed.headMap(window(mark - size - grace + 1, 0)).clear();
    }
}
