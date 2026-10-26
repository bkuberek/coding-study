import java.util.*;

public class Solution {
    public int countComponents(int n, int[][] edges) {
        List<List<Integer>> neighbors = new ArrayList<>(n);
        for (int node = 0; node < n; node++) {
            neighbors.add(new ArrayList<>());
        }
        for (int[] edge : edges) {
            neighbors.get(edge[0]).add(edge[1]);
            neighbors.get(edge[1]).add(edge[0]);
        }
        boolean[] seen = new boolean[n];
        int components = 0;
        ArrayDeque<Integer> stack = new ArrayDeque<>(); // an explicit stack avoids deep recursion
        for (int start = 0; start < n; start++) {
            if (seen[start]) {
                continue;
            }
            components++;
            seen[start] = true;
            stack.push(start);
            while (!stack.isEmpty()) {
                int node = stack.pop();
                for (int neighbor : neighbors.get(node)) {
                    if (!seen[neighbor]) {
                        seen[neighbor] = true;
                        stack.push(neighbor);
                    }
                }
            }
        }
        return components;
    }
}
