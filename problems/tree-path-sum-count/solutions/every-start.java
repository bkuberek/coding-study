import cs.support.*;
import java.util.*;

public class Solution {
    public int pathSum(TreeNode root, int targetSum) {
        int count = 0;
        Deque<TreeNode> starts = new ArrayDeque<>();
        if (root != null) {
            starts.push(root);
        }
        while (!starts.isEmpty()) {
            TreeNode start = starts.pop();
            // Walk every downward path from start, carrying the sum so far.
            Deque<TreeNode> nodes = new ArrayDeque<>();
            Deque<Integer> totals = new ArrayDeque<>();
            nodes.push(start);
            totals.push(start.val);
            while (!nodes.isEmpty()) {
                TreeNode node = nodes.pop();
                int total = totals.pop();
                if (total == targetSum) {
                    count++;
                }
                for (TreeNode child : new TreeNode[] {node.left, node.right}) {
                    if (child != null) {
                        nodes.push(child);
                        totals.push(total + child.val);
                    }
                }
            }
            if (start.left != null) {
                starts.push(start.left);
            }
            if (start.right != null) {
                starts.push(start.right);
            }
        }
        return count;
    }
}
