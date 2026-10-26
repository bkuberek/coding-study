import cs.support.*;
import java.util.*;

public class Solution {
    public List<List<Integer>> levelOrder(TreeNode root) {
        List<List<Integer>> levels = new ArrayList<>();
        visit(root, 0, levels);
        return levels;
    }

    private static void visit(TreeNode node, int depth, List<List<Integer>> levels) {
        if (node == null) {
            return;
        }
        if (depth == levels.size()) {
            levels.add(new ArrayList<>());
        }
        levels.get(depth).add(node.val);
        visit(node.left, depth + 1, levels);
        visit(node.right, depth + 1, levels);
    }
}
