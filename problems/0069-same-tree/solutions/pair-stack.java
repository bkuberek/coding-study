import cs.support.*;
import java.util.*;

public class Solution {
    public boolean isSameTree(TreeNode p, TreeNode q) {
        if (!sameNode(p, q)) {
            return false;
        }
        // ArrayDeque rejects nulls, so only pairs of two real, already matching nodes are pushed.
        Deque<TreeNode[]> pending = new ArrayDeque<>();
        if (p != null) {
            pending.push(new TreeNode[] {p, q});
        }
        while (!pending.isEmpty()) {
            TreeNode[] pair = pending.pop();
            TreeNode a = pair[0];
            TreeNode b = pair[1];
            if (!sameNode(a.left, b.left) || !sameNode(a.right, b.right)) {
                return false;
            }
            if (a.left != null) {
                pending.push(new TreeNode[] {a.left, b.left});
            }
            if (a.right != null) {
                pending.push(new TreeNode[] {a.right, b.right});
            }
        }
        return true;
    }

    private static boolean sameNode(TreeNode a, TreeNode b) {
        if (a == null || b == null) {
            return a == b;
        }
        return a.val == b.val;
    }
}
