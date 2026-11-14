import cs.support.*;
import java.util.*;

public class Solution {
    private int[] preorder;
    private Map<Integer, Integer> position;
    private int nextRoot;

    public TreeNode buildTree(int[] preorder, int[] inorder) {
        this.preorder = preorder;
        this.position = new HashMap<>(inorder.length * 2);
        for (int i = 0; i < inorder.length; i++) {
            position.put(inorder[i], i);
        }
        this.nextRoot = 0;
        return build(0, inorder.length);
    }

    /** Tree whose in-order walk is inorder[low, high); its root is the next pre-order value. */
    private TreeNode build(int low, int high) {
        if (low == high) {
            return null;
        }
        int value = preorder[nextRoot++];
        int split = position.get(value);
        TreeNode node = new TreeNode(value);
        node.left = build(low, split);
        node.right = build(split + 1, high);
        return node;
    }
}
