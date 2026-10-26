import cs.support.*;
import java.util.*;

public class Solution {
    public int kthSmallest(TreeNode root, int k) {
        Deque<TreeNode> stack = new ArrayDeque<>();
        TreeNode node = root;
        int remaining = k;
        while (true) {
            while (node != null) {
                stack.push(node);
                node = node.left;
            }
            node = stack.pop();
            if (--remaining == 0) {
                return node.val;
            }
            node = node.right;
        }
    }
}
