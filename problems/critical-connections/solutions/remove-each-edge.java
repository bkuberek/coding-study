import java.util.*;

public class Solution {
    public List<List<Integer>> criticalConnections(int n, int[][] connections) {
        List<List<int[]>> adjacency = new ArrayList<>();
        for (int server = 0; server < n; server++) {
            adjacency.add(new ArrayList<>());
        }
        for (int index = 0; index < connections.length; index++) {
            int a = connections[index][0];
            int b = connections[index][1];
            adjacency.get(a).add(new int[] {b, index});
            adjacency.get(b).add(new int[] {a, index});
        }
        List<List<Integer>> critical = new ArrayList<>();
        for (int index = 0; index < connections.length; index++) {
            if (!connectedWithout(adjacency, index)) {
                critical.add(List.of(connections[index][0], connections[index][1]));
            }
        }
        return critical;
    }

    /** Can every server still be reached from server 0 when cable {@code skipped} is cut? */
    private boolean connectedWithout(List<List<int[]>> adjacency, int skipped) {
        int n = adjacency.size();
        boolean[] seen = new boolean[n];
        seen[0] = true;
        Deque<Integer> stack = new ArrayDeque<>();
        stack.push(0);
        int reached = 1;
        while (!stack.isEmpty()) {
            for (int[] edge : adjacency.get(stack.pop())) {
                if (edge[1] != skipped && !seen[edge[0]]) {
                    seen[edge[0]] = true;
                    reached++;
                    stack.push(edge[0]);
                }
            }
        }
        return reached == n;
    }
}
