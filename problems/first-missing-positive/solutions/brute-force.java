import java.util.*;

public class Solution {
    public int firstMissingPositive(int[] nums) {
        int candidate = 1;
        while (contains(nums, candidate)) {
            candidate++;
        }
        return candidate;
    }

    private static boolean contains(int[] nums, int target) {
        for (int value : nums) {
            if (value == target) {
                return true;
            }
        }
        return false;
    }
}
