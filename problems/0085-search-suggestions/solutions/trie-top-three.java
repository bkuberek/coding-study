import java.util.*;

public class Solution {
    private static final int SHOWN = 3;

    private static final class Node {
        final Node[] children = new Node[26];
        final List<String> smallest = new ArrayList<>(SHOWN);
    }

    public List<List<String>> suggestedProducts(String[] products, String searchWord) {
        String[] ordered = products.clone();
        Arrays.sort(ordered);
        Node root = new Node();
        // Inserting in sorted order means each node's first three products are its smallest.
        for (String product : ordered) {
            Node node = root;
            for (int i = 0; i < product.length(); i++) {
                int index = product.charAt(i) - 'a';
                if (node.children[index] == null) {
                    node.children[index] = new Node();
                }
                node = node.children[index];
                if (node.smallest.size() < SHOWN) {
                    node.smallest.add(product);
                }
            }
        }
        List<List<String>> suggestions = new ArrayList<>();
        Node node = root;
        for (int i = 0; i < searchWord.length(); i++) {
            node = node == null ? null : node.children[searchWord.charAt(i) - 'a'];
            suggestions.add(node == null ? new ArrayList<>() : new ArrayList<>(node.smallest));
        }
        return suggestions;
    }
}
