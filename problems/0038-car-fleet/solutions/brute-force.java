import java.util.*;

public class Solution {
    public int carFleet(int target, int[] position, int[] speed) {
        int fleets = 0;
        for (int car = 0; car < position.length; car++) {
            int slowest = -1;
            for (int other = 0; other < position.length; other++) {
                if (position[other] > position[car]
                        && (slowest < 0 || arrivesLater(target, position, speed, other, slowest))) {
                    slowest = other;
                }
            }
            // The car leads its own fleet only if it arrives strictly later than the slowest car ahead.
            if (slowest < 0 || arrivesLater(target, position, speed, car, slowest)) {
                fleets++;
            }
        }
        return fleets;
    }

    // Arrival times are distance / speed; compare them by cross-multiplying, so no division.
    // Each product is at most 10^6 * 1000, which fits in an int.
    private static boolean arrivesLater(int target, int[] position, int[] speed, int a, int b) {
        return (target - position[a]) * speed[b] > (target - position[b]) * speed[a];
    }
}
