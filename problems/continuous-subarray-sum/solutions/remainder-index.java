import java.util.*;

public class Solution {
    public boolean checkSubarraySum(int[] nums, int k) {
        // firstIndex maps a prefix remainder to the earliest position where it appeared;
        // the empty prefix ends at position -1.
        Map<Integer, Integer> firstIndex = new HashMap<>();
        firstIndex.put(0, -1);
        int remainder = 0;
        for (int position = 0; position < nums.length; position++) {
            // remainder + nums[position] can pass 2^31 - 1, so add in long before reducing.
            remainder = (int) (((long) remainder + nums[position]) % k);
            Integer earlier = firstIndex.putIfAbsent(remainder, position);
            if (earlier != null && position - earlier >= 2) {
                return true;
            }
        }
        return false;
    }
}
