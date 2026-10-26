import cs.support.*;

public class Solution {
    public int diameterOfBinaryTree(TreeNode root) {
        if (root == null) {
            return 0;
        }
        int turningHere = height(root.left) + height(root.right);
        int below = Math.max(diameterOfBinaryTree(root.left), diameterOfBinaryTree(root.right));
        return Math.max(turningHere, below);
    }

    /** Number of nodes on the longest downward path from {@code node}. */
    private static int height(TreeNode node) {
        return node == null ? 0 : 1 + Math.max(height(node.left), height(node.right));
    }
}
