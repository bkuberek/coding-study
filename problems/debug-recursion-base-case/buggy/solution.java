// Debug: Recursion Base Case. Some tests fail: find the bug and fix it.
import cs.support.*;

public class Solution {
    public boolean hasPathSum(TreeNode root, int target) {
        if (root == null) {
            return target == 0;
        }
        int remaining = target - root.val;
        return hasPathSum(root.left, remaining) || hasPathSum(root.right, remaining);
    }
}
