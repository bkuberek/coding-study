import java.util.*;

public class Solution {
    public double[] calcEquation(String[][] equations, double[] values, String[][] queries) {
        // graph.get(a).get(b) is the value of a / b, stored in both directions.
        Map<String, Map<String, Double>> graph = new HashMap<>();
        for (int i = 0; i < equations.length; i++) {
            String a = equations[i][0];
            String b = equations[i][1];
            graph.computeIfAbsent(a, key -> new HashMap<>()).put(b, values[i]);
            graph.computeIfAbsent(b, key -> new HashMap<>()).put(a, 1.0 / values[i]);
        }
        double[] answers = new double[queries.length];
        for (int j = 0; j < queries.length; j++) {
            answers[j] = ratio(graph, queries[j][0], queries[j][1]);
        }
        return answers;
    }

    private double ratio(Map<String, Map<String, Double>> graph, String source, String target) {
        if (!graph.containsKey(source) || !graph.containsKey(target)) {
            return -1.0;
        }
        // product.get(x) is the value of source / x along the path that reached x.
        Map<String, Double> product = new HashMap<>();
        product.put(source, 1.0);
        Queue<String> queue = new ArrayDeque<>();
        queue.add(source);
        while (!queue.isEmpty()) {
            String node = queue.poll();
            if (node.equals(target)) {
                return product.get(node);
            }
            for (Map.Entry<String, Double> edge : graph.get(node).entrySet()) {
                if (!product.containsKey(edge.getKey())) {
                    product.put(edge.getKey(), product.get(node) * edge.getValue());
                    queue.add(edge.getKey());
                }
            }
        }
        return -1.0;
    }
}
