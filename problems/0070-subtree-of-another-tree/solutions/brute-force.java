import cs.support.*;

public class Solution {
    public boolean isSubtree(TreeNode root, TreeNode subRoot) {
        if (root == null) {
            return false;
        }
        return same(root, subRoot) || isSubtree(root.left, subRoot) || isSubtree(root.right, subRoot);
    }

    private static boolean same(TreeNode a, TreeNode b) {
        if (a == null || b == null) {
            return a == b;
        }
        return a.val == b.val && same(a.left, b.left) && same(a.right, b.right);
    }
}
