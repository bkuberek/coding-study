import java.util.*;

public class Solution {
    private static final String START = "JFK";

    public List<String> findItinerary(String[][] tickets) {
        // A min-heap of destinations per airport: poll() always takes the smallest unused one.
        Map<String, PriorityQueue<String>> destinations = new HashMap<>();
        for (String[] ticket : tickets) {
            destinations.computeIfAbsent(ticket[0], key -> new PriorityQueue<>()).add(ticket[1]);
        }
        LinkedList<String> route = new LinkedList<>();
        Deque<String> stack = new ArrayDeque<>();
        stack.push(START);
        while (!stack.isEmpty()) {
            PriorityQueue<String> targets = destinations.get(stack.peek());
            if (targets != null && !targets.isEmpty()) {
                stack.push(targets.poll());
            } else {
                // Stuck: this airport comes last among what is left, so it joins the route now.
                route.addFirst(stack.pop());
            }
        }
        return route;
    }
}
