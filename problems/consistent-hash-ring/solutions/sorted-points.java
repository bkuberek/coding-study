import java.nio.charset.StandardCharsets;
import java.util.*;

/**
 * The ring is a list of points sorted by position and then by label, which is the ring order with
 * its tie-break. A key's owner is the first point at or after the key's position, found by binary
 * search, wrapping to the first point.
 */
public class HashRing {
    private static final long RING_SIZE = 1L << 32;
    private static final int FNV_OFFSET_BASIS = (int) 2166136261L;
    private static final int FNV_PRIME = 16777619;
    private static final Comparator<Point> RING_ORDER =
            Comparator.comparingLong(Point::position).thenComparing(Point::label);

    private record Point(long position, String label, String node) {}

    private List<Point> points = new ArrayList<>();
    private final List<String> joined = new ArrayList<>();
    private final Map<String, Integer> counts = new HashMap<>();
    private final Set<String> tracked = new HashSet<>();
    private List<List<String>> report = new ArrayList<>();

    /** FNV-1a, 32 bits, over the UTF-8 bytes; {@code int} multiplication wraps at 32 bits. */
    private static long fnv1a(String text) {
        int value = FNV_OFFSET_BASIS;
        for (byte b : text.getBytes(StandardCharsets.UTF_8)) {
            value = (value ^ (b & 0xff)) * FNV_PRIME;
        }
        return Integer.toUnsignedLong(value);
    }

    /**
     * Point 0 is the bare name and point i is {@code i#node}: the number goes first, because
     * FNV-1a mixes the first bytes of a text far better than its last ones.
     */
    private static List<String> labelsOf(String node, int count) {
        List<String> labels = new ArrayList<>(List.of(node));
        for (int index = 1; index < count; index++) {
            labels.add(index + "#" + node);
        }
        return labels;
    }

    /** The index of the first point at or after the position, wrapping to 0 past the last one. */
    private static int startOf(List<Point> ring, long position) {
        int low = 0;
        int high = ring.size();
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (ring.get(middle).position() < position) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low < ring.size() ? low : 0;
    }

    private static String ownerIn(List<Point> ring, long position) {
        return ring.isEmpty() ? "" : ring.get(startOf(ring, position)).node();
    }

    private static String moduloIn(List<String> order, String key) {
        return order.isEmpty() ? "" : order.get((int) (fnv1a(key) % order.size()));
    }

    // Level 1
    public long positionOf(String text) {
        return fnv1a(text);
    }

    public long addNode(String node) {
        return addVirtualNode(node, 1) ? fnv1a(node) : -1;
    }

    public boolean removeNode(String node) {
        if (!counts.containsKey(node)) {
            return false;
        }
        Map<String, String> before = owners();
        points.removeIf(point -> point.node().equals(node));
        joined.remove(node);
        counts.remove(node);
        makeReport(before);
        return true;
    }

    public List<String> nodes() {
        List<String> sorted = new ArrayList<>(joined);
        Collections.sort(sorted);
        return sorted;
    }

    public String nodeFor(String key) {
        return ownerIn(points, fnv1a(key));
    }

    public String moduloNodeFor(String key) {
        return moduloIn(joined, key);
    }

    public List<Integer> countMoves(List<String> keys, String node) {
        if (counts.containsKey(node)) {
            return new ArrayList<>();
        }
        List<Point> grown = new ArrayList<>(points);
        grown.add(new Point(fnv1a(node), node, node));
        grown.sort(RING_ORDER);
        List<String> order = new ArrayList<>(joined);
        order.add(node);
        int ringMoves = 0;
        int moduloMoves = 0;
        for (String key : keys) {
            long position = fnv1a(key);
            if (!ownerIn(points, position).equals(ownerIn(grown, position))) {
                ringMoves++;
            }
            if (!moduloIn(joined, key).equals(moduloIn(order, key))) {
                moduloMoves++;
            }
        }
        return new ArrayList<>(List.of(ringMoves, moduloMoves));
    }

    // Level 2
    public boolean addVirtualNode(String node, int count) {
        if (counts.containsKey(node) || count < 1) {
            return false;
        }
        Map<String, String> before = owners();
        for (String label : labelsOf(node, count)) {
            points.add(new Point(fnv1a(label), label, node));
        }
        points.sort(RING_ORDER);
        joined.add(node);
        counts.put(node, count);
        makeReport(before);
        return true;
    }

    public List<Long> positions(String node) {
        List<Long> found = new ArrayList<>();
        if (counts.containsKey(node)) {
            for (String label : labelsOf(node, counts.get(node))) {
                found.add(fnv1a(label));
            }
        }
        return found;
    }

    public List<Long> arcShare() {
        Map<String, Long> share = new HashMap<>();
        for (int index = 0; index < points.size(); index++) {
            Point point = points.get(index);
            long previous = points.get((index + points.size() - 1) % points.size()).position();
            long arc = index > 0 ? point.position() - previous : point.position() - previous + RING_SIZE;
            share.merge(point.node(), arc, Long::sum);
        }
        List<Long> answer = new ArrayList<>();
        for (String node : nodes()) {
            answer.add(share.getOrDefault(node, 0L));
        }
        return answer;
    }

    public List<Integer> keyCounts(List<String> keys) {
        Map<String, Integer> owned = new HashMap<>();
        for (String key : keys) {
            owned.merge(nodeFor(key), 1, Integer::sum);
        }
        List<Integer> answer = new ArrayList<>();
        for (String node : nodes()) {
            answer.add(owned.getOrDefault(node, 0));
        }
        return answer;
    }

    // Level 3
    public int trackKeys(List<String> keys) {
        tracked.addAll(keys);
        return tracked.size();
    }

    public List<List<String>> lastMoves() {
        List<List<String>> copy = new ArrayList<>();
        for (List<String> row : report) {
            copy.add(new ArrayList<>(row));
        }
        return copy;
    }

    public List<String> ownedKeys(String node) {
        List<String> owned = new ArrayList<>();
        if (counts.containsKey(node)) {
            for (String key : tracked) {
                if (nodeFor(key).equals(node)) {
                    owned.add(key);
                }
            }
            Collections.sort(owned);
        }
        return owned;
    }

    // Level 4
    public List<String> replicas(String key, int count) {
        List<String> found = new ArrayList<>();
        if (count < 1 || points.isEmpty()) {
            return found;
        }
        int start = startOf(points, fnv1a(key));
        for (int step = 0; step < points.size() && found.size() < count; step++) {
            String node = points.get((start + step) % points.size()).node();
            if (!found.contains(node)) {
                found.add(node);
            }
        }
        return found;
    }

    public List<String> assignBounded(List<String> keys, int numerator, int denominator) {
        List<String> assigned = new ArrayList<>();
        if (points.isEmpty() || keys.isEmpty()) {
            return assigned;
        }
        long total = (long) (denominator + numerator) * keys.size();
        long share = (long) denominator * joined.size();
        long capacity = (total + share - 1) / share;
        Map<String, Integer> load = new HashMap<>();
        for (String key : keys) {
            int index = startOf(points, fnv1a(key));
            while (load.getOrDefault(points.get(index).node(), 0) >= capacity) {
                index = (index + 1) % points.size();
            }
            String node = points.get(index).node();
            load.merge(node, 1, Integer::sum);
            assigned.add(node);
        }
        return assigned;
    }

    // Shared
    private Map<String, String> owners() {
        Map<String, String> owners = new HashMap<>();
        for (String key : tracked) {
            owners.put(key, nodeFor(key));
        }
        return owners;
    }

    private void makeReport(Map<String, String> before) {
        List<List<String>> rows = new ArrayList<>();
        for (Map.Entry<String, String> entry : before.entrySet()) {
            String to = nodeFor(entry.getKey());
            if (!entry.getValue().equals(to)) {
                rows.add(List.of(entry.getKey(), entry.getValue(), to));
            }
        }
        rows.sort((one, other) -> one.get(0).compareTo(other.get(0)));
        report = rows;
    }
}
