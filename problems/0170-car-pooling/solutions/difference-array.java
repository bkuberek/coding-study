public class Solution {
    public boolean carPooling(int[][] trips, int capacity) {
        int last = 0;
        for (int[] trip : trips) {
            last = Math.max(last, trip[2]);
        }
        // change[x] is how much the load changes at location x; its prefix sums are the loads.
        int[] change = new int[last + 1];
        for (int[] trip : trips) {
            change[trip[1]] += trip[0];
            change[trip[2]] -= trip[0];
        }
        int load = 0;
        for (int delta : change) {
            load += delta;
            if (load > capacity) {
                return false;
            }
        }
        return true;
    }
}
