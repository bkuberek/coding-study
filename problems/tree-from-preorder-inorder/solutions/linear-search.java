import cs.support.*;

public class Solution {
    public TreeNode buildTree(int[] preorder, int[] inorder) {
        return build(preorder, inorder, 0, 0, preorder.length);
    }

    /** Tree of the {@code size} values starting at preorder[preStart] and inorder[inStart]. */
    private static TreeNode build(int[] preorder, int[] inorder, int preStart, int inStart, int size) {
        if (size == 0) {
            return null;
        }
        int value = preorder[preStart];
        int split = inStart;
        while (inorder[split] != value) {
            split++;
        }
        int leftSize = split - inStart;
        TreeNode node = new TreeNode(value);
        node.left = build(preorder, inorder, preStart + 1, inStart, leftSize);
        node.right = build(preorder, inorder, preStart + 1 + leftSize, split + 1, size - leftSize - 1);
        return node;
    }
}
