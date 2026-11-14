public class RangeModule {
    private static final int EMPTY = 0;
    private static final int COVERED = 1;
    private static final int MIXED = 2;
    private static final int LOW = 1;
    private static final int HIGH = 1_000_000_000; // every range lies inside [1, 10^9)

    /** EMPTY or COVERED with no children, or MIXED with both children. */
    private static final class Node {
        int state;
        Node left;
        Node right;

        Node(int state) {
            this.state = state;
        }
    }

    private final Node root = new Node(EMPTY);

    public RangeModule() {
    }

    public void addRange(int left, int right) {
        assign(root, LOW, HIGH, left, right, COVERED);
    }

    public boolean queryRange(int left, int right) {
        return covered(root, LOW, HIGH, left, right);
    }

    public void removeRange(int left, int right) {
        assign(root, LOW, HIGH, left, right, EMPTY);
    }

    private void assign(Node node, int low, int high, int left, int right, int value) {
        if (right <= low || high <= left) {
            return;
        }
        if (left <= low && high <= right) {
            node.state = value;
            node.left = null;
            node.right = null;
            return;
        }
        if (node.left == null) {
            // A uniform node is split: both halves inherit its state.
            node.left = new Node(node.state);
            node.right = new Node(node.state);
        }
        int middle = low + (high - low) / 2;
        assign(node.left, low, middle, left, right, value);
        assign(node.right, middle, high, left, right, value);
        if (node.left.state == node.right.state && node.left.state != MIXED) {
            node.state = node.left.state; // both halves agree: collapse
            node.left = null;
            node.right = null;
        } else {
            node.state = MIXED;
        }
    }

    private boolean covered(Node node, int low, int high, int left, int right) {
        if (right <= low || high <= left) {
            return true;
        }
        if (node.left == null) {
            return node.state == COVERED;
        }
        int middle = low + (high - low) / 2;
        return covered(node.left, low, middle, left, right) && covered(node.right, middle, high, left, right);
    }
}
