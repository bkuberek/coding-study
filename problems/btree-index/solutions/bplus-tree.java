import java.util.*;

/**
 * A B+ tree: every entry lives in a leaf, the leaves are linked left to right, and the inner nodes
 * hold separator keys that only steer the way down. Keys are int arrays compared field by field
 * with Arrays.compare, which is exactly the order of a composite key. Every change walks down once
 * and keeps the path, then repairs nodes on the way back up: splits after an insert, borrows and
 * merges after a remove.
 */
public class BTreeIndex {
    private static final class Node {
        final boolean leaf;
        final List<int[]> keys = new ArrayList<>();
        final List<Integer> rows = new ArrayList<>();
        final List<Node> children = new ArrayList<>();
        Node next;

        Node(boolean leaf) {
            this.leaf = leaf;
        }
    }

    private record Step(Node node, int index) {
    }

    private final int d;
    private Node root = new Node(true);

    public BTreeIndex(int minKeys) {
        d = minKeys;
    }

    // Level 1
    public int search(int[] key) {
        Node leaf = descend(key, null);
        int at = lowerBound(leaf.keys, key);
        return holds(leaf, at, key) ? leaf.rows.get(at) : -1;
    }

    public boolean insert(int[] key, int rowId) {
        Deque<Step> path = new ArrayDeque<>();
        Node leaf = descend(key, path);
        int at = lowerBound(leaf.keys, key);
        if (holds(leaf, at, key)) {
            return false;
        }
        leaf.keys.add(at, key.clone());
        leaf.rows.add(at, rowId);
        splitUpward(leaf, path);
        return true;
    }

    public List<String> levels() {
        List<String> lines = new ArrayList<>();
        List<Node> level = List.of(root);
        while (!level.isEmpty()) {
            StringJoiner line = new StringJoiner(" ");
            List<Node> below = new ArrayList<>();
            for (Node node : level) {
                StringJoiner keys = new StringJoiner(" ", "[", "]");
                for (int[] key : node.keys) {
                    StringJoiner fields = new StringJoiner(",");
                    for (int field : key) {
                        fields.add(Integer.toString(field));
                    }
                    keys.add(fields.toString());
                }
                line.add(keys.toString());
                below.addAll(node.children);
            }
            lines.add(line.toString());
            level = below;
        }
        return lines;
    }

    // Level 2
    public List<Integer> rangeScan(int[] low, int[] high) {
        List<Integer> rows = new ArrayList<>();
        scan(low, high, rows);
        return rows;
    }

    public int scanVisits(int[] low, int[] high) {
        return scan(low, high, new ArrayList<>());
    }

    public int height() {
        int count = 1;
        for (Node node = root; !node.leaf; node = node.children.get(0)) {
            count++;
        }
        return count;
    }

    // Level 3
    public boolean remove(int[] key) {
        Deque<Step> path = new ArrayDeque<>();
        Node leaf = descend(key, path);
        int at = lowerBound(leaf.keys, key);
        if (!holds(leaf, at, key)) {
            return false;
        }
        leaf.keys.remove(at);
        leaf.rows.remove(at);
        Node node = leaf;
        while (!path.isEmpty() && node.keys.size() < d) {
            Step step = path.pop();
            if (node.leaf) {
                fixLeaf(step.node(), step.index());
            } else {
                fixInner(step.node(), step.index());
            }
            node = step.node();
        }
        if (!root.leaf && root.keys.isEmpty()) {
            root = root.children.get(0);
        }
        return true;
    }

    // Level 4
    public boolean bulkLoad(int[][] keys, int[] rowIds, int fillPercent) {
        if (!root.leaf || !root.keys.isEmpty()) {
            return false;
        }
        for (int i = 0; i + 1 < keys.length; i++) {
            if (Arrays.compare(keys[i], keys[i + 1]) >= 0) {
                return false;
            }
        }
        if (keys.length == 0) {
            return true;
        }
        int per = 2 * d * fillPercent / 100;
        List<Node> level = new ArrayList<>();
        List<int[]> lowest = new ArrayList<>();
        int start = 0;
        for (int size : sizes(keys.length, per, d, 2 * d)) {
            Node leaf = new Node(true);
            for (int i = start; i < start + size; i++) {
                leaf.keys.add(keys[i].clone());
                leaf.rows.add(rowIds[i]);
            }
            if (!level.isEmpty()) {
                level.get(level.size() - 1).next = leaf;
            }
            level.add(leaf);
            lowest.add(leaf.keys.get(0));
            start += size;
        }
        while (level.size() > 1) {
            List<Node> parents = new ArrayList<>();
            List<int[]> parentLowest = new ArrayList<>();
            start = 0;
            for (int size : sizes(level.size(), per + 1, d + 1, 2 * d + 1)) {
                Node parent = new Node(false);
                parent.children.addAll(level.subList(start, start + size));
                parent.keys.addAll(lowest.subList(start + 1, start + size));
                parents.add(parent);
                parentLowest.add(lowest.get(start));
                start += size;
            }
            level = parents;
            lowest = parentLowest;
        }
        root = level.get(0);
        return true;
    }

    public List<Integer> prefixScan(int[] prefix) {
        int width = prefix.length;
        Node node = root;
        while (!node.leaf) {
            int index = 0;
            for (int[] separator : node.keys) {
                if (Arrays.compare(separator, 0, width, prefix, 0, width) < 0) {
                    index++;
                }
            }
            node = node.children.get(index);
        }
        List<Integer> rows = new ArrayList<>();
        for (Node leaf = node; leaf != null; leaf = leaf.next) {
            for (int i = 0; i < leaf.keys.size(); i++) {
                int order = Arrays.compare(leaf.keys.get(i), 0, width, prefix, 0, width);
                if (order > 0) {
                    return rows;
                }
                if (order == 0) {
                    rows.add(leaf.rows.get(i));
                }
            }
        }
        return rows;
    }

    // Helpers
    private Node descend(int[] key, Deque<Step> path) {
        Node node = root;
        while (!node.leaf) {
            int index = upperBound(node.keys, key);
            if (path != null) {
                path.push(new Step(node, index));
            }
            node = node.children.get(index);
        }
        return node;
    }

    private static boolean holds(Node leaf, int at, int[] key) {
        return at < leaf.keys.size() && Arrays.compare(leaf.keys.get(at), key) == 0;
    }

    /** The first position whose key is at least {@code key}. */
    private static int lowerBound(List<int[]> keys, int[] key) {
        int low = 0;
        int high = keys.size();
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (Arrays.compare(keys.get(middle), key) < 0) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low;
    }

    /** The number of keys that are at most {@code key}. */
    private static int upperBound(List<int[]> keys, int[] key) {
        int low = 0;
        int high = keys.size();
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (Arrays.compare(keys.get(middle), key) <= 0) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low;
    }

    private static <T> void moveTail(List<T> from, List<T> to, int start) {
        List<T> tail = from.subList(start, from.size());
        to.addAll(tail);
        tail.clear();
    }

    private void splitUpward(Node leaf, Deque<Step> path) {
        if (leaf.keys.size() <= 2 * d) {
            return;
        }
        Node right = new Node(true);
        moveTail(leaf.keys, right.keys, d);
        moveTail(leaf.rows, right.rows, d);
        right.next = leaf.next;
        leaf.next = right;
        Node left = leaf;
        int[] separator = right.keys.get(0);
        Node created = right;
        while (!path.isEmpty()) {
            Step step = path.pop();
            Node parent = step.node();
            parent.keys.add(step.index(), separator);
            parent.children.add(step.index() + 1, created);
            if (parent.keys.size() <= 2 * d) {
                return;
            }
            Node sibling = new Node(false);
            moveTail(parent.keys, sibling.keys, d + 1);
            moveTail(parent.children, sibling.children, d + 1);
            separator = parent.keys.remove(d);
            created = sibling;
            left = parent;
        }
        Node top = new Node(false);
        top.keys.add(separator);
        top.children.add(left);
        top.children.add(created);
        root = top;
    }

    private int scan(int[] low, int[] high, List<Integer> rows) {
        Deque<Step> path = new ArrayDeque<>();
        Node leaf = descend(low, path);
        int visits = path.size() + 1;
        int at = lowerBound(leaf.keys, low);
        while (true) {
            for (; at < leaf.keys.size(); at++) {
                if (Arrays.compare(leaf.keys.get(at), high) > 0) {
                    return visits;
                }
                rows.add(leaf.rows.get(at));
            }
            if (leaf.next == null) {
                return visits;
            }
            leaf = leaf.next;
            at = 0;
            visits++;
        }
    }

    private void fixLeaf(Node parent, int index) {
        Node node = parent.children.get(index);
        Node left = index > 0 ? parent.children.get(index - 1) : null;
        Node right = index + 1 < parent.children.size() ? parent.children.get(index + 1) : null;
        if (left != null && left.keys.size() > d) {
            node.keys.add(0, left.keys.remove(left.keys.size() - 1));
            node.rows.add(0, left.rows.remove(left.rows.size() - 1));
            parent.keys.set(index - 1, node.keys.get(0));
        } else if (right != null && right.keys.size() > d) {
            node.keys.add(right.keys.remove(0));
            node.rows.add(right.rows.remove(0));
            parent.keys.set(index, right.keys.get(0));
        } else if (left != null) {
            left.keys.addAll(node.keys);
            left.rows.addAll(node.rows);
            left.next = node.next;
            parent.keys.remove(index - 1);
            parent.children.remove(index);
        } else {
            node.keys.addAll(right.keys);
            node.rows.addAll(right.rows);
            node.next = right.next;
            parent.keys.remove(index);
            parent.children.remove(index + 1);
        }
    }

    private void fixInner(Node parent, int index) {
        Node node = parent.children.get(index);
        Node left = index > 0 ? parent.children.get(index - 1) : null;
        Node right = index + 1 < parent.children.size() ? parent.children.get(index + 1) : null;
        if (left != null && left.keys.size() > d) {
            node.keys.add(0, parent.keys.get(index - 1));
            parent.keys.set(index - 1, left.keys.remove(left.keys.size() - 1));
            node.children.add(0, left.children.remove(left.children.size() - 1));
        } else if (right != null && right.keys.size() > d) {
            node.keys.add(parent.keys.get(index));
            parent.keys.set(index, right.keys.remove(0));
            node.children.add(right.children.remove(0));
        } else if (left != null) {
            left.keys.add(parent.keys.remove(index - 1));
            left.keys.addAll(node.keys);
            left.children.addAll(node.children);
            parent.children.remove(index);
        } else {
            node.keys.add(parent.keys.remove(index));
            node.keys.addAll(right.keys);
            node.children.addAll(right.children);
            parent.children.remove(index + 1);
        }
    }

    private static List<Integer> sizes(int total, int per, int minimum, int maximum) {
        List<Integer> sizes = new ArrayList<>(Collections.nCopies(total / per, per));
        if (total % per != 0) {
            sizes.add(total % per);
        }
        int last = sizes.size() - 1;
        if (last > 0 && sizes.get(last) < minimum) {
            int pool = sizes.remove(last) + sizes.remove(last - 1);
            if (pool <= maximum) {
                sizes.add(pool);
            } else {
                sizes.add((pool + 1) / 2);
                sizes.add(pool / 2);
            }
        }
        return sizes;
    }
}
