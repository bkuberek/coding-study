import cs.support.*;
import java.util.*;

public class Solution {
    public TreeNode lowestCommonAncestor(TreeNode root, TreeNode p, TreeNode q) {
        // TreeNode keeps Object's identity equals and hashCode, so nodes work as map keys.
        Map<TreeNode, TreeNode> parent = new HashMap<>();
        parent.put(root, null);
        Deque<TreeNode> pending = new ArrayDeque<>();
        pending.push(root);
        while (!parent.containsKey(p) || !parent.containsKey(q)) {
            TreeNode node = pending.pop();
            if (node.left != null) {
                parent.put(node.left, node);
                pending.push(node.left);
            }
            if (node.right != null) {
                parent.put(node.right, node);
                pending.push(node.right);
            }
        }
        Set<TreeNode> ancestorsOfP = new HashSet<>();
        for (TreeNode node = p; node != null; node = parent.get(node)) {
            ancestorsOfP.add(node);
        }
        TreeNode node = q;
        while (!ancestorsOfP.contains(node)) {
            node = parent.get(node);
        }
        return node;
    }
}
