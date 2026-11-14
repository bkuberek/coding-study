import cs.support.*;
import java.util.*;

public class BSTIterator {
    // Nodes whose left subtree is finished (or about to be) and that are not returned yet.
    private final Deque<TreeNode> stack = new ArrayDeque<>();

    public BSTIterator(TreeNode root) {
        pushLeftSpine(root);
    }

    private void pushLeftSpine(TreeNode node) {
        for (TreeNode current = node; current != null; current = current.left) {
            stack.push(current);
        }
    }

    public int next() {
        TreeNode node = stack.pop();
        pushLeftSpine(node.right);
        return node.val;
    }

    public boolean hasNext() {
        return !stack.isEmpty();
    }
}
