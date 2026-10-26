import java.util.*;

public class Solution {
    // parent.get(x) is x's parent; weight.get(x) is the value of x / parent(x).
    private final Map<String, String> parent = new HashMap<>();
    private final Map<String, Double> weight = new HashMap<>();

    public double[] calcEquation(String[][] equations, double[] values, String[][] queries) {
        parent.clear();
        weight.clear();
        for (int i = 0; i < equations.length; i++) {
            String a = equations[i][0];
            String b = equations[i][1];
            for (String name : equations[i]) {
                if (!parent.containsKey(name)) {
                    parent.put(name, name);
                    weight.put(name, 1.0);
                }
            }
            String rootA = find(a);
            String rootB = find(b);
            if (!rootA.equals(rootB)) {
                // Hang rootA under rootB: rootA / rootB = (a / b) * (b / rootB) / (a / rootA).
                parent.put(rootA, rootB);
                weight.put(rootA, values[i] * weight.get(b) / weight.get(a));
            }
        }
        double[] answers = new double[queries.length];
        for (int j = 0; j < queries.length; j++) {
            String c = queries[j][0];
            String d = queries[j][1];
            if (!parent.containsKey(c) || !parent.containsKey(d) || !find(c).equals(find(d))) {
                answers[j] = -1.0;
            } else {
                answers[j] = weight.get(c) / weight.get(d);
            }
        }
        return answers;
    }

    /** Returns the root of name; afterwards parent(name) is the root and weight(name) is name / root. */
    private String find(String name) {
        List<String> path = new ArrayList<>();
        String node = name;
        while (!parent.get(node).equals(node)) {
            path.add(node);
            node = parent.get(node);
        }
        String root = node;
        for (int i = path.size() - 1; i >= 0; i--) {
            String current = path.get(i);
            String up = parent.get(current);
            if (!up.equals(root)) {
                weight.put(current, weight.get(current) * weight.get(up));
                parent.put(current, root);
            }
        }
        return root;
    }
}
