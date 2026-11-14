import cs.support.*;

public class Solution {
    private static final String MISSING = "#";
    private static final String SEPARATOR = ",";

    public TreeNode serializeDeserialize(TreeNode root) {
        return deserialize(serialize(root));
    }

    static String serialize(TreeNode root) {
        StringBuilder out = new StringBuilder();
        write(root, out);
        return out.toString();
    }

    private static void write(TreeNode node, StringBuilder out) {
        if (out.length() > 0) {
            out.append(SEPARATOR);
        }
        if (node == null) {
            out.append(MISSING);
            return;
        }
        out.append(node.val);
        write(node.left, out);
        write(node.right, out);
    }

    static TreeNode deserialize(String data) {
        return new Reader(data.split(SEPARATOR)).read();
    }

    /** Hands out the tokens of one string in order, rebuilding the tree in pre-order. */
    private static final class Reader {
        private final String[] tokens;
        private int next;

        Reader(String[] tokens) {
            this.tokens = tokens;
        }

        TreeNode read() {
            String token = tokens[next++];
            if (token.equals(MISSING)) {
                return null;
            }
            TreeNode node = new TreeNode(Integer.parseInt(token));
            node.left = read();
            node.right = read();
            return node;
        }
    }
}
