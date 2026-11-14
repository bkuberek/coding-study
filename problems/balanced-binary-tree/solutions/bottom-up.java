import cs.support.*;

public class Solution {
    private static final int UNBALANCED = -1;

    public boolean isBalanced(TreeNode root) {
        return checkedHeight(root) != UNBALANCED;
    }

    /** Height of {@code node}, or UNBALANCED as soon as any subtree below it is unbalanced. */
    private static int checkedHeight(TreeNode node) {
        if (node == null) {
            return 0;
        }
        int left = checkedHeight(node.left);
        if (left == UNBALANCED) {
            return UNBALANCED;
        }
        int right = checkedHeight(node.right);
        if (right == UNBALANCED || Math.abs(left - right) > 1) {
            return UNBALANCED;
        }
        return 1 + Math.max(left, right);
    }
}
