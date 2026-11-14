import java.util.*;

public class Solution {
    public String smallestStringWithSwaps(String s, int[][] pairs) {
        int[] parent = new int[s.length()]; // parent[x] == x marks a root
        for (int x = 0; x < parent.length; x++) {
            parent[x] = x;
        }
        for (int[] pair : pairs) {
            int rootA = find(parent, pair[0]);
            int rootB = find(parent, pair[1]);
            if (rootA != rootB) {
                parent[rootA] = rootB; // no balancing: trees can grow into long chains
            }
        }
        // Positions are added in increasing order, so each group's list is sorted.
        Map<Integer, List<Integer>> groups = new HashMap<>();
        for (int position = 0; position < s.length(); position++) {
            groups.computeIfAbsent(find(parent, position), unused -> new ArrayList<>()).add(position);
        }
        char[] letters = s.toCharArray();
        for (List<Integer> positions : groups.values()) {
            char[] sorted = new char[positions.size()];
            for (int k = 0; k < sorted.length; k++) {
                sorted[k] = s.charAt(positions.get(k));
            }
            Arrays.sort(sorted);
            for (int k = 0; k < sorted.length; k++) {
                letters[positions.get(k)] = sorted[k];
            }
        }
        return new String(letters);
    }

    private static int find(int[] parent, int x) {
        while (parent[x] != x) {
            x = parent[x];
        }
        return x;
    }
}
