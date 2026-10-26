public class Solution {
    public boolean carPooling(int[][] trips, int capacity) {
        // The load is highest right after some pickup, so checking every pickup point suffices.
        int busiest = 0;
        for (int[] booking : trips) {
            int pickup = booking[1];
            int load = 0;
            for (int[] trip : trips) {
                if (trip[1] <= pickup && pickup < trip[2]) {
                    load += trip[0];
                }
            }
            busiest = Math.max(busiest, load);
        }
        return busiest <= capacity;
    }
}
