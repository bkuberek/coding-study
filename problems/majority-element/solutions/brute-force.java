import java.util.*;

public class Solution {
    public int majorityElement(int[] nums) {
        int half = nums.length / 2;
        for (int candidate : nums) {
            int count = 0;
            for (int value : nums) {
                if (value == candidate) {
                    count++;
                }
            }
            if (count > half) {
                return candidate;
            }
        }
        throw new IllegalArgumentException("no majority element");
    }
}
