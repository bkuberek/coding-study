import cs.support.*;

public class Solution {
    public boolean isValidBST(TreeNode root) {
        // long bounds lie outside the int range, so they never collide with a real value.
        return within(root, Long.MIN_VALUE, Long.MAX_VALUE);
    }

    /** Is every value of the subtree strictly between {@code low} and {@code high}? */
    private static boolean within(TreeNode node, long low, long high) {
        if (node == null) {
            return true;
        }
        if (node.val <= low || node.val >= high) {
            return false;
        }
        return within(node.left, low, node.val) && within(node.right, node.val, high);
    }
}
