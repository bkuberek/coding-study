import java.util.*;

public class Solution {
    public boolean canPartition(int[] nums) {
        int total = Arrays.stream(nums).sum();
        if (total % 2 == 1) {
            return false;
        }
        int target = total / 2;
        // reachable[s] is true when some of the elements seen so far add up to exactly s.
        boolean[] reachable = new boolean[target + 1];
        reachable[0] = true;
        for (int value : nums) {
            // Right to left, so reachable[s - value] still describes the elements before value.
            for (int s = target; s >= value; s--) {
                if (reachable[s - value]) {
                    reachable[s] = true;
                }
            }
            if (reachable[target]) {
                return true;
            }
        }
        return reachable[target];
    }
}
