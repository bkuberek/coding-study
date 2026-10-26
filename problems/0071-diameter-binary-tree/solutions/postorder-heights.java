import cs.support.*;

public class Solution {
    private int best;

    public int diameterOfBinaryTree(TreeNode root) {
        best = 0;
        height(root);
        return best;
    }

    /** Height of {@code node} in nodes; records the longest path turning at it on the way. */
    private int height(TreeNode node) {
        if (node == null) {
            return 0;
        }
        int left = height(node.left);
        int right = height(node.right);
        best = Math.max(best, left + right);
        return 1 + Math.max(left, right);
    }
}
