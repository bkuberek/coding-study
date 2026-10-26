public class WordDictionary {
    private static final class Node {
        final Node[] children = new Node[26];
        boolean isWord;
    }

    private final Node root = new Node();

    public WordDictionary() {
    }

    public void addWord(String word) {
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
        return matchesFrom(root, word, 0);
    }

    /** Does some stored word continue from {@code node} the way word[position..] says? */
    private static boolean matchesFrom(Node node, String word, int position) {
        for (int at = position; at < word.length(); at++) {
            char wanted = word.charAt(at);
            if (wanted == '.') {
                for (Node child : node.children) {
                    if (child != null && matchesFrom(child, word, at + 1)) {
                        return true;
                    }
                }
                return false;
            }
            node = node.children[wanted - 'a'];
            if (node == null) {
                return false;
            }
        }
        return node.isWord;
    }
}
