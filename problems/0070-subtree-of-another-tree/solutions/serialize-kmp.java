import cs.support.*;
import java.util.*;

public class Solution {
    // Values lie in [-10^4, 10^4], so this marker for a missing child never equals a value.
    private static final int NO_NODE = Integer.MIN_VALUE;
    // ArrayDeque rejects null, so a missing child is pushed as this placeholder node.
    private static final TreeNode MISSING = new TreeNode();

    public boolean isSubtree(TreeNode root, TreeNode subRoot) {
        return occurs(tokens(subRoot), tokens(root));
    }

    /** Pre-order values with NO_NODE for every missing child: a unique description of the tree. */
    private static int[] tokens(TreeNode root) {
        List<Integer> out = new ArrayList<>();
        Deque<TreeNode> pending = new ArrayDeque<>();
        pending.push(orMissing(root));
        while (!pending.isEmpty()) {
            TreeNode node = pending.pop();
            if (node == MISSING) {
                out.add(NO_NODE);
                continue;
            }
            out.add(node.val);
            pending.push(orMissing(node.right));
            pending.push(orMissing(node.left));
        }
        return out.stream().mapToInt(Integer::intValue).toArray();
    }

    private static TreeNode orMissing(TreeNode node) {
        return node == null ? MISSING : node;
    }

    /** Knuth-Morris-Pratt: does {@code pattern} occur as a contiguous block of {@code text}? */
    private static boolean occurs(int[] pattern, int[] text) {
        int[] border = new int[pattern.length];
        int length = 0;
        for (int i = 1; i < pattern.length; i++) {
            while (length > 0 && pattern[i] != pattern[length]) {
                length = border[length - 1];
            }
            if (pattern[i] == pattern[length]) {
                length++;
            }
            border[i] = length;
        }
        int matched = 0;
        for (int token : text) {
            while (matched > 0 && token != pattern[matched]) {
                matched = border[matched - 1];
            }
            if (token == pattern[matched]) {
                matched++;
                if (matched == pattern.length) {
                    return true;
                }
            }
        }
        return false;
    }
}
