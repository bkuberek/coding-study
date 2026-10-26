import cs.support.*;
import java.util.*;

public class Solution {
    // onPath maps a prefix sum of the current root path to how many prefixes have it.
    private final Map<Integer, Integer> onPath = new HashMap<>();
    private int targetSum;

    public int pathSum(TreeNode root, int targetSum) {
        this.targetSum = targetSum;
        onPath.clear();
        onPath.put(0, 1);
        return countBelow(root, 0);
    }

    private int countBelow(TreeNode node, int total) {
        if (node == null) {
            return 0;
        }
        total += node.val;
        int found = onPath.getOrDefault(total - targetSum, 0);
        onPath.merge(total, 1, Integer::sum);
        found += countBelow(node.left, total) + countBelow(node.right, total);
        onPath.merge(total, -1, Integer::sum); // leave the subtree
        return found;
    }
}
