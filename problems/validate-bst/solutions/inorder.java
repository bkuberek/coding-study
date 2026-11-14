import cs.support.*;
import java.util.*;

public class Solution {
    public boolean isValidBST(TreeNode root) {
        Deque<TreeNode> stack = new ArrayDeque<>();
        TreeNode node = root;
        // Below every int, so the first value always passes.
        long previous = Long.MIN_VALUE;
        while (!stack.isEmpty() || node != null) {
            while (node != null) {
                stack.push(node);
                node = node.left;
            }
            node = stack.pop();
            if (node.val <= previous) {
                return false;
            }
            previous = node.val;
            node = node.right;
        }
        return true;
    }
}
