import cs.support.*;
import java.util.*;

public class Solution {
    public List<List<Integer>> verticalOrder(TreeNode root) {
        List<List<Integer>> result = new ArrayList<>();
        if (root == null) {
            return result;
        }
        Map<Integer, List<Integer>> columns = new HashMap<>();
        Deque<TreeNode> nodes = new ArrayDeque<>();
        Deque<Integer> columnOf = new ArrayDeque<>();
        nodes.add(root);
        columnOf.add(0);
        int leftmost = 0;
        int rightmost = 0;
        while (!nodes.isEmpty()) {
            TreeNode node = nodes.poll();
            int column = columnOf.poll();
            columns.computeIfAbsent(column, key -> new ArrayList<>()).add(node.val);
            leftmost = Math.min(leftmost, column);
            rightmost = Math.max(rightmost, column);
            if (node.left != null) {
                nodes.add(node.left);
                columnOf.add(column - 1);
            }
            if (node.right != null) {
                nodes.add(node.right);
                columnOf.add(column + 1);
            }
        }
        // Columns form a contiguous range: every path from the root moves one column per step.
        for (int column = leftmost; column <= rightmost; column++) {
            result.add(columns.get(column));
        }
        return result;
    }
}
