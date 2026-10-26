import java.util.*;

public class Solution {
    public int majorityElement(int[] nums) {
        int half = nums.length / 2;
        Map<Integer, Integer> counts = new HashMap<>();
        for (int value : nums) {
            // merge returns the updated count as an Integer; compare it as an int.
            int count = counts.merge(value, 1, Integer::sum);
            if (count > half) {
                return value;
            }
        }
        throw new IllegalArgumentException("no majority element");
    }
}
