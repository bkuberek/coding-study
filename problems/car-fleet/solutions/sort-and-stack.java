import java.util.*;

public class Solution {
    public int carFleet(int target, int[] position, int[] speed) {
        int cars = position.length;
        Integer[] order = new Integer[cars];
        for (int car = 0; car < cars; car++) {
            order[car] = car;
        }
        Arrays.sort(order, Comparator.comparingInt(car -> position[car]));
        // Fleets formed so far, from the farthest back (bottom) to the closest to the target (top);
        // their arrival times strictly decrease from bottom to top.
        double[] fleets = new double[cars];
        int size = 0;
        for (int car : order) {
            double arrival = (double) (target - position[car]) / speed[car];
            // Every fleet behind this car that would arrive no later catches up with it.
            while (size > 0 && fleets[size - 1] <= arrival) {
                size--;
            }
            fleets[size++] = arrival;
        }
        return size;
    }
}
