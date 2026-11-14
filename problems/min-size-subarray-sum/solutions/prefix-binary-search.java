import java.util.*;

public class Solution {
    public int minSubArrayLen(int target, int[] nums) {
        int n = nums.length;
        int[] prefix = new int[n + 1];
        for (int i = 0; i < n; i++) {
            prefix[i + 1] = prefix[i] + nums[i];
        }
        int best = 0;
        for (int start = 0; start < n; start++) {
            int found = Arrays.binarySearch(prefix, start + 1, n + 1, prefix[start] + target);
            int end = found >= 0 ? found : -found - 1;
            if (end <= n && (best == 0 || end - start < best)) {
                best = end - start;
            }
        }
        return best;
    }
}
