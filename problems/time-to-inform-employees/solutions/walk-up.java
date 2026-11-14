public class Solution {
    public int numOfMinutes(int n, int headID, int[] manager, int[] informTime) {
        int longest = 0;
        for (int employee = 0; employee < n; employee++) {
            // The news reaches employee after every manager above them has passed it on.
            int elapsed = 0;
            int current = employee;
            while (current != headID) {
                current = manager[current];
                elapsed += informTime[current];
            }
            longest = Math.max(longest, elapsed);
        }
        return longest;
    }
}
