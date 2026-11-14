import cs.support.*;
import java.util.*;

public class Solution {
    public int maxDepth(TreeNode root) {
        Deque<TreeNode> level = new ArrayDeque<>();
        if (root != null) {
            level.add(root);
        }
        int depth = 0;
        while (!level.isEmpty()) {
            depth++;
            // Drain exactly the nodes of the current level; their children form the next one.
            for (int remaining = level.size(); remaining > 0; remaining--) {
                TreeNode node = level.poll();
                if (node.left != null) {
                    level.add(node.left);
                }
                if (node.right != null) {
                    level.add(node.right);
                }
            }
        }
        return depth;
    }
}
