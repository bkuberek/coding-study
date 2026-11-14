import cs.support.*;
import java.util.*;

public class Solution {
    public List<Integer> rightSideView(TreeNode root) {
        List<Integer> view = new ArrayList<>();
        Deque<TreeNode> queue = new ArrayDeque<>();
        if (root != null) {
            queue.add(root);
        }
        while (!queue.isEmpty()) {
            // The node at the back of the queue is the last one of the current level.
            view.add(queue.peekLast().val);
            for (int remaining = queue.size(); remaining > 0; remaining--) {
                TreeNode node = queue.poll();
                if (node.left != null) {
                    queue.add(node.left);
                }
                if (node.right != null) {
                    queue.add(node.right);
                }
            }
        }
        return view;
    }
}
