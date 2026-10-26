import cs.support.*;

public class Solution {
    public boolean isValidBST(TreeNode root) {
        if (root == null) {
            return true;
        }
        if (root.left != null && largest(root.left) >= root.val) {
            return false;
        }
        if (root.right != null && smallest(root.right) <= root.val) {
            return false;
        }
        return isValidBST(root.left) && isValidBST(root.right);
    }

    /** Largest value anywhere in the subtree; it need not be a search tree, so scan it all. */
    private static int largest(TreeNode node) {
        int best = node.val;
        if (node.left != null) {
            best = Math.max(best, largest(node.left));
        }
        if (node.right != null) {
            best = Math.max(best, largest(node.right));
        }
        return best;
    }

    private static int smallest(TreeNode node) {
        int best = node.val;
        if (node.left != null) {
            best = Math.min(best, smallest(node.left));
        }
        if (node.right != null) {
            best = Math.min(best, smallest(node.right));
        }
        return best;
    }
}
