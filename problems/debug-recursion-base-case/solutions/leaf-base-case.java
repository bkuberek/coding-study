import cs.support.*;

public class Solution {
    public boolean hasPathSum(TreeNode root, int target) {
        if (root == null) {
            return false;
        }
        int remaining = target - root.val;
        if (root.left == null && root.right == null) {
            return remaining == 0;
        }
        return hasPathSum(root.left, remaining) || hasPathSum(root.right, remaining);
    }
}
