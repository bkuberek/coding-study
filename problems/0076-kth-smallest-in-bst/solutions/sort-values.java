import cs.support.*;
import java.util.*;

public class Solution {
    public int kthSmallest(TreeNode root, int k) {
        int[] values = new int[count(root)];
        int size = 0;
        Deque<TreeNode> pending = new ArrayDeque<>();
        pending.push(root);
        while (!pending.isEmpty()) {
            TreeNode node = pending.pop();
            values[size++] = node.val;
            if (node.left != null) {
                pending.push(node.left);
            }
            if (node.right != null) {
                pending.push(node.right);
            }
        }
        Arrays.sort(values);
        return values[k - 1];
    }

    private static int count(TreeNode root) {
        int nodes = 0;
        Deque<TreeNode> pending = new ArrayDeque<>();
        pending.push(root);
        while (!pending.isEmpty()) {
            TreeNode node = pending.pop();
            nodes++;
            if (node.left != null) {
                pending.push(node.left);
            }
            if (node.right != null) {
                pending.push(node.right);
            }
        }
        return nodes;
    }
}
