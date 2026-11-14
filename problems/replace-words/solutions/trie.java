import java.util.*;

public class Solution {
    private static final class TrieNode {
        final TrieNode[] children = new TrieNode[26];
        boolean end; // a root ends at this node
    }

    public String replaceWords(String[] dictionary, String sentence) {
        TrieNode trie = new TrieNode();
        for (String root : dictionary) {
            TrieNode node = trie;
            for (char letter : root.toCharArray()) {
                int index = letter - 'a';
                if (node.children[index] == null) {
                    node.children[index] = new TrieNode();
                }
                node = node.children[index];
            }
            node.end = true;
        }
        StringBuilder result = new StringBuilder();
        for (String word : sentence.split(" ")) {
            if (result.length() > 0) {
                result.append(' ');
            }
            result.append(shorten(trie, word));
        }
        return result.toString();
    }

    private static String shorten(TrieNode trie, String word) {
        TrieNode node = trie;
        for (int length = 0; length < word.length(); length++) {
            if (node.end) {
                return word.substring(0, length);
            }
            node = node.children[word.charAt(length) - 'a'];
            if (node == null) {
                return word;
            }
        }
        return word;
    }
}
