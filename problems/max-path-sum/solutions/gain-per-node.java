import cs.support.*;

public class Solution {
    public int maxPathSum(TreeNode root) {
        int best = root.val + Math.max(0, gain(root.left)) + Math.max(0, gain(root.right));
        if (root.left != null) {
            best = Math.max(best, maxPathSum(root.left));
        }
        if (root.right != null) {
            best = Math.max(best, maxPathSum(root.right));
        }
        return best;
    }

    /** Largest sum of a path that starts at {@code node} and only goes down (0 for no node). */
    private static int gain(TreeNode node) {
        if (node == null) {
            return 0;
        }
        return node.val + Math.max(0, Math.max(gain(node.left), gain(node.right)));
    }
}
