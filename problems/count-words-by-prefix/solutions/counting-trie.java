public class Solution {
    private static final class Node {
        final Node[] children = new Node[26];
        int passing; // how many words go through this node
    }

    public int[] countByPrefix(String[] words, String[] prefixes) {
        Node root = new Node();
        for (String word : words) {
            Node node = root;
            for (int i = 0; i < word.length(); i++) {
                int slot = word.charAt(i) - 'a';
                if (node.children[slot] == null) {
                    node.children[slot] = new Node();
                }
                node = node.children[slot];
                node.passing++;
            }
        }

        int[] counts = new int[prefixes.length];
        for (int i = 0; i < prefixes.length; i++) {
            Node node = root;
            for (int j = 0; j < prefixes[i].length() && node != null; j++) {
                node = node.children[prefixes[i].charAt(j) - 'a'];
            }
            // A broken path leaves null: no word begins with this prefix.
            counts[i] = node == null ? 0 : node.passing;
        }
        return counts;
    }
}
