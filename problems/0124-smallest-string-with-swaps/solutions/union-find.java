import java.util.*;

public class Solution {
    private static final class DisjointSets {
        private final int[] parent;
        private final int[] size; // size[r]: number of positions in the tree rooted at r

        DisjointSets(int count) {
            parent = new int[count];
            size = new int[count];
            for (int x = 0; x < count; x++) {
                parent[x] = x;
                size[x] = 1;
            }
        }

        int find(int x) {
            int root = x;
            while (parent[root] != root) {
                root = parent[root];
            }
            while (parent[x] != root) { // path compression: point the whole path at the root
                int next = parent[x];
                parent[x] = root;
                x = next;
            }
            return root;
        }

        void union(int a, int b) {
            int rootA = find(a);
            int rootB = find(b);
            if (rootA == rootB) {
                return;
            }
            if (size[rootA] < size[rootB]) {
                int held = rootA;
                rootA = rootB;
                rootB = held;
            }
            parent[rootB] = rootA; // union by size: the smaller tree goes under the larger
            size[rootA] += size[rootB];
        }
    }

    public String smallestStringWithSwaps(String s, int[][] pairs) {
        DisjointSets sets = new DisjointSets(s.length());
        for (int[] pair : pairs) {
            sets.union(pair[0], pair[1]);
        }
        // Positions are added in increasing order, so each group's list is sorted.
        Map<Integer, List<Integer>> groups = new HashMap<>();
        for (int position = 0; position < s.length(); position++) {
            groups.computeIfAbsent(sets.find(position), unused -> new ArrayList<>()).add(position);
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
}
