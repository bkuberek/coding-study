import cs.support.*;
import java.util.*;

public class BSTIterator {
    private final List<Integer> values = new ArrayList<>();
    private int position;

    public BSTIterator(TreeNode root) {
        collect(root);
    }

    private void collect(TreeNode node) {
        if (node == null) {
            return;
        }
        collect(node.left);
        values.add(node.val);
        collect(node.right);
    }

    public int next() {
        return values.get(position++);
    }

    public boolean hasNext() {
        return position < values.size();
    }
}
