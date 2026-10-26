import java.util.*;

public class Solution {
    public boolean canJump(int[] nums) {
        int last = nums.length - 1;
        // reachable[i] is true once some sequence of jumps from index 0 is known to land on i.
        boolean[] reachable = new boolean[nums.length];
        reachable[0] = true;
        for (int i = 0; i < nums.length; i++) {
            if (!reachable[i]) {
                continue;
            }
            if (i == last) {
                return true;
            }
            int farthest = Math.min(last, i + nums[i]);
            for (int target = i + 1; target <= farthest; target++) {
                reachable[target] = true;
            }
        }
        return reachable[last];
    }
}
