public class Trie {
    private static final class Node {
        final Node[] children = new Node[26];
        boolean isWord;
    }

    private final Node root = new Node();

    public Trie() {
    }

    public void insert(String word) {
        Node node = root;
        for (int i = 0; i < word.length(); i++) {
            int index = word.charAt(i) - 'a';
            if (node.children[index] == null) {
                node.children[index] = new Node();
            }
            node = node.children[index];
        }
        node.isWord = true;
    }

    public boolean search(String word) {
        Node node = walk(word);
        return node != null && node.isWord;
    }

    public boolean startsWith(String prefix) {
        return walk(prefix) != null;
    }

    /** The node at the end of the path spelled by {@code text}, or null if the path breaks off. */
    private Node walk(String text) {
        Node node = root;
        for (int i = 0; i < text.length() && node != null; i++) {
            node = node.children[text.charAt(i) - 'a'];
        }
        return node;
    }
}
