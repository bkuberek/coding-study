import cs.support.*;

public class Solution {
    public TreeNode invertTree(TreeNode root) {
        if (root == null) {
            return null;
        }
        TreeNode invertedLeft = invertTree(root.left);
        root.left = invertTree(root.right);
        root.right = invertedLeft;
        return root;
    }
}
