import java.util.*;

public class Solution {
    private static final class TrieNode {
        final TrieNode[] children = new TrieNode[26];
        boolean endsWord;
    }

    public boolean wordBreak(String s, String[] wordDict) {
        TrieNode root = new TrieNode();
        for (String word : wordDict) {
            TrieNode node = root;
            for (char letter : word.toCharArray()) {
                int index = letter - 'a';
                if (node.children[index] == null) {
                    node.children[index] = new TrieNode();
                }
                node = node.children[index];
            }
            node.endsWord = true;
        }

        // reachable[i] is true when the prefix s[0..i) can be split into dictionary words.
        boolean[] reachable = new boolean[s.length() + 1];
        reachable[0] = true;
        for (int start = 0; start < s.length(); start++) {
            if (!reachable[start]) {
                continue;
            }
            TrieNode node = root;
            for (int position = start; position < s.length(); position++) {
                node = node.children[s.charAt(position) - 'a'];
                if (node == null) {
                    break;
                }
                if (node.endsWord) {
                    reachable[position + 1] = true;
                }
            }
        }
        return reachable[s.length()];
    }
}
