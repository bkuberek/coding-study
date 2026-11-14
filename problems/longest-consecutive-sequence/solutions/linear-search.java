import java.util.*;

public class Solution {
    public int longestConsecutive(int[] nums) {
        int longest = 0;
        for (int i = 0; i < nums.length; i++) {
            int value = nums[i];
            if (indexOf(nums, value - 1) != -1) {
                continue;
            }
            if (indexOf(nums, value) < i) {
                continue; // an earlier copy of this start already counted its run
            }
            int length = 1;
            while (indexOf(nums, value + length) != -1) {
                length++;
            }
            longest = Math.max(longest, length);
        }
        return longest;
    }

    private static int indexOf(int[] nums, int target) {
        for (int i = 0; i < nums.length; i++) {
            if (nums[i] == target) {
                return i;
            }
        }
        return -1;
    }
}
