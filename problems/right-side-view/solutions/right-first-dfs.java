import cs.support.*;
import java.util.*;

public class Solution {
    public List<Integer> rightSideView(TreeNode root) {
        List<Integer> view = new ArrayList<>();
        visit(root, 0, view);
        return view;
    }

    private static void visit(TreeNode node, int depth, List<Integer> view) {
        if (node == null) {
            return;
        }
        if (depth == view.size()) {
            view.add(node.val);
        }
        visit(node.right, depth + 1, view);
        visit(node.left, depth + 1, view);
    }
}
