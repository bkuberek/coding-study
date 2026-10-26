import java.util.*;

public class Solution {
    public boolean carPooling(int[][] trips, int capacity) {
        int[][] events = new int[2 * trips.length][];
        for (int i = 0; i < trips.length; i++) {
            int[] trip = trips[i];
            events[2 * i] = new int[] {trip[1], trip[0]};
            events[2 * i + 1] = new int[] {trip[2], -trip[0]};
        }
        // By location, then by change: drop-offs (negative) come before pickups at the same place.
        Arrays.sort(events, Comparator.<int[]>comparingInt(e -> e[0]).thenComparingInt(e -> e[1]));
        int load = 0;
        for (int[] event : events) {
            load += event[1];
            if (load > capacity) {
                return false;
            }
        }
        return true;
    }
}
