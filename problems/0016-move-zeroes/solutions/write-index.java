import java.util.*;

public class Solution {
    public void moveZeroes(int[] nums) {
        int write = 0;
        for (int value : nums) {
            if (value != 0) {
                nums[write++] = value;
            }
        }
        Arrays.fill(nums, write, nums.length, 0);
    }
}
