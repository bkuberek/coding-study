import java.util.*;

public class Solution {
    private static final class DisjointSet {
        private final int[] parent;
        private final int[] size;

        DisjointSet(int count) {
            parent = new int[count];
            size = new int[count];
            for (int i = 0; i < count; i++) {
                parent[i] = i;
                size[i] = 1;
            }
        }

        int find(int node) {
            int root = node;
            while (parent[root] != root) {
                root = parent[root];
            }
            while (parent[node] != root) {
                int next = parent[node];
                parent[node] = root;
                node = next;
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
                int swap = rootA;
                rootA = rootB;
                rootB = swap;
            }
            parent[rootB] = rootA;
            size[rootA] += size[rootB];
        }
    }

    public boolean isBipartite(int[][] graph) {
        DisjointSet teams = new DisjointSet(graph.length);
        // All neighbors of a node must share a team, so they go into one group.
        for (int[] neighbors : graph) {
            for (int neighbor : neighbors) {
                teams.union(neighbors[0], neighbor);
            }
        }
        // A split exists exactly when no edge has both ends in one group.
        for (int node = 0; node < graph.length; node++) {
            for (int neighbor : graph[node]) {
                if (teams.find(node) == teams.find(neighbor)) {
                    return false;
                }
            }
        }
        return true;
    }
}
