import java.util.*;

public class Solution {
    public int subarraySum(int[] nums, int k) {
        // seen maps a prefix sum to how many prefixes so far have it; the empty prefix sums to 0.
        Map<Integer, Integer> seen = new HashMap<>();
        seen.put(0, 1);
        int total = 0;
        int count = 0;
        for (int value : nums) {
            total += value;
            count += seen.getOrDefault(total - k, 0);
            seen.merge(total, 1, Integer::sum);
        }
        return count;
    }
}
