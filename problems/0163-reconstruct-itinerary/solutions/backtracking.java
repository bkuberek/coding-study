import java.util.*;

public class Solution {
    private static final String START = "JFK";

    private final Map<String, List<String>> destinations = new HashMap<>();
    private final Map<String, boolean[]> used = new HashMap<>();
    private final List<String> route = new ArrayList<>();
    private int ticketCount;

    public List<String> findItinerary(String[][] tickets) {
        destinations.clear();
        used.clear();
        route.clear();
        ticketCount = tickets.length;
        // Destinations per airport in increasing order, with a used flag per ticket.
        for (String[] ticket : tickets) {
            destinations.computeIfAbsent(ticket[0], key -> new ArrayList<>()).add(ticket[1]);
        }
        for (Map.Entry<String, List<String>> entry : destinations.entrySet()) {
            Collections.sort(entry.getValue());
            used.put(entry.getKey(), new boolean[entry.getValue().size()]);
        }
        route.add(START);
        extend(START);
        return new ArrayList<>(route);
    }

    /** Tries to complete the route from airport; on failure, leaves the route unchanged. */
    private boolean extend(String airport) {
        if (route.size() == ticketCount + 1) {
            return true;
        }
        List<String> targets = destinations.getOrDefault(airport, List.of());
        boolean[] flags = used.get(airport);
        for (int i = 0; i < targets.size(); i++) {
            if (flags[i]) {
                continue;
            }
            // An identical ticket was just tried from this same position and failed.
            if (i > 0 && targets.get(i).equals(targets.get(i - 1)) && !flags[i - 1]) {
                continue;
            }
            flags[i] = true;
            route.add(targets.get(i));
            if (extend(targets.get(i))) {
                return true;
            }
            route.remove(route.size() - 1);
            flags[i] = false;
        }
        return false;
    }
}
