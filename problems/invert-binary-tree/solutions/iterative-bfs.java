import cs.support.*;
import java.util.*;

public class Solution {
    public TreeNode invertTree(TreeNode root) {
        Deque<TreeNode> pending = new ArrayDeque<>();
        if (root != null) {
            pending.add(root);
        }
        while (!pending.isEmpty()) {
            TreeNode node = pending.poll();
            TreeNode left = node.left;
            node.left = node.right;
            node.right = left;
            // ArrayDeque rejects null elements, so only real children are queued.
            if (node.left != null) {
                pending.add(node.left);
            }
            if (node.right != null) {
                pending.add(node.right);
            }
        }
        return root;
    }
}
