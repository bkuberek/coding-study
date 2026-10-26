import cs.support.*;

public class Solution {
    private int best;

    public int maxPathSum(TreeNode root) {
        best = root.val;
        gain(root);
        return best;
    }

    /** Best downward path sum from {@code node}, recording the best path turning at it. */
    private int gain(TreeNode node) {
        if (node == null) {
            return 0;
        }
        int left = Math.max(0, gain(node.left));
        int right = Math.max(0, gain(node.right));
        best = Math.max(best, node.val + left + right);
        return node.val + Math.max(left, right);
    }
}
