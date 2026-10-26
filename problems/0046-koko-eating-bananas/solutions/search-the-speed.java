import java.util.*;

public class Solution {
    public int minEatingSpeed(int[] piles, int h) {
        // Hours never increase with speed: find the first speed in [1, max(piles)] that fits.
        int low = 1;
        int high = Arrays.stream(piles).max().getAsInt();
        while (low < high) {
            int speed = low + (high - low) / 2;
            if (hoursAt(piles, speed) <= h) {
                high = speed;
            } else {
                low = speed + 1;
            }
        }
        return low;
    }

    private static long hoursAt(int[] piles, int speed) {
        long hours = 0;
        for (int pile : piles) {
            hours += (pile + (long) speed - 1) / speed;
        }
        return hours;
    }
}
