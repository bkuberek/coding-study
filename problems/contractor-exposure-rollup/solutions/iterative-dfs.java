import java.math.BigDecimal;
import java.util.*;

public class Solution {
    private static final class Frame {
        final String node;
        int next = 0; // index of the next child to look at

        Frame(String node) {
            this.node = node;
        }
    }

    public BigDecimal totalExposure(String[][] edges, String[] contractors, BigDecimal[] exposures, String root) {
        Map<String, List<String>> children = new HashMap<>();
        for (String[] edge : edges) {
            children.computeIfAbsent(edge[0], k -> new ArrayList<>()).add(edge[1]);
        }
        Map<String, BigDecimal> own = new HashMap<>();
        for (int i = 0; i < contractors.length; i++) {
            own.put(contractors[i], exposures[i]);
        }
        Set<String> onPath = new HashSet<>(); // meeting one again closes a cycle
        Set<String> finished = new HashSet<>(); // fully explored contractors, already counted
        onPath.add(root);
        BigDecimal total = own.getOrDefault(root, BigDecimal.ZERO);
        Deque<Frame> stack = new ArrayDeque<>();
        stack.push(new Frame(root));
        while (!stack.isEmpty()) {
            Frame frame = stack.peek();
            List<String> below = children.getOrDefault(frame.node, List.of());
            if (frame.next == below.size()) {
                stack.pop();
                onPath.remove(frame.node);
                finished.add(frame.node);
                continue;
            }
            String child = below.get(frame.next++);
            if (onPath.contains(child)) {
                return BigDecimal.ONE.negate();
            }
            if (!finished.contains(child)) {
                onPath.add(child);
                total = total.add(own.getOrDefault(child, BigDecimal.ZERO));
                stack.push(new Frame(child));
            }
        }
        return total;
    }
}
