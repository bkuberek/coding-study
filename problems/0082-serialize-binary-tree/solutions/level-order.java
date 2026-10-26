import cs.support.*;
import java.util.*;

public class Solution {
    private static final String MISSING = "#";
    private static final String SEPARATOR = ",";

    public TreeNode serializeDeserialize(TreeNode root) {
        return deserialize(serialize(root));
    }

    static String serialize(TreeNode root) {
        StringJoiner out = new StringJoiner(SEPARATOR);
        // ArrayDeque rejects null, so missing children are written out instead of queued.
        Deque<TreeNode> queue = new ArrayDeque<>();
        if (root == null) {
            out.add(MISSING);
        } else {
            out.add(String.valueOf(root.val));
            queue.add(root);
        }
        while (!queue.isEmpty()) {
            TreeNode node = queue.poll();
            for (TreeNode child : new TreeNode[] {node.left, node.right}) {
                if (child == null) {
                    out.add(MISSING);
                } else {
                    out.add(String.valueOf(child.val));
                    queue.add(child);
                }
            }
        }
        return out.toString();
    }

    static TreeNode deserialize(String data) {
        String[] tokens = data.split(SEPARATOR);
        if (tokens[0].equals(MISSING)) {
            return null;
        }
        TreeNode root = new TreeNode(Integer.parseInt(tokens[0]));
        Deque<TreeNode> queue = new ArrayDeque<>();
        queue.add(root);
        int position = 1;
        // Every node was written with exactly two child tokens, in queue order.
        while (!queue.isEmpty()) {
            TreeNode node = queue.poll();
            String left = tokens[position++];
            String right = tokens[position++];
            if (!left.equals(MISSING)) {
                node.left = new TreeNode(Integer.parseInt(left));
                queue.add(node.left);
            }
            if (!right.equals(MISSING)) {
                node.right = new TreeNode(Integer.parseInt(right));
                queue.add(node.right);
            }
        }
        return root;
    }
}
